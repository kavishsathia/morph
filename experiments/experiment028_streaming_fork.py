"""
Streaming Fork Experiment

Same as experiment027 (implicit fork, auto-detected imports) but with streaming
tool execution. Tool calls are executed the MOMENT they finish streaming — not
after the full API response completes. This means:

- Root streams append_to_file for types.ts → executed immediately, while the
  model is still streaming the next tool call (utils.ts)
- When App.tsx is written mid-stream, stubs are created and auto-fork can begin
  BEFORE the root's API call even finishes
- Files appear on disk (and in the browser via HMR) as fast as the model can
  stream them, not batched at the end of each response

## Experiment Results (2026-03-27)

Model: claude-sonnet-4-6
Root task: Product dashboard.

### Timing Summary

    Built in:         130s
    tsc --noEmit:     PASS
    Auto-forked:      7 agents (6 from root + 1 recursive ProductCard)

### Auto-Emerged Agent Tree

    root (15 msgs, 6 children)
      SearchBar (20 msgs)
      SortControls (20 msgs)
      ProductGrid (20 msgs, 1 child)
        ProductCard (25 msgs)       <- recursive auto-fork
      LoadingSpinner (20 msgs)
      ErrorMessage (20 msgs)
      ResultsSummary (20 msgs)      <- agent invented this

### Key Findings

- Streaming execution works — tool calls fire mid-stream. But the speed
  improvement over exp027 is marginal (~3s). The bottleneck is model
  thinking time, not tool execution latency.
- The real value of streaming is UX, not speed: files hit disk slightly
  earlier, so HMR updates appear sooner during the stream.
- Recursive auto-fork still works: ProductGrid -> ProductCard detected
  and forked immediately when ProductGrid finishes (not waiting for siblings).
- Agent invented ResultsSummary on its own (not in the task spec).
- Modification ("add dark mode toggle") works — root reads and modifies
  App.tsx and types directly.
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json
import os
import re
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
    # Agents only get filesystem tools. No fork, no spawn, no delegate.
    AGENT_TOOLS = [
        {"name": "read_file", "description": "Read a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
        {"name": "append_to_file", "description": "Append to a file. Creates dirs if needed.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}},
        {"name": "replace_text", "description": "Replace text in a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["file_path", "old_text", "new_text"]}},
        {"name": "done", "description": "Signal you are finished.", "input_schema": {"type": "object", "properties": {}}},
    ]

    SYSTEM_PROMPT = """\
You are a senior React/TypeScript developer. Write code directly to files.

Tools: read_file, append_to_file, replace_text, done.

You are building ONE component or module. Write it to your assigned file.
Use inline styles. Include proper imports. Call done() when finished.

If you need child components, just IMPORT and USE them in your JSX as if they
already exist. You don't need to implement them — other agents will handle that
automatically. Just write the import and use the component with the props you need.

Example: if you're writing a Dashboard and need a SearchBar, just write:
  import SearchBar from './components/SearchBar';
  ...
  <SearchBar query={query} onChange={setQuery} placeholder="Search..." />

