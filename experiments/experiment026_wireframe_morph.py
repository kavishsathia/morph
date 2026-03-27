"""
Wireframe Morph Experiment

The parent writes a complete wireframe of the app — visible stubs with gray
boxes, dashed borders, placeholder text, and rough layout. The user sees the
full structure from second one. Then children are forked, and each child morphs
its stub into the real component using replace_text on App.tsx.

No lazy loading, no error boundaries. The stubs ARE the initial render.
Children replace them in-place via HMR. The user watches the wireframe come
alive piece by piece.

Flow:
1. Vite starts
2. Architect writes types, utils, hooks, and App.tsx with inline wireframe stubs
3. Browser shows full wireframe layout immediately
4. Architect forks children — each gets a stub ID and replaces it with real JSX
5. Each replacement triggers HMR — wireframe blocks morph into real components

## Experiment Results (2026-03-27)

Model: claude-sonnet-4-6
Root task: Product dashboard.

### Timing Summary

    Built in:         136s
    tsc --noEmit:     PASS
    Architect calls:  3 (wireframe, fork_batch, wait+done)
    Children:         4 (SearchBar, SortControls, LoadingSpinner, ProductGrid)

### What happened

    Response 1: Architect writes types, utils, hook, App.tsx with wireframe stubs
                -> Browser shows full wireframe layout with dashed gray boxes
    Response 2: fork_batch — all 4 children launched simultaneously
                >> Batched 4 forks
    Response 3: wait_all + done

    Children ran in true parallel (interleaved file writes confirm this).
    Each child: wrote component file, then replaced its stub in App.tsx.
    Stubs morphed into real components via HMR as children finished.

### Key Findings

- fork_batch solved the sequential forking problem — one tool call, all children.
- Architect had exactly 3 responses as instructed (wireframe, forks, done).
- Wireframe appeared in browser within seconds. Stubs morphed into real
  components one by one as children finished writing.
- tsc PASS after generation.
- 136s is slower than exp022 (49s) because the wireframe + stub replacement
  pattern requires more work per child (read App.tsx, find stub, replace).
  The exp022 pattern where children just write their own file is faster.
- The tradeoff: exp022 is faster, exp026 has a better user experience
  (no blank screen, visible wireframe from second one).
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


@dataclass
class AgentNode:
    name: str
    messages: list[dict] = field(default_factory=list)
    children: dict[str, "AgentNode"] = field(default_factory=dict)


class Morph:
    AGENT_TOOLS = [
        {"name": "read_file", "description": "Read a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
        {"name": "append_to_file", "description": "Append to a file. Creates dirs if needed.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}},
        {"name": "replace_text", "description": "Replace text in a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["file_path", "old_text", "new_text"]}},
        {
            "name": "fork_batch",
            "description": "Fork MULTIPLE child agents at once. Each inherits your full history. ALL children start immediately in parallel. Use this instead of calling fork one at a time.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "children": {
                        "type": "array",
                        "description": "Array of children to fork simultaneously.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "file_path": {"type": "string"},
                                "task": {"type": "string"},
                            },
                            "required": ["name", "file_path", "task"],
                        },
                    },
                },
                "required": ["children"],
            },
        },
        {
            "name": "delegate_to_child",
            "description": "Send a modification to an existing child agent by name. Returns immediately.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "child_name": {"type": "string"},
                    "request": {"type": "string"},
                },
                "required": ["child_name", "request"],
            },
        },
        {"name": "wait_all", "description": "Wait for ALL pending children/delegations.", "input_schema": {"type": "object", "properties": {}}},
        {"name": "done", "description": "Signal you are finished.", "input_schema": {"type": "object", "properties": {}}},
    ]

    SYSTEM_PROMPT = """\
You are a senior React/TypeScript developer. You can read and write files,
fork_batch children, delegate to existing children, and signal completion.

When you fork_batch, ALL children start simultaneously. Each inherits your full conversation.
When you delegate_to_child, the child has its history from the initial build.

Use .tsx for JSX, .ts for logic. Include imports. Use inline styles only.
Call done() when finished.

IMPORTANT — WIREFRAME-FIRST APPROACH:
A live dev server is running. The user is watching the browser RIGHT NOW.

When building App.tsx, write VISIBLE WIREFRAME STUBS for each section — not
empty divs, not "Loading...", but realistic placeholder blocks that show the
layout. Each stub should:
- Have a dashed border and light gray background
- Show the name of the component (e.g. "SearchBar", "ProductCard")
- Approximate the size and position of the real component
- Use a unique comment marker like {/* STUB:SearchBar */} ... {/* END:SearchBar */}
  so children can find and replace their stub.

