"""
No-Verify Persistent Agent Tree Experiment

Same as experiment021 but the architect is told not to verify children's work
after wait_all(). Trust children + rely on tsc as the external validator.
This should cut the architect's post-fork API calls and reduce total time.

## Experiment Results (2026-03-27)

Model: claude-sonnet-4-6
Root task: Product dashboard.

### Timing Summary

    Generation time:  49s
    tsc --noEmit:     PASS (0 errors)
    Architect msgs:   9 (vs 15 in exp021)

### Comparison

    | Metric              | Exp021 (verify) | Exp022 (no verify) |
    |---------------------|-----------------|--------------------|
    | Generation time     | 74s             | 49s (-34%)         |
    | Architect messages  | 15              | 9 (-40%)           |
    | tsc                 | PASS            | PASS               |

### Key Findings

- 34% faster just by telling the architect not to read children's files
  after wait_all(). It went straight to done().
- tsc still passes — external validation catches errors, no need for
  the architect to double-check.
- Architect messages dropped from 15 to 9 — no post-fork read_file calls.
- Simple instruction change, no code change needed.
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json
import os
import subprocess
import tempfile
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from uuid import uuid4

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = anthropic.Anthropic()
executor = ThreadPoolExecutor(max_workers=8)

_print_lock = threading.Lock()
_index_lock = threading.Lock()
file_index: dict[str, list[str]] = {}


def safe_print(msg: str):
    with _print_lock:
        print(msg)


# ──────────────────────────────────────────────
# Filesystem tools
# ──────────────────────────────────────────────

def execute_fs_tool(tool_name: str, tool_input: dict, project_root: str) -> str:
    if tool_name == "read_file":
        fpath = os.path.join(project_root, tool_input["file_path"])
        if os.path.isdir(fpath):
            return f"Directory: {os.listdir(fpath)}"
        if os.path.exists(fpath):
            with open(fpath) as f:
                return f.read() or "(empty)"
        return f"Not found: {tool_input['file_path']}"
    elif tool_name == "append_to_file":
        if "content" not in tool_input:
            return "Error: missing content."
        fpath = os.path.join(project_root, tool_input["file_path"])
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "a") as f:
            f.write(tool_input["content"])
        return f"Appended to {tool_input['file_path']}."
    elif tool_name == "replace_text":
        if "old_text" not in tool_input or "new_text" not in tool_input:
            return "Error: missing old_text/new_text."
        fpath = os.path.join(project_root, tool_input["file_path"])
        if not os.path.exists(fpath):
            return f"Not found: {tool_input['file_path']}"
        with open(fpath) as f:
            content = f.read()
        if tool_input["old_text"] not in content:
            return f"old_text not found in {tool_input['file_path']}."
        with open(fpath, "w") as f:
            f.write(content.replace(tool_input["old_text"], tool_input["new_text"], 1))
        return f"Replaced in {tool_input['file_path']}."
    return f"Unknown tool: {tool_name}"


# ──────────────────────────────────────────────
# Tools & prompt
# ──────────────────────────────────────────────

AGENT_TOOLS = [
    {"name": "read_file", "description": "Read a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
    {"name": "append_to_file", "description": "Append to a file. Creates dirs if needed.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}},
    {"name": "replace_text", "description": "Replace text in a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["file_path", "old_text", "new_text"]}},
    {
        "name": "fork_and_assign",
        "description": "Fork your conversation context to a child agent. The child inherits your full history. Returns immediately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "file_path": {"type": "string"},
                "task": {"type": "string"},
            },
            "required": ["name", "file_path", "task"],
        },
    },
    {
        "name": "delegate_to_child",
        "description": (
            "Send a modification request to an existing child agent by name. "
            "The child already has its full conversation history from the initial build. "
            "It will receive your request and modify its files accordingly. "
            "Returns immediately — child runs in parallel."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "child_name": {"type": "string", "description": "Name of the existing child agent."},
                "request": {"type": "string", "description": "What to change. The child has full context."},
            },
            "required": ["child_name", "request"],
        },
    },
    {"name": "wait_all", "description": "Wait for ALL pending children/delegations to finish.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "done", "description": "Signal you are finished.", "input_schema": {"type": "object", "properties": {}}},
]

SYSTEM_PROMPT = """\
You are a senior React/TypeScript developer. You can read and write files,
fork child agents, delegate to existing children, and signal completion.