The system will detect that SearchBar doesn't exist and create it for you.
"""

    PACKAGE_JSON = '{"name":"morph-app","private":true,"version":"0.0.1","type":"module","scripts":{"dev":"vite"},"dependencies":{"react":"^18.2.0","react-dom":"^18.2.0"},"devDependencies":{"@types/react":"^18.2.0","@types/react-dom":"^18.2.0","@vitejs/plugin-react":"^4.2.0","typescript":"^5.3.0","vite":"^5.0.0"}}'
    TSCONFIG_JSON = '{"compilerOptions":{"target":"ES2020","useDefineForClassFields":true,"lib":["ES2020","DOM","DOM.Iterable"],"module":"ESNext","skipLibCheck":true,"moduleResolution":"bundler","resolveJsonModule":true,"isolatedModules":true,"noEmit":true,"jsx":"react-jsx","strict":true,"noUnusedLocals":false,"noUnusedParameters":false},"include":["src"]}'
    INDEX_HTML = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/><title>Morph App</title></head><body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>'
    MAIN_TSX = "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\n\nReactDOM.createRoot(document.getElementById('root')!).render(\n  <React.StrictMode><App /></React.StrictMode>\n);\n"
    VITE_CONFIG = "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\nexport default defineConfig({ plugins: [react()] });\n"

    # Known imports that should NOT be auto-forked
    KNOWN_MODULES = {
        "react", "react-dom", "react-dom/client", "react/jsx-runtime",
    }

    def __init__(self, model="claude-sonnet-4-6", project_root=None, max_depth=3, port=5173):
        self.model = model
        self.max_depth = max_depth
        self.project_root = project_root or tempfile.mkdtemp(prefix="morph_")
        self.client = anthropic.Anthropic()
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.root: AgentNode | None = None
        self._print_lock = threading.Lock()
        self._vite_process = None
        self._port = port
        # Track what files exist (to detect undefined components)
        self._written_files: set[str] = set()
        self._written_lock = threading.Lock()
        # Track agents in progress to avoid double-forking
        self._pending_components: set[str] = set()
        self._pending_lock = threading.Lock()

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
            with self._written_lock:
                self._written_files.add(input["file_path"])
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

    def _write_stub(self, item: dict) -> None:
        """Write a placeholder stub file so Vite doesn't crash on the import."""
        file_path = item["file_path"]
        component_name = item["name"]

        # Don't overwrite if it already exists
        full_path = os.path.join(self.project_root, file_path)
        if os.path.exists(full_path):
            return

        with self._written_lock:
            if file_path in self._written_files:
                return
            self._written_files.add(file_path)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        if file_path.endswith(".ts") and "hook" in file_path.lower():
            # Hook stub
            stub = (
                f"// Stub: {component_name} — being implemented by an agent\n"
                f"export function {component_name}() {{\n"
                f"  return {{}};\n"
                f"}}\n"
                f"export default {component_name};\n"
            )
        else:
            # Component stub — renders a visible placeholder
            stub = (
                "import React from 'react';\n\n"
                f"const {component_name}: React.FC<any> = () => (\n"
                "  <div style={{\n"
                "    border: '2px dashed #d0d0d0',\n"
                "    borderRadius: 8,\n"
                "    padding: 16,\n"
                "    margin: 8,\n"
                "    background: '#f8f8f8',\n"
                "    color: '#999',\n"
                "    fontSize: 14,\n"
                "    textAlign: 'center' as const,\n"
                "  }}>\n"
                f"    Building {component_name}...\n"
                "  </div>\n"
                ");\n\n"
                f"export default {component_name};\n"
            )

        with open(full_path, "w") as f:
            f.write(stub)
        self._print(f"    [stub] {file_path} — placeholder for {component_name}")

    def _detect_undefined_imports(self, file_path: str, content: str) -> list[dict]:
        """Scan written code for imports of local files that don't exist yet."""
        undefined = []

        # Match: import X from './components/X' or import { X } from './hooks/useX'
        import_pattern = re.compile(
            r"""import\s+(?:(?:\{[^}]*\}|\w+)(?:\s*,\s*(?:\{[^}]*\}|\w+))*)\s+from\s+['"](\.[^'"]+)['"]"""
        )

        for match in import_pattern.finditer(content):
            import_path = match.group(1)

            # Skip known modules
            if any(import_path.startswith(k) for k in self.KNOWN_MODULES):
                continue

            # Resolve the import to possible file paths
            # ./components/SearchBar -> src/components/SearchBar.tsx, src/components/SearchBar/index.ts, etc.
            base_dir = os.path.dirname(file_path)
            rel_path = os.path.normpath(os.path.join(base_dir, import_path))

            possible_files = [
                f"{rel_path}.tsx",
                f"{rel_path}.ts",
                f"{rel_path}/index.tsx",
                f"{rel_path}/index.ts",
            ]

            with self._written_lock:
                exists = any(f in self._written_files for f in possible_files)

            # Also check filesystem
            if not exists:
                exists = any(
                    os.path.exists(os.path.join(self.project_root, f))
                    for f in possible_files
                )

            if not exists:
                # Extract component name from import
                full_match = match.group(0)
                # Try to get the default import name
                name_match = re.match(r"import\s+(\w+)", full_match)
                if not name_match:
                    # Named import
                    name_match = re.match(r"import\s+\{\s*(\w+)", full_match)
                if name_match:
                    component_name = name_match.group(1)
                    target_file = f"{rel_path}.tsx" if not rel_path.startswith("src/hooks") else f"{rel_path}.ts"

                    undefined.append({
                        "name": component_name,
                        "import_path": import_path,
                        "file_path": target_file,
                        "used_in": file_path,
                    })

        return undefined

    def _extract_usage_context(self, content: str, component_name: str) -> str:
        """Extract how a component is used in JSX to infer its props."""
        # Find JSX usage: <ComponentName prop1={...} prop2="..." />
        pattern = re.compile(
            rf"<{component_name}\s([^>]*?)(?:/>|>[\s\S]*?</{component_name}>)",
            re.MULTILINE,
        )
        usages = pattern.findall(content)
        if usages:
            return f"Used as: <{component_name} {usages[0].strip()} />"
        return f"Used as: <{component_name} />"

    def _run_agent(self, node: AgentNode, user_message: str, depth: int = 0) -> list[dict]:
        """Run an agent with streaming — execute tool calls as they complete mid-stream."""
        indent = "  " * depth
        self._print(f"{indent}[{node.name}] Building...")

        node.messages.append({"role": "user", "content": user_message})
        all_undefined: list[dict] = []
        is_done = False

        while not is_done:
            # Track tool calls as they stream in
            tool_calls_in_progress: dict[int, dict] = {}  # index -> {id, name, input_json}
            tool_results = []
            any_tools = False

            with self.client.messages.stream(
                model=self.model, max_tokens=4096,
                system=self.SYSTEM_PROMPT, tools=self.AGENT_TOOLS,
                messages=node.messages,
                cache_control={"type": "ephemeral"},
            ) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            tool_calls_in_progress[event.index] = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input_json": "",
                            }

                    elif event.type == "content_block_delta":
                        if event.delta.type == "input_json_delta":
                            idx = event.index
                            if idx in tool_calls_in_progress:
                                tool_calls_in_progress[idx]["input_json"] += event.delta.partial_json

                    elif event.type == "content_block_stop":
                        idx = event.index
                        if idx in tool_calls_in_progress:
                            tc = tool_calls_in_progress.pop(idx)
                            tool_id = tc["id"]
                            tool_name = tc["name"]
                            try:
                                tool_input = json.loads(tc["input_json"]) if tc["input_json"] else {}
                            except json.JSONDecodeError:
                                tool_input = {}

                            any_tools = True

                            # EXECUTE IMMEDIATELY — while other tool calls are still streaming
                            if tool_name in ("read_file", "append_to_file", "replace_text"):
                                result = self._exec_fs(tool_name, tool_input)
                                fp = tool_input.get("file_path", "?")
                                self._print(f"{indent}  [{tool_name}] {fp[:50]}")
                                tool_results.append({"type": "tool_result", "tool_use_id": tool_id, "content": result})

                                # Detect undefined imports and stub RIGHT NOW
                                if tool_name in ("append_to_file", "replace_text"):
                                    written_path = os.path.join(self.project_root, fp)
                                    if os.path.exists(written_path):
                                        with open(written_path) as f:
                                            written_content = f.read()
                                        undefined = self._detect_undefined_imports(fp, written_content)
                                        for item in undefined:
                                            self._write_stub(item)
                                        all_undefined.extend(undefined)

                            elif tool_name == "done":
                                is_done = True
                                tool_results.append({"type": "tool_result", "tool_use_id": tool_id, "content": "Done."})

                final_message = stream.get_final_message()

            if not any_tools:
                node.messages.append({"role": "assistant", "content": final_message.content})
                break

            node.messages.append({"role": "assistant", "content": final_message.content})
            node.messages.append({"role": "user", "content": tool_results})

        self._print(f"{indent}[{node.name}] Done.")
        return all_undefined

    def _auto_fork_undefined(self, parent_node: AgentNode, undefined: list[dict], depth: int) -> None:
        """Auto-fork agents for undefined components. Runs them in parallel."""
        # Deduplicate and filter already-pending
        to_fork = []
        for item in undefined:
            with self._pending_lock:
                if item["name"] not in self._pending_components:
                    self._pending_components.add(item["name"])
                    to_fork.append(item)

        if not to_fork:
            return

        indent = "  " * depth
        self._print(f"{indent}>> Auto-forking {len(to_fork)} undefined components: {[i['name'] for i in to_fork]}")

        if depth >= self.max_depth:
            self._print(f"{indent}>> Max depth reached, skipping auto-fork")
            return

        futures: list[tuple[Future, dict, AgentNode]] = []

        for item in to_fork:
            child_name = item["name"]
            child_path = item["file_path"]
            used_in = item["used_in"]

            # Read the parent file to get usage context
            parent_file = os.path.join(self.project_root, used_in)
            usage_context = ""
            if os.path.exists(parent_file):
                with open(parent_file) as f:
                    content = f.read()
                usage_context = self._extract_usage_context(content, child_name)

            child_node = AgentNode(name=child_name, messages=list(parent_node.messages))
            parent_node.children[child_name] = child_node

            self._print(f"{indent}  -> Auto-fork: {child_name} -> {child_path}")

            # Read the stub content so the child doesn't need to
            stub_content = ""
            stub_path = os.path.join(self.project_root, child_path)
            if os.path.exists(stub_path):
                with open(stub_path) as f:
                    stub_content = f.read()

            task_msg = (
                f"Implement the component: {child_name}\n"
                f"Write to: {child_path}\n"
                f"{usage_context}\n\n"
                f"The stub file contains:\n```\n{stub_content}```\n\n"
                f"DO NOT read any files. You already have all the context you need.\n"
                f"You know the types, the project structure, and how this component is used.\n\n"
                f"In your FIRST response, call replace_text on {child_path} to replace the\n"
                f"ENTIRE stub content with your real implementation. Then done().\n"
                f"That's it — one replace_text, one done. Two tool calls total.\n\n"
                f"If you need sub-components, just import and use them — they'll be auto-created."
            )

            future = self.executor.submit(
                self._run_agent, child_node, task_msg, depth + 1,
            )
            futures.append((future, item, child_node))

        # Process children as they complete — fork their undefined imports immediately
        from concurrent.futures import as_completed
        future_to_info = {f: (item, child_node) for f, item, child_node in futures}

        for completed_future in as_completed(future_to_info):
            item, child_node = future_to_info[completed_future]
            child_undefined = completed_future.result()
            self._print(f"{indent}  <- Done: {item['name']}")

            # Fork any undefined imports from this child RIGHT NOW, don't wait for siblings
            if child_undefined:
                self._auto_fork_undefined(child_node, child_undefined, depth + 1)

    # ── Infrastructure ──

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
        # Write App.tsx stub so the browser shows something immediately
        app_path = os.path.join(self.project_root, "src", "App.tsx")
        with open(app_path, "w") as f:
            f.write(
                "import React from 'react';\n\n"
                "const App: React.FC = () => (\n"
                "  <div style={{\n"
                "    display: 'flex', alignItems: 'center', justifyContent: 'center',\n"
                "    minHeight: '100vh', background: '#f0f0f0', color: '#999',\n"
                "    fontFamily: 'system-ui', fontSize: 18,\n"
                "  }}>\n"
                "    Building your app...\n"
                "  </div>\n"
                ");\n\n"
                "export default App;\n"
            )
        # Pre-register
        with self._written_lock:
            self._written_files.add("src/main.tsx")
            self._written_files.add("src/App.tsx")
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

    def build(self, task: str) -> "Morph":
        t0 = time.monotonic()
        self.root = AgentNode(name="root")
        self._scaffold()
        self._start_vite()

        message = (
            f"{task}\n\n"
            "Write the app. Start with:\n"
            "1. src/types/index.ts — shared TypeScript types\n"
            "2. src/utils/mockProducts.ts — mock data\n"
            "3. src/hooks/useProducts.ts — the custom hook\n"
            "4. src/App.tsx — the main app component\n\n"
            "src/App.tsx already exists as a stub showing 'Building your app...'. \n"
            "Use replace_text to replace its ENTIRE content with your real App component.\n\n"
            "For App.tsx, import and use sub-components as if they exist.\n"
            "Don't implement them — just import and use them with the right props.\n"
            "Other agents will auto-implement any component you reference.\n\n"
            "Example: import SearchBar from './components/SearchBar';\n"
            "         <SearchBar query={query} onChange={setQuery} />\n\n"
            "Write types, utils, hook with append_to_file. Replace App.tsx with replace_text. Then done()."
        )

        # Run root agent
        undefined = self._run_agent(self.root, message, depth=0)

        # Auto-fork undefined components (recursively)
        if undefined:
            self._auto_fork_undefined(self.root, undefined, depth=1)

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

    def modify(self, request: str) -> "Morph":
        if not self.root:
            raise RuntimeError("Call build() first.")
        t0 = time.monotonic()

        # Find which child is most relevant, or delegate to root
        message = (
            f"Modification request:\n\n{request}\n\n"
            f"Read the relevant files, make changes with replace_text, done().\n"
            f"If you need new components, just import them — they'll be auto-created."
        )
        undefined = self._run_agent(self.root, message, depth=0)
        if undefined:
            self._auto_fork_undefined(self.root, undefined, depth=1)

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
    print("STREAMING FORK — MORPH")
    print("=" * 60)
    print(f"Project: {app.path}")
    print(f"Open http://localhost:5173 NOW\n")

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

    print("\n--- Agent Tree (auto-emerged) ---")
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