Example stub for a search bar:
  {/* STUB:SearchBar */}
  <div style={{ border: '2px dashed #ccc', borderRadius: 8, padding: '12px 16px',
    background: '#f5f5f5', color: '#999', fontSize: 14 }}>
    🔍 SearchBar — type to filter products...
  </div>
  {/* END:SearchBar */}

Children will replace everything between STUB and END markers with the real
component. The user watches stubs morph into real components one by one.
"""

    PACKAGE_JSON = '{"name":"morph-app","private":true,"version":"0.0.1","type":"module","scripts":{"dev":"vite"},"dependencies":{"react":"^18.2.0","react-dom":"^18.2.0"},"devDependencies":{"@types/react":"^18.2.0","@types/react-dom":"^18.2.0","@vitejs/plugin-react":"^4.2.0","typescript":"^5.3.0","vite":"^5.0.0"}}'

    TSCONFIG_JSON = '{"compilerOptions":{"target":"ES2020","useDefineForClassFields":true,"lib":["ES2020","DOM","DOM.Iterable"],"module":"ESNext","skipLibCheck":true,"moduleResolution":"bundler","resolveJsonModule":true,"isolatedModules":true,"noEmit":true,"jsx":"react-jsx","strict":true,"noUnusedLocals":false,"noUnusedParameters":false},"include":["src"]}'

    INDEX_HTML = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/><title>Morph App</title></head><body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>'

    MAIN_TSX = "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\n\nReactDOM.createRoot(document.getElementById('root')!).render(\n  <React.StrictMode><App /></React.StrictMode>\n);\n"

    VITE_CONFIG = "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\nexport default defineConfig({ plugins: [react()] });\n"

    def __init__(self, model="claude-sonnet-4-6", project_root=None, max_depth=2, port=5173):
        self.model = model
        self.max_depth = max_depth
        self.project_root = project_root or tempfile.mkdtemp(prefix="morph_")
        self.client = anthropic.Anthropic()
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.root: AgentNode | None = None
        self._print_lock = threading.Lock()
        self._vite_process = None
        self._port = port

    def _print(self, msg):
        with self._print_lock:
            print(msg)

    def _exec_fs(self, name, input):
        root = self.project_root
        if name == "read_file":
            fpath = os.path.join(root, input["file_path"])
            if os.path.isdir(fpath):
                return f"Directory: {os.listdir(fpath)}"
            if os.path.exists(fpath):
                with open(fpath) as f:
                    return f.read() or "(empty)"
            return f"Not found: {input['file_path']}"
        elif name == "append_to_file":
            if "content" not in input:
                return "Error: missing content."
            fpath = os.path.join(root, input["file_path"])
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "a") as f:
                f.write(input["content"])
            return f"Appended to {input['file_path']}."
        elif name == "replace_text":
            if "old_text" not in input or "new_text" not in input:
                return "Error: missing old_text/new_text."
            fpath = os.path.join(root, input["file_path"])
            if not os.path.exists(fpath):
                return f"Not found: {input['file_path']}"
            with open(fpath) as f:
                content = f.read()
            if input["old_text"] not in content:
                return f"old_text not found in {input['file_path']}."
            with open(fpath, "w") as f:
                f.write(content.replace(input["old_text"], input["new_text"], 1))
            return f"Replaced in {input['file_path']}."
        return "Unknown tool."

    def _run_turn(self, node, user_message, depth=0, is_initial=True):
        indent = "  " * depth
        self._print(f"{indent}[{node.name}] {'Building' if is_initial else 'Modifying'}...")

        node.messages.append({"role": "user", "content": user_message})

        if depth >= self.max_depth and is_initial:
            tools = [t for t in self.AGENT_TOOLS if t["name"] not in ("fork_batch", "delegate_to_child", "wait_all")]
        else:
            tools = self.AGENT_TOOLS

        pending_futures = {}
        pending_forks = []
        is_done = False

        while not is_done:
            response = self.client.messages.create(
                model=self.model, max_tokens=4096,
                system=self.SYSTEM_PROMPT, tools=tools, messages=node.messages,
                cache_control={"type": "ephemeral"},
            )
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if response.stop_reason == "end_turn" and not tool_use_blocks:
                node.messages.append({"role": "assistant", "content": response.content})
                break
            if not tool_use_blocks:
                break

            node.messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            pending_forks.clear()

            for block in tool_use_blocks:
                if block.name in ("read_file", "append_to_file", "replace_text"):
                    result = self._exec_fs(block.name, block.input)
                    self._print(f"{indent}  [{block.name}] {block.input.get('file_path', '?')[:50]}")
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})

                elif block.name == "fork_batch":
                    children_to_fork = block.input.get("children", [])
                    task_ids = []
                    for child_input in children_to_fork:
                        task_id = str(uuid4())[:8]
                        n = child_input.get("name", "unknown")
                        self._print(f"{indent}  -> Fork: {n} [{task_id}]")
                        pending_forks.append((task_id, child_input))
                        task_ids.append({"name": n, "task_id": task_id})
                    self._print(f"{indent}  >> Batched {len(children_to_fork)} forks")
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"forked": task_ids})})

                elif block.name == "delegate_to_child":
                    child_name = block.input["child_name"]
                    request = block.input["request"]
                    if child_name in node.children:
                        task_id = str(uuid4())[:8]
                        self._print(f"{indent}  -> Delegate: {child_name} [{task_id}]")
                        future = self.executor.submit(
                            self._run_turn, node.children[child_name],
                            f"Modification: {request}\n\nRead App.tsx or your file, make the change with replace_text, done().",
                            depth + 1, False,
                        )
                        pending_futures[task_id] = (future, {"name": child_name})
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"task_id": task_id})})
                    else:
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": f"No child '{child_name}'. Available: {list(node.children.keys())}", "is_error": True})

                elif block.name == "wait_all":
                    if pending_futures:
                        self._print(f"{indent}  <- Waiting for {len(pending_futures)}...")
                        results = []
                        for tid, (future, info) in list(pending_futures.items()):
                            future.result()
                            self._print(f"{indent}  <- Done: {info['name']}")
                            results.append({"name": info["name"], "success": True})
                        pending_futures.clear()
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"results": results})})
                    else:
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "No pending."})

                elif block.name == "done":
                    is_done = True
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Done."})

            node.messages.append({"role": "user", "content": tool_results})

            for task_id, fork_input in pending_forks:
                child_name = fork_input.get("name", "unknown")
                child_path = fork_input.get("file_path", "src/App.tsx")
                child_task = fork_input.get("task", f"Implement {child_name}.")

                child_node = AgentNode(name=child_name, messages=list(node.messages))
                node.children[child_name] = child_node

                self._print(f"{indent}  -> Forking: {child_name}")
                future = self.executor.submit(
                    self._run_turn, child_node,
                    (
                        f"You are forked to implement: {child_name}\n"
                        f"File: {child_path}\n"
                        f"Task: {child_task}\n\n"
                        f"Find the stub markers {{/* STUB:{child_name} */}} ... {{/* END:{child_name} */}} "
                        f"in App.tsx (or read your target file). Replace the entire stub block "
                        f"(including markers) with the real implementation.\n\n"
                        f"If you're writing a separate component file, also update App.tsx to "
                        f"import and use your component instead of the stub.\n\n"
                        f"done() when finished."
                    ),
                    depth + 1, True,
                )
                pending_futures[task_id] = (future, fork_input)
            pending_forks.clear()

        for tid, (future, info) in pending_futures.items():
            future.result()

        self._print(f"{indent}[{node.name}] Done.")

    def _scaffold(self):
        for name, content in [
            ("package.json", self.PACKAGE_JSON), ("tsconfig.json", self.TSCONFIG_JSON),
            ("index.html", self.INDEX_HTML), ("vite.config.ts", self.VITE_CONFIG),
        ]:
            with open(os.path.join(self.project_root, name), "w") as f:
                f.write(content)
        main_path = os.path.join(self.project_root, "src", "main.tsx")
        if not os.path.exists(main_path):
            os.makedirs(os.path.dirname(main_path), exist_ok=True)
            with open(main_path, "w") as f:
                f.write(self.MAIN_TSX)
        subprocess.run(["npm", "install", "--silent"], cwd=self.project_root, capture_output=True, timeout=60)

    def _start_vite(self):
        if self._vite_process and self._vite_process.poll() is None:
            return
        self._vite_process = subprocess.Popen(
            ["npx", "vite", "--host", "--port", str(self._port)],
            cwd=self.project_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        self._print(f"Vite running at http://localhost:{self._port}")

    def _stop_vite(self):
        if self._vite_process and self._vite_process.poll() is None:
            self._vite_process.terminate()
            self._vite_process.wait()

    # ── Public API ──

    def build(self, task):
        t0 = time.monotonic()
        self.root = AgentNode(name="architect")
        self._scaffold()
        self._start_vite()

        message = (
            f"{task}\n\n"
            "You are the architect. A live dev server is running — the user is watching NOW.\n\n"
            "STEP 1 — WIREFRAME (do this in your FIRST tool-use response):\n"
            "In a SINGLE response, call append_to_file for ALL of these:\n"
            "- src/types/index.ts (shared types)\n"
            "- src/utils/mockProducts.ts (mock data)\n"
            "- src/hooks/useProducts.ts (the custom hook — write it yourself)\n"
            "- src/App.tsx — a COMPLETE page with WIREFRAME STUBS for every component\n\n"
            "Each stub in App.tsx should:\n"
            "- Have a dashed border, light gray background, and component name visible\n"
            "- Approximate the real size and position\n"
            "- Be wrapped in {{/* STUB:ComponentName */}} ... {{/* END:ComponentName */}} markers\n\n"
            "STEP 2 — FORK ALL CHILDREN AT ONCE:\n"
            "Call fork_batch with an array of ALL children. One tool call, all children.\n"
            "Each child replaces its stub in App.tsx with a real component file + import.\n"
            "Then call wait_all() and done().\n\n"
            "CRITICAL: You must have exactly 3 responses:\n"
            "  Response 1: append_to_file × 4 (types, utils, hook, App.tsx wireframe)\n"
            "  Response 2: fork_batch (ALL children in one call)\n"
            "  Response 3: wait_all() + done()\n\n"
            "DO NOT verify children's work. DO NOT read files after wait_all."
        )

        self._run_turn(self.root, message, depth=0, is_initial=True)
        print(f"\nBuilt in {time.monotonic() - t0:.1f}s")
        print(f"Open http://localhost:{self._port}")
        return self

    def validate(self):
        result = subprocess.run(["npx", "tsc", "--noEmit"], cwd=self.project_root, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        errors = output.count("error TS")
        if result.returncode == 0:
            print("tsc: PASS")
            return True
        print(f"tsc: FAIL ({errors} errors)")
        for line in output.strip().split("\n")[:20]:
            print(f"  {line}")
        return False

    def modify(self, request):
        if not self.root:
            raise RuntimeError("Call build() first.")
        t0 = time.monotonic()
        children = list(self.root.children.keys())
        message = (
            f"Modification request:\n\n{request}\n\n"
            f"Child agents: {children}\n"
            f"Delegate to children as needed. wait_all(), done().\n"
            f"DO NOT verify children's work.\n"
            f"Dev server is live — make incremental replace_text changes."
        )
        self._run_turn(self.root, message, depth=0, is_initial=False)
        print(f"\nModified in {time.monotonic() - t0:.1f}s")
        return self

    def tree(self):
        def _p(node, indent=0):
            print(f"{'  ' * indent}{node.name} ({len(node.messages)} msgs, {len(node.children)} children)")
            for c in node.children.values():
                _p(c, indent + 1)
        if self.root:
            _p(self.root)

    def stop(self):
        self._stop_vite()
        self.executor.shutdown(wait=False)

    @property
    def path(self):
        return self.project_root


if __name__ == "__main__":
    app = Morph()

    print("=" * 60)
    print("WIREFRAME MORPH")
    print("=" * 60)
    print(f"Project: {app.path}")
    print(f"Open http://localhost:5173 NOW — watch it build.\n")

    app.build(
        "Build a React dashboard that displays a list of products. Features:\n"
        "- A search bar that filters products by name in real time\n"
        "- Sort buttons to sort by name, price, or rating\n"
        "- A product card grid showing name, price, rating, and an image\n"
        "- A loading spinner while data is being fetched\n"
        "- Use a custom hook for the data fetching and filtering logic\n"
        "- TypeScript types for the Product model\n"
        "- The product data can be hardcoded as mock data in a utils file"
    )

    print("\n--- Validate ---")
    app.validate()

    print("\n--- Agent Tree ---")
    app.tree()

    print(f"\nApp live at http://localhost:5173")
    print("Type modifications. 'validate', 'tree', 'quit' also work.\n")

    while True:
        try:
            cmd = input("morph> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not cmd:
            continue
        parts = cmd.split(None, 1)
        command = parts[0].lower()
        if command in ("quit", "exit"):
            break
        elif command == "tree":
            app.tree()
        elif command == "validate":
            app.validate()
        else:
            app.modify(cmd)
            app.validate()

    app.stop()
    print(f"\nProject at: {app.path}")
