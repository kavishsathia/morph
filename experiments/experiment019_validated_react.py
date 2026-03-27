"""
Validated React Experiment

Same as experiment015 (generic agent, forked context, single-wave fork) but
after generation, we scaffold a real project (package.json, tsconfig.json),
install dependencies, and run `tsc --noEmit` to validate the output compiles.

No fixing — just checking if the generated code actually works.

## Experiment Results (2026-03-27)

Model: claude-sonnet-4-6
Root task: Product dashboard.
7 agents, 22 API calls, 7.6K tokens + 77K cache reads.

### Timing Summary

    Generation:       58s
    Validation:        2s (npm install + tsc --noEmit)
    Total:            60s

### Validation

    tsc --noEmit: PASSED — 0 errors

### Agent Timings

    architect          58.0s  (46s API, 12s waiting, 6 calls)
    app-agent          13.6s  (2 calls)
    productcard-agent  10.2s  (3 calls)
    sortcontrols        9.2s  (3 calls)
    searchbar           6.8s  (3 calls)
    spinner             6.7s  (3 calls)
    hook-agent          5.7s  (2 calls)

### Key Findings

- tsc --noEmit passes with 0 errors on first generation. No fixing needed.
- The forked agent pattern produces fully type-safe React/TypeScript code.
- All imports resolve, all types are correct, all exports match.
- Validation adds only 2s (npm install + tsc) — negligible overhead.
- This confirms the architecture: generic agent + forked context + single
  wave produces correct, compilable code out of the box.
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

# ──────────────────────────────────────────────
# Timing
# ──────────────────────────────────────────────

@dataclass
class AgentTiming:
    name: str
    kind: str
    depth: int
    start: float = 0.0
    end: float = 0.0
    api_calls: list[float] = field(default_factory=list)
    wait_time: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def total(self) -> float:
        return self.end - self.start

    @property
    def api_total(self) -> float:
        return sum(self.api_calls)

    @property
    def own_work(self) -> float:
        return self.total - self.wait_time


_timings_lock = threading.Lock()
agent_timings: list[AgentTiming] = []

_index_lock = threading.Lock()
file_index: dict[str, list[str]] = {}

_print_lock = threading.Lock()


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
# Agent tools & prompt
# ──────────────────────────────────────────────

AGENT_TOOLS = [
    {"name": "read_file", "description": "Read a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
    {"name": "append_to_file", "description": "Append to a file. Creates dirs if needed.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}},
    {"name": "replace_text", "description": "Replace text in a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["file_path", "old_text", "new_text"]}},
    {
        "name": "fork_and_assign",
        "description": "Fork your conversation context to a child agent. The child inherits your full history. Give it a file_path and short task. Returns immediately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "file_path": {"type": "string"},
                "task": {"type": "string", "description": "Short task. The child has your full context."},
            },
            "required": ["name", "file_path", "task"],
        },
    },
    {"name": "wait_all", "description": "Wait for ALL forked children to finish.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "done", "description": "Signal you are finished.", "input_schema": {"type": "object", "properties": {}}},
]

SYSTEM_PROMPT = """\
You are a senior React/TypeScript developer. You can read and write files,
fork child agents, and signal completion.

Tools: read_file, append_to_file, replace_text, fork_and_assign, wait_all, done.

When you fork a child, it inherits your full conversation — it knows everything
you've discussed and written. Keep fork tasks short (2-3 sentences).

Project layout: src/components/Name/Name.tsx + index.ts, src/hooks/useX.ts,
src/utils/x.ts, src/types/index.ts, src/App.tsx.

Use .tsx for files with JSX, .ts for pure logic/types. Include imports. Call done() when finished.