Tools: read_file, append_to_file, replace_text, fork_and_assign,
       delegate_to_child, wait_all, done.

When you fork a child, it inherits your full conversation.
When you delegate_to_child, the child already has its history from the initial
build — it knows what it wrote. Send it a short modification request.

Project layout: src/components/Name/Name.tsx + index.ts, src/hooks/useX.ts,
src/utils/x.ts, src/types/index.ts, src/App.tsx.

Use .tsx for JSX, .ts for logic. Include imports. Call done() when finished.
"""


# ──────────────────────────────────────────────
# Persistent Agent Node
# ──────────────────────────────────────────────

@dataclass
class AgentNode:
    name: str
    messages: list[dict] = field(default_factory=list)
    children: dict[str, "AgentNode"] = field(default_factory=dict)
    file_path: str = ""


# Global agent tree
agent_tree: dict[str, AgentNode] = {}


def run_agent_turn(
    node: AgentNode,
    user_message: str,
    project_root: str,
    depth: int = 0,
    max_depth: int = 2,
    is_initial: bool = True,
) -> None:
    """Run one conversation turn for an agent. Modifies node.messages in place."""
    indent = "  " * depth
    safe_print(f"{indent}[{node.name}] Processing{'...' if is_initial else ' modification...'}")

    node.messages.append({"role": "user", "content": user_message})

    # At max depth during initial build, no fork/delegate/wait
    if depth >= max_depth and is_initial:
        tools = [t for t in AGENT_TOOLS if t["name"] not in ("fork_and_assign", "delegate_to_child", "wait_all")]
    else:
        tools = AGENT_TOOLS

    pending_futures: dict[str, tuple[Future, dict]] = {}
    pending_forks: list[tuple[str, dict]] = []
    is_done = False

    while not is_done:
        response = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=4096,
            system=SYSTEM_PROMPT, tools=tools, messages=node.messages,
            cache_control={"type": "ephemeral"},
        )
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" and not tool_use_blocks:
            # Save assistant response
            node.messages.append({"role": "assistant", "content": response.content})
            break
        if not tool_use_blocks:
            break

        node.messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        pending_forks.clear()

        for block in tool_use_blocks:
            if block.name in ("read_file", "append_to_file", "replace_text"):
                result = execute_fs_tool(block.name, block.input, project_root)
                if block.name in ("append_to_file", "replace_text"):
                    fp = block.input.get("file_path", "")
                    if fp:
                        with _index_lock:
                            file_index.setdefault(fp, [])
                            if node.name not in file_index[fp]:
                                file_index[fp].append(node.name)
                safe_print(f"{indent}  [{block.name}] {block.input.get('file_path', '?')[:50]} -> {result[:40]}")
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})

            elif block.name == "fork_and_assign":
                task_id = str(uuid4())[:8]
                pending_forks.append((task_id, block.input))
                safe_print(f"{indent}  -> Will fork: {block.input['name']} [{task_id}]")
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"task_id": task_id, "status": "forked"})})

            elif block.name == "delegate_to_child":
                child_name = block.input["child_name"]
                request = block.input["request"]

                if child_name in node.children:
                    child_node = node.children[child_name]
                    task_id = str(uuid4())[:8]
                    safe_print(f"{indent}  -> Delegating to {child_name}: {request[:50]}... [{task_id}]")

                    future = executor.submit(
                        run_agent_turn,
                        node=child_node,
                        user_message=f"Modification request: {request}\n\nRead your current file, make the change, then call done().",
                        project_root=project_root,
                        depth=depth + 1,
                        is_initial=False,
                    )
                    pending_futures[task_id] = (future, {"name": child_name})
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"task_id": task_id, "status": "delegated"})})
                else:
                    available = list(node.children.keys())
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": block.id,
                        "content": f"Error: no child named '{child_name}'. Available: {available}",
                        "is_error": True,
                    })

            elif block.name == "wait_all":
                if pending_futures:
                    safe_print(f"{indent}  <- Waiting for {len(pending_futures)} agents...")
                    results_list = []
                    for tid, (future, info) in list(pending_futures.items()):
                        future.result()
                        safe_print(f"{indent}  <- Done: {info['name']}")
                        results_list.append({"name": info["name"], "success": True})
                    pending_futures.clear()
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"results": results_list})})
                else:
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "No pending agents."})

            elif block.name == "done":
                is_done = True
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Done."})

        node.messages.append({"role": "user", "content": tool_results})

        # Fork new children after tool_results appended
        for task_id, fork_input in pending_forks:
            child_name = fork_input["name"]
            child_path = fork_input["file_path"]
            child_task = fork_input["task"]

            # Create child node with forked context
            child_node = AgentNode(name=child_name, messages=list(node.messages), file_path=child_path)
            node.children[child_name] = child_node

            safe_print(f"{indent}  -> Forking now: {child_name} -> {child_path} [{task_id}]")

            future = executor.submit(
                run_agent_turn,
                node=child_node,
                user_message=(
                    f"You have been forked to implement: {child_name}\n"
                    f"Write to: {child_path}\n"
                    f"Task: {child_task}\n\n"
                    f"Implement this now, then call done()."
                ),
                project_root=project_root,
                depth=depth + 1,
                max_depth=max_depth,
                is_initial=True,
            )
            pending_futures[task_id] = (future, fork_input)
        pending_forks.clear()

    # Collect orphans
    for tid, (future, info) in pending_futures.items():
        future.result()

    safe_print(f"{indent}[{node.name}] Done.")


# ──────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────

PACKAGE_JSON = """{
  "name": "morph-generated-app",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": { "dev": "vite" },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
"""

TSCONFIG_JSON = """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false
  },
  "include": ["src"]
}
"""

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
  <head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><title>Morph App</title></head>
  <body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>
</html>
"""

