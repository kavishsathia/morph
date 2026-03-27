"""
Live Morph Experiment

Vite dev server runs in a background thread the entire time. Agents write files
while the server is live — Vite HMR picks up changes instantly and the browser
updates in real time. The user sees the UI morph as each child agent finishes.

Agents are instructed to make small, incremental changes (one replace_text at a
time) so HMR can update the browser between each write, creating a visible
morphing effect.
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
    file_path: str = ""


class Morph:
    AGENT_TOOLS = [
        {"name": "read_file", "description": "Read a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
        {"name": "append_to_file", "description": "Append to a file. Creates dirs if needed.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}},
        {"name": "replace_text", "description": "Replace text in a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["file_path", "old_text", "new_text"]}},
        {
            "name": "fork_and_assign",
            "description": "Fork your conversation to a child agent. It inherits your full history. Returns immediately.",
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
fork child agents, delegate to existing children, and signal completion.

When you fork a child, it inherits your full conversation.
When you delegate_to_child, the child has its history from the initial build.

Project layout: src/components/Name/Name.tsx + index.ts, src/hooks/useX.ts,
src/utils/x.ts, src/types/index.ts, src/App.tsx.

Use .tsx for JSX, .ts for logic. Include imports. Use inline styles.
Call done() when finished.

IMPORTANT — LAZY LOADING & ERROR BOUNDARIES:
A live dev server is running. Components may not exist on disk yet when App.tsx
first renders. To handle this gracefully:
- In App.tsx, import components with React.lazy():
    const ProductCard = React.lazy(() => import('./components/ProductCard'));
- Wrap lazy components in <Suspense fallback={<div>Loading...</div>}>
- Also wrap in an ErrorBoundary so if a component hasn't been written yet,
  the app shows a placeholder instead of crashing.
- Write a simple ErrorBoundary component in src/components/ErrorBoundary.tsx
  that catches errors and renders a fallback.

IMPORTANT — INCREMENTAL CHANGES:
Every file write triggers a browser update via HMR. To create a smooth morphing:
- When MODIFYING existing files, make ONE small replace_text at a time.
- Each replace_text should be a meaningful, self-contained change.
- When CREATING new files, write the whole file at once with append_to_file.
"""

    PACKAGE_JSON = '{"name":"morph-app","private":true,"version":"0.0.1","type":"module","scripts":{"dev":"vite"},"dependencies":{"react":"^18.2.0","react-dom":"^18.2.0"},"devDependencies":{"@types/react":"^18.2.0","@types/react-dom":"^18.2.0","@vitejs/plugin-react":"^4.2.0","typescript":"^5.3.0","vite":"^5.0.0"}}'

    TSCONFIG_JSON = '{"compilerOptions":{"target":"ES2020","useDefineForClassFields":true,"lib":["ES2020","DOM","DOM.Iterable"],"module":"ESNext","skipLibCheck":true,"moduleResolution":"bundler","resolveJsonModule":true,"isolatedModules":true,"noEmit":true,"jsx":"react-jsx","strict":true,"noUnusedLocals":false,"noUnusedParameters":false},"include":["src"]}'

    INDEX_HTML = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/><title>Morph App</title></head><body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>'

    MAIN_TSX = "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\n\nReactDOM.createRoot(document.getElementById('root')!).render(\n  <React.StrictMode><App /></React.StrictMode>\n);\n"

    VITE_CONFIG = "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\nexport default defineConfig({ plugins: [react()] });\n"

    def __init__(self, model: str = "claude-sonnet-4-6", project_root: str | None = None, max_depth: int = 2, port: int = 5173):
        self.model = model
        self.max_depth = max_depth
        self.project_root = project_root or tempfile.mkdtemp(prefix="morph_")
        self.client = anthropic.Anthropic()
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.root: AgentNode | None = None
        self._print_lock = threading.Lock()
        self._vite_process: subprocess.Popen | None = None
        self._port = port

    def _print(self, msg: str):
        with self._print_lock:
            print(msg)

    def _exec_fs(self, name: str, input: dict) -> str:
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

    def _run_turn(self, node: AgentNode, user_message: str, depth: int = 0,
                  is_initial: bool = True) -> None:
        indent = "  " * depth
        self._print(f"{indent}[{node.name}] {'Building' if is_initial else 'Modifying'}...")

        node.messages.append({"role": "user", "content": user_message})

        if depth >= self.max_depth and is_initial:
            tools = [t for t in self.AGENT_TOOLS if t["name"] not in ("fork_and_assign", "delegate_to_child", "wait_all")]
        else:
            tools = self.AGENT_TOOLS

        pending_futures: dict[str, tuple[Future, dict]] = {}
        pending_forks: list[tuple[str, dict]] = []
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

                elif block.name == "fork_and_assign":
                    task_id = str(uuid4())[:8]
                    name = block.input.get("name", "unknown")
                    self._print(f"{indent}  -> Fork: {name} [{task_id}]")
                    pending_forks.append((task_id, block.input))
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"task_id": task_id})})

                elif block.name == "delegate_to_child":
                    child_name = block.input["child_name"]
                    request = block.input["request"]
                    if child_name in node.children:
                        task_id = str(uuid4())[:8]
                        self._print(f"{indent}  -> Delegate: {child_name} [{task_id}]")
                        child_node = node.children[child_name]
                        future = self.executor.submit(
                            self._run_turn, child_node,
                            f"Modification: {request}\n\nMake small incremental changes. Read your file, then make ONE replace_text at a time. done() when finished.",
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
                child_path = fork_input.get("file_path", "src/unknown.tsx")
                child_task = fork_input.get("task", f"Implement {child_name}.")

                child_node = AgentNode(name=child_name, messages=list(node.messages), file_path=child_path)
                node.children[child_name] = child_node

                self._print(f"{indent}  -> Forking: {child_name} -> {child_path}")
                future = self.executor.submit(
                    self._run_turn, child_node,
                    f"You are forked to implement: {child_name}\nWrite to: {child_path}\nTask: {child_task}\n\nImplement, then done().",
                    depth + 1, True,
                )
                pending_futures[task_id] = (future, fork_input)
            pending_forks.clear()

        for tid, (future, info) in pending_futures.items():
            future.result()

        self._print(f"{indent}[{node.name}] Done.")

    # ──────────────────────────────────────────
    # Vite management
    # ──────────────────────────────────────────

    def _scaffold(self):
        """Write project scaffolding files."""
        for name, content in [
            ("package.json", self.PACKAGE_JSON),
            ("tsconfig.json", self.TSCONFIG_JSON),
            ("index.html", self.INDEX_HTML),
            ("vite.config.ts", self.VITE_CONFIG),
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
        """Start Vite in background."""
        if self._vite_process and self._vite_process.poll() is None:
            return  # already running

        self._vite_process = subprocess.Popen(
            ["npx", "vite", "--host", "--port", str(self._port)],
            cwd=self.project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Give Vite a moment to start
        time.sleep(2)
        self._print(f"Vite running at http://localhost:{self._port}")

    def _stop_vite(self):
        """Stop Vite."""
        if self._vite_process and self._vite_process.poll() is None:
            self._vite_process.terminate()
            self._vite_process.wait()
            self._print("Vite stopped.")

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    def build(self, task: str) -> "Morph":
        """Generate the project. Vite starts automatically — watch the browser."""
        t0 = time.monotonic()
        self.root = AgentNode(name="architect")

        # Scaffold and start Vite BEFORE generation so HMR catches writes live
        self._scaffold()
        self._start_vite()

        message = (
            f"{task}\n\n"
            "Don't write component code yourself.\n"
            "1. Plan the structure. Write shared types (src/types/index.ts) and any utils.\n"
            "2. Write an ErrorBoundary component (src/components/ErrorBoundary.tsx) that\n"
            "   catches render errors and shows a placeholder. It should be a class component\n"
            "   with componentDidCatch, rendering props.children normally and a fallback on error.\n"
            "3. Write App.tsx YOURSELF using React.lazy() + Suspense + ErrorBoundary for each\n"
            "   component. This way, components that don't exist yet show placeholders instead\n"
            "   of crashing. Example:\n"
            "     const ProductCard = React.lazy(() => import('./components/ProductCard'));\n"
            "     <ErrorBoundary><Suspense fallback={<div>Loading...</div>}><ProductCard /></Suspense></ErrorBoundary>\n"
            "4. Fork a child for each component and hook (NOT App.tsx — you wrote that already).\n"
            "5. Fork ALL at once, wait_all(), done().\n\n"
            "Code will be validated with tsc --noEmit. All imports must resolve.\n"
            "DO NOT verify children's work after wait_all(). Just done().\n\n"
            "A live dev server is running — components will appear in the browser\n"
            "one by one as children write their files. Lazy loading ensures no crashes."
        )

        self._run_turn(self.root, message, depth=0, is_initial=True)
        print(f"\nBuilt in {time.monotonic() - t0:.1f}s")
        print(f"Open http://localhost:{self._port} to see the app.")
        return self

    def validate(self) -> bool:
        """Run tsc --noEmit."""
        result = subprocess.run(["npx", "tsc", "--noEmit"], cwd=self.project_root, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        errors = output.count("error TS")
        if result.returncode == 0:
            print(f"tsc: PASS")
            return True
        else:
            print(f"tsc: FAIL ({errors} errors)")
            for line in output.strip().split("\n")[:20]:
                print(f"  {line}")
            return False

    def modify(self, request: str) -> "Morph":
        """Send a modification. Vite HMR shows changes live in the browser."""
        if not self.root:
            raise RuntimeError("Call build() first.")

        t0 = time.monotonic()
        children = list(self.root.children.keys())
        message = (
            f"Modification request:\n\n{request}\n\n"
            f"Child agents: {children}\n"
            f"Delegate to children as needed. wait_all(), done().\n"
            f"DO NOT verify children's work.\n\n"
            f"IMPORTANT: The dev server is live with HMR. Make small, incremental "
            f"replace_text changes so the user sees the UI morph step by step."
        )
        self._run_turn(self.root, message, depth=0, is_initial=False)
        print(f"\nModified in {time.monotonic() - t0:.1f}s")
        return self

    def tree(self):
        """Print the agent tree."""
        def _print(node: AgentNode, indent: int = 0):
            prefix = "  " * indent
            print(f"{prefix}{node.name} ({len(node.messages)} msgs, {len(node.children)} children)")
            for child in node.children.values():
                _print(child, indent + 1)
        if self.root:
            _print(self.root)

    def stop(self):
        """Stop Vite and clean up."""
        self._stop_vite()
        self.executor.shutdown(wait=False)

    @property
    def path(self) -> str:
        return self.project_root


# ──────────────────────────────────────────────
# Demo
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app = Morph()

    print("=" * 60)
    print("LIVE MORPH")
    print("=" * 60)
    print(f"Project: {app.path}\n")

    app.build(
        "Build a React dashboard that displays a list of products. Features:\n"
        "- A search bar that filters products by name in real time\n"
        "- Sort buttons to sort by name, price, or rating\n"
        "- A product card component showing name, price, rating, and an image\n"
        "- A loading spinner while data is being fetched\n"
        "- Use a custom hook for the data fetching and filtering logic\n"
        "- TypeScript types for the Product model\n"
        "- The product data can be hardcoded as mock data in a utils file"
    )

    print("\n--- Validate ---")
    app.validate()

    print("\n--- Agent Tree ---")
    app.tree()

    print("\n" + "=" * 60)
    print(f"App live at http://localhost:5173")
    print("Type modifications below. 'validate', 'tree', 'quit' also work.\n")

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