IMPORTANT: Write valid TypeScript that will pass `tsc --noEmit`. This means:
- All imports must resolve to actual files
- All types must be properly defined and exported
- No implicit any — use explicit types
- Export components as default exports
"""


def timed_api_call(timing, **kwargs):
    t0 = time.monotonic()
    response = client.messages.create(**kwargs)
    dt = time.monotonic() - t0
    timing.api_calls.append(dt)
    timing.input_tokens += response.usage.input_tokens
    timing.output_tokens += response.usage.output_tokens
    timing.cache_read_tokens += getattr(response.usage, 'cache_read_input_tokens', 0) or 0
    timing.cache_creation_tokens += getattr(response.usage, 'cache_creation_input_tokens', 0) or 0
    return response


# ──────────────────────────────────────────────
# Generic agent
# ──────────────────────────────────────────────

def run_agent(
    name: str,
    user_message: str,
    parent_messages: list[dict] | None = None,
    project_root: str = "",
    depth: int = 0,
    max_depth: int = 2,
) -> dict:
    timing = AgentTiming(name=name, kind="agent", depth=depth, start=time.monotonic())
    indent = "  " * depth
    safe_print(f"{indent}[depth={depth}] Agent started: {name}")

    if parent_messages:
        messages = list(parent_messages) + [{"role": "user", "content": user_message}]
    else:
        messages = [{"role": "user", "content": user_message}]

    if depth >= max_depth:
        tools = [t for t in AGENT_TOOLS if t["name"] not in ("fork_and_assign", "wait_all")]
    else:
        tools = AGENT_TOOLS

    children = []
    pending_futures: dict[str, tuple[Future, dict]] = {}
    pending_forks: list[tuple[str, dict]] = []
    is_done = False

    while not is_done:
        response = timed_api_call(
            timing, model="claude-sonnet-4-6", max_tokens=4096,
            system=SYSTEM_PROMPT, tools=tools, messages=messages,
            cache_control={"type": "ephemeral"},
        )
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" and not tool_use_blocks:
            break
        if not tool_use_blocks:
            break

        messages.append({"role": "assistant", "content": response.content})
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
                            if name not in file_index[fp]:
                                file_index[fp].append(name)
                safe_print(f"{indent}  [{block.name}] {block.input.get('file_path', '?')[:50]} -> {result[:40]}")
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})

            elif block.name == "fork_and_assign":
                task_id = str(uuid4())[:8]
                safe_print(f"{indent}  -> Will fork: {block.input['name']} [{task_id}]")
                pending_forks.append((task_id, block.input))
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"task_id": task_id, "status": "forked"})})

            elif block.name == "wait_all":
                if pending_futures:
                    safe_print(f"{indent}  <- Waiting for {len(pending_futures)} children...")
                    wait_start = time.monotonic()
                    results_list = []
                    for tid, (future, info) in list(pending_futures.items()):
                        child_result = future.result()
                        children.append(child_result)
                        safe_print(f"{indent}  <- Done: {info['name']}")
                        results_list.append({"name": info["name"], "success": True})
                    timing.wait_time += time.monotonic() - wait_start
                    pending_futures.clear()
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"results": results_list})})
                else:
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "No pending children."})

            elif block.name == "done":
                is_done = True
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Done."})

        messages.append({"role": "user", "content": tool_results})

        for task_id, fork_input in pending_forks:
            child_name = fork_input["name"]
            child_path = fork_input["file_path"]
            child_task = fork_input["task"]

            safe_print(f"{indent}  -> Forking now: {child_name} -> {child_path} [{task_id}]")

            future = executor.submit(
                run_agent,
                name=child_name,
                user_message=(
                    f"You have been forked to implement: {child_name}\n"
                    f"Write to: {child_path}\n"
                    f"Task: {child_task}\n\n"
                    f"You have my full context. Implement this now, then call done()."
                ),
                parent_messages=list(messages),
                project_root=project_root,
                depth=depth + 1,
                max_depth=max_depth,
            )
            pending_futures[task_id] = (future, fork_input)
        pending_forks.clear()

    for tid, (future, info) in pending_futures.items():
        wait_start = time.monotonic()
        children.append(future.result())
        timing.wait_time += time.monotonic() - wait_start

    timing.end = time.monotonic()
    with _timings_lock:
        agent_timings.append(timing)

    safe_print(f"{indent}[depth={depth}] Agent done: {name} ({timing.total:.1f}s)")
    return {"name": name, "children": children}


# ──────────────────────────────────────────────
# Validation: scaffold + tsc
# ──────────────────────────────────────────────

PACKAGE_JSON = """{
  "name": "morph-generated-app",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.3.0"
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
    "allowImportingTsExtensions": false,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {}
  },
  "include": ["src"]
}
"""


def validate_project(project_root: str) -> tuple[bool, str, float]:
    """Run npm install + tsc --noEmit. Returns (success, output, duration)."""
    t0 = time.monotonic()

    # Write package.json and tsconfig.json
    with open(os.path.join(project_root, "package.json"), "w") as f:
        f.write(PACKAGE_JSON)
    with open(os.path.join(project_root, "tsconfig.json"), "w") as f:
        f.write(TSCONFIG_JSON)

    # npm install
    print("\n[Validation] Running npm install...")
    install_result = subprocess.run(
        ["npm", "install", "--silent"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if install_result.returncode != 0:
        return False, f"npm install failed:\n{install_result.stderr}", time.monotonic() - t0

    # tsc --noEmit
    print("[Validation] Running tsc --noEmit...")
    tsc_result = subprocess.run(
        ["npx", "tsc", "--noEmit"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=60,
    )

    duration = time.monotonic() - t0
    output = tsc_result.stdout + tsc_result.stderr

    if tsc_result.returncode == 0:
        return True, "No errors.", duration
    else:
        return False, output, duration


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def print_tree(node, indent=0):
    prefix = "  " * indent
    print(f"{prefix}{node['name']}")
    for child in node.get("children", []):
        print_tree(child, indent + 1)


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
        "Take it easy on this one. Don't write component code yourself.\n"
        "Instead:\n"
        "1. Plan the project structure — decide what components, hooks, types, and utils you need.\n"
        "2. Write ONLY the shared types (src/types/index.ts) and mock data (src/utils/mockProducts.ts).\n"
        "3. Fork a child agent for EACH component and the hook. Give each a file_path and short task.\n"
        "4. Fork one child for App.tsx too — you're just the architect.\n"
        "5. Fork ALL children at once, then wait_all(), then done().\n\n"
        "IMPORTANT: The generated code will be validated with `tsc --noEmit`.\n"
        "Make sure all imports resolve, all types are correct, and exports match."
    )

    project_root = tempfile.mkdtemp(prefix="morph_exp019_")
    total_start = time.monotonic()

    print("=" * 60)
    print("VALIDATED REACT EXPERIMENT")
    print("=" * 60)
    print(f"\nRoot task: {root_task}")
    print(f"Project root: {project_root}\n")

    # Phase 1: Generate
    print("--- Phase 1: Generate ---\n")
    gen_start = time.monotonic()
    tree = run_agent(
        name="architect",
        user_message=root_message,
        project_root=project_root,
        depth=0,
        max_depth=2,
    )
    gen_time = time.monotonic() - gen_start

    # Phase 2: Validate
    print("\n--- Phase 2: Validate ---")
    success, output, val_time = validate_project(project_root)

    total_time = time.monotonic() - total_start

    # Results
    print("\n" + "=" * 60)
    print("AGENT TREE")
    print("=" * 60)
    print_tree(tree)

    print("\n" + "=" * 60)
    print("FILE INDEX")
    print("=" * 60)
    with _index_lock:
        for path, names in sorted(file_index.items()):
            print(f"  {path}: {', '.join(set(names))}")

    # Validation result
    print("\n" + "=" * 60)
    print("VALIDATION RESULT")
    print("=" * 60)
    if success:
        print("\n  tsc --noEmit: PASSED")
    else:
        print("\n  tsc --noEmit: FAILED")
        # Show errors, limit to first 50 lines
        lines = output.strip().split("\n")
        for line in lines[:50]:
            print(f"  {line}")
        if len(lines) > 50:
            print(f"  ... ({len(lines) - 50} more lines)")

    # Count errors
    error_count = output.count("error TS")
    print(f"\n  Total TS errors: {error_count}")
    print(f"  Validation time: {val_time:.1f}s")

    # Timing
    print("\n" + "=" * 60)
    print("TIMING REPORT")
    print("=" * 60)

    total_api_calls = sum(len(t.api_calls) for t in agent_timings)
    total_input = sum(t.input_tokens for t in agent_timings)
    total_output = sum(t.output_tokens for t in agent_timings)
    total_cache_read = sum(t.cache_read_tokens for t in agent_timings)

    print(f"\n  Total wall clock:        {total_time:.1f}s")
    print(f"  Generation time:         {gen_time:.1f}s")
    print(f"  Validation time:         {val_time:.1f}s")
    print(f"  Total API calls:         {total_api_calls}")
    print(f"  Total input tokens:      {total_input:,}")
    print(f"  Total output tokens:     {total_output:,}")
    print(f"  Cache read tokens:       {total_cache_read:,}")
    print(f"  tsc result:              {'PASS' if success else 'FAIL'} ({error_count} errors)")

    print(f"\n  --- Agent Timings ({len(agent_timings)} agents) ---")
    print(f"  {'Name':<25} {'D':>1} {'Total':>7} {'API':>7} {'Wait':>7} {'#':>3} {'In':>8} {'Out':>7} {'CacheR':>8}")
    print(f"  {'-'*25} {'-'} {'-'*7} {'-'*7} {'-'*7} {'-'*3} {'-'*8} {'-'*7} {'-'*8}")
    for t in sorted(agent_timings, key=lambda x: x.start):
        print(f"  {t.name:<25} {t.depth} {t.total:>6.1f}s {t.api_total:>6.1f}s {t.wait_time:>6.1f}s {len(t.api_calls):>3} {t.input_tokens:>8,} {t.output_tokens:>7,} {t.cache_read_tokens:>8,}")

    # Files on disk
    print(f"\n" + "=" * 60)
    print(f"FILES ON DISK ({project_root})")
    print("=" * 60)
    for dirpath, _, filenames in os.walk(project_root):
        for fname in sorted(filenames):
            if fname in ("package.json", "tsconfig.json") or "node_modules" in dirpath:
                continue
            fpath = os.path.join(dirpath, fname)
            relpath = os.path.relpath(fpath, project_root)
            print(f"\n# ===== {relpath} =====")
            with open(fpath) as f:
                lines = f.read().split("\n")
            if len(lines) > 50:
                print("\n".join(lines[:50]))
                print(f"  ... ({len(lines) - 50} more lines)")
            else:
                print("\n".join(lines))

    print(f"\nProject written to: {project_root}")
    executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