MAIN_TSX = """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>
);
"""

VITE_CONFIG = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()] });
"""


def scaffold_and_validate(project_root: str) -> tuple[bool, str]:
    for name, content in [("package.json", PACKAGE_JSON), ("tsconfig.json", TSCONFIG_JSON),
                          ("index.html", INDEX_HTML), ("vite.config.ts", VITE_CONFIG)]:
        with open(os.path.join(project_root, name), "w") as f:
            f.write(content)
    main_path = os.path.join(project_root, "src", "main.tsx")
    if not os.path.exists(main_path):
        os.makedirs(os.path.dirname(main_path), exist_ok=True)
        with open(main_path, "w") as f:
            f.write(MAIN_TSX)

    subprocess.run(["npm", "install", "--silent"], cwd=project_root, capture_output=True, timeout=60)
    result = subprocess.run(["npx", "tsc", "--noEmit"], cwd=project_root, capture_output=True, text=True, timeout=60)
    output = result.stdout + result.stderr
    return result.returncode == 0, output


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def print_agent_tree(node: AgentNode, indent: int = 0):
    prefix = "  " * indent
    n_msgs = len(node.messages)
    print(f"{prefix}{node.name} ({n_msgs} messages, {len(node.children)} children)")
    for child in node.children.values():
        print_agent_tree(child, indent + 1)


def main():
    root_task = (
        "Build a React dashboard that displays a list of products. Features:\n"
        "- A search bar that filters products by name in real time\n"
        "- Sort buttons to sort by name, price, or rating\n"
        "- A product card component showing name, price, rating, and an image\n"
        "- A loading spinner while data is being fetched\n"
        "- Use a custom hook for the data fetching and filtering logic\n"
        "- TypeScript types for the Product model\n"
        "- The product data can be hardcoded as mock data in a utils file"
    )

    root_message = (
        f"{root_task}\n\n"
        "Take it easy. Don't write component code yourself.\n"
        "1. Plan the structure. Write shared types (src/types/index.ts) and mock data (src/utils/mockProducts.ts).\n"
        "2. Fork a child for each component, the hook, and App.tsx.\n"
        "3. Fork ALL at once, wait_all(), done().\n\n"
        "IMPORTANT: Code will be validated with tsc --noEmit. All imports must resolve.\n\n"
        "DO NOT verify children's work after wait_all(). Trust them — tsc will catch errors. "
        "Just wait_all() then done() immediately."
    )

    project_root = tempfile.mkdtemp(prefix="morph_exp022_")

    print("=" * 60)
    print("NO-VERIFY PERSISTENT AGENT TREE")
    print("=" * 60)
    print(f"\nProject root: {project_root}\n")

    # Phase 1: Initial generation
    print("--- Phase 1: Generate ---\n")
    root_node = AgentNode(name="architect")
    t0 = time.monotonic()
    run_agent_turn(root_node, root_message, project_root, depth=0, max_depth=2, is_initial=True)
    gen_time = time.monotonic() - t0

    # Validate
    print("\n--- Validating ---")
    success, output = scaffold_and_validate(project_root)
    error_count = output.count("error TS")
    print(f"  tsc: {'PASS' if success else 'FAIL'} ({error_count} errors)")
    if not success:
        for line in output.strip().split("\n")[:20]:
            print(f"  {line}")

    print(f"\n  Generation time: {gen_time:.1f}s")

    # Show agent tree
    print("\n--- Agent Tree ---")
    print_agent_tree(root_node)

    # Phase 2: Interactive modification loop
    print("\n" + "=" * 60)
    print("MODIFICATION MODE")
    print("=" * 60)
    print("Send modification requests to the architect.")
    print("The architect will delegate to child agents as needed.")
    print("Type 'quit' to exit, 'tree' to show agent tree,")
    print("'validate' to re-run tsc, 'serve' to start Vite.\n")

    while True:
        try:
            user_input = input("modification> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue
        if user_input == "quit":
            break
        if user_input == "tree":
            print_agent_tree(root_node)
            continue
        if user_input == "validate":
            success, output = scaffold_and_validate(project_root)
            error_count = output.count("error TS")
            print(f"  tsc: {'PASS' if success else 'FAIL'} ({error_count} errors)")
            if not success:
                for line in output.strip().split("\n")[:20]:
                    print(f"  {line}")
            continue
        if user_input == "serve":
            print(f"  Starting Vite at {project_root}...")
            print("  Open http://localhost:5173")
            print("  Press Ctrl+C to stop.\n")
            try:
                subprocess.run(["npx", "vite", "--host"], cwd=project_root)
            except KeyboardInterrupt:
                print("\n  Dev server stopped.")
            continue

        # Send modification to architect
        mod_message = (
            f"Modification request from the user:\n\n{user_input}\n\n"
            f"You have the following child agents you can delegate to: {list(root_node.children.keys())}.\n"
            f"Use delegate_to_child to send changes to the right agent(s), "
            f"or handle it yourself if it's a types/utils change. "
            f"Then wait_all() and done().\n\n"
            f"DO NOT verify children's work after wait_all(). Trust them. Just done() immediately."
        )

        t0 = time.monotonic()
        run_agent_turn(root_node, mod_message, project_root, depth=0, is_initial=False)
        mod_time = time.monotonic() - t0

        # Auto-validate
        success, output = scaffold_and_validate(project_root)
        error_count = output.count("error TS")
        print(f"\n  Modification: {mod_time:.1f}s")
        print(f"  tsc: {'PASS' if success else 'FAIL'} ({error_count} errors)")
        if not success:
            for line in output.strip().split("\n")[:20]:
                print(f"  {line}")
        print()

    print(f"\nProject at: {project_root}")
    executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
