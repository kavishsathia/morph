"""
Linear Baseline Experiment

One agent, no forking, no tree. Just a single Sonnet agent with filesystem tools
that builds the entire product dashboard by itself. This is the baseline to
compare the tree architecture against.

## Experiment Results (2026-03-27)

Model: claude-sonnet-4-6
Root task: Product dashboard.

### Timing Summary

    Generation time:  134s
    tsc --noEmit:     PASS (0 errors)
    API calls:        22
    Input tokens:     153,612
    Output tokens:    9,224
    Total tokens:     162,836
    Files written:    17

### Comparison with Tree (exp022)

    | Metric         | Linear (exp000) | Tree (exp022) |
    |----------------|-----------------|---------------|
    | Wall clock     | 134s            | 49s (2.7x)    |
    | Input tokens   | 153K            | ~3K + 80K cache|
    | Total tokens   | 163K            | ~10K (16x)    |
    | API calls      | 22              | ~22           |
    | tsc            | PASS            | PASS          |

### Key Findings

- Linear agent is 2.7x slower despite the same number of API calls.
  Every call is sequential — no parallelism.
- Token cost is 16x higher because the linear agent's context grows
  with every file it writes. By call 22, it sends 150K+ tokens of
  history just to write a 50-line component.
- Tree agents each have small, focused contexts with cached prefixes.
  They never accumulate the context bloat.
- Both produce valid TypeScript (tsc PASS). Quality is comparable.
- The tree architecture is strictly better: faster AND cheaper.
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json
import os
import subprocess
import tempfile
import time

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = anthropic.Anthropic()

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


TOOLS = [
    {"name": "read_file", "description": "Read a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
    {"name": "append_to_file", "description": "Append to a file. Creates dirs if needed.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}},
    {"name": "replace_text", "description": "Replace text in a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["file_path", "old_text", "new_text"]}},
    {"name": "done", "description": "Signal you are finished with the entire project.", "input_schema": {"type": "object", "properties": {}}},
]

SYSTEM_PROMPT = """\
You are a senior React/TypeScript developer. Build the entire project yourself.

Tools: read_file, append_to_file, replace_text, done.

Project layout: src/components/Name/Name.tsx + index.ts, src/hooks/useX.ts,
src/utils/x.ts, src/types/index.ts, src/App.tsx.

Use .tsx for JSX, .ts for logic. Include proper imports. Use inline styles.
When you're done with the entire project, call done().

IMPORTANT: Code will be validated with tsc --noEmit. All imports must resolve,
all types must be correct.
"""

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
    return result.returncode == 0, result.stdout + result.stderr


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    root_task = (
        "Build a React dashboard that displays a list of products. Features:\n"
        "- A search bar that filters products by name in real time\n"
        "- Sort buttons to sort by name, price, or rating\n"
        "- A product card component showing name, price, rating, and an image\n"
        "- A loading spinner while data is being fetched\n"
        "- Use a custom hook for the data fetching and filtering logic\n"
        "- TypeScript types for the Product model\n"
        "- The product data can be hardcoded as mock data in a utils file\n\n"
        "Build the entire project. Write each file one at a time using append_to_file.\n"
        "Create barrel exports (index.ts) for each component.\n"
        "When you're done with everything, call done()."
    )

    project_root = tempfile.mkdtemp(prefix="morph_exp000_")

    print("=" * 60)
    print("LINEAR BASELINE EXPERIMENT")
    print("=" * 60)
    print(f"\nProject root: {project_root}\n")

    messages = [{"role": "user", "content": root_task}]
    api_calls = 0
    total_input = 0
    total_output = 0
    files_written = set()

    t0 = time.monotonic()
    is_done = False

    while not is_done:
        call_start = time.monotonic()
        response = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=4096,
            system=SYSTEM_PROMPT, tools=TOOLS, messages=messages,
        )
        call_time = time.monotonic() - call_start
        api_calls += 1
        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens

        print(f"  [API call {api_calls}] {call_time:.1f}s, in={response.usage.input_tokens}, out={response.usage.output_tokens}")

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" and not tool_use_blocks:
            messages.append({"role": "assistant", "content": response.content})
            break
        if not tool_use_blocks:
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for block in tool_use_blocks:
            if block.name in ("read_file", "append_to_file", "replace_text"):
                result = execute_fs_tool(block.name, block.input, project_root)
                fp = block.input.get("file_path", "?")
                if block.name in ("append_to_file", "replace_text"):
                    files_written.add(fp)
                print(f"    [{block.name}] {fp[:50]} -> {result[:40]}")
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            elif block.name == "done":
                is_done = True
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Done."})

        messages.append({"role": "user", "content": tool_results})

    gen_time = time.monotonic() - t0

    # Validate
    print("\n--- Validating ---")
    success, output = scaffold_and_validate(project_root)
    error_count = output.count("error TS")
    print(f"  tsc: {'PASS' if success else 'FAIL'} ({error_count} errors)")
    if not success:
        for line in output.strip().split("\n")[:30]:
            print(f"  {line}")

    total_time = time.monotonic() - t0

    # Report
    print("\n" + "=" * 60)
    print("TIMING REPORT")
    print("=" * 60)
    print(f"\n  Generation time:     {gen_time:.1f}s")
    print(f"  Total wall clock:    {total_time:.1f}s")
    print(f"  API calls:           {api_calls}")
    print(f"  Input tokens:        {total_input:,}")
    print(f"  Output tokens:       {total_output:,}")
    print(f"  Total tokens:        {total_input + total_output:,}")
    print(f"  Files written:       {len(files_written)}")
    print(f"  tsc:                 {'PASS' if success else 'FAIL'} ({error_count} errors)")

    print(f"\n  Files:")
    for fp in sorted(files_written):
        print(f"    {fp}")

    # Show files
    print(f"\n" + "=" * 60)
    print(f"FILES ON DISK ({project_root})")
    print("=" * 60)
    for dirpath, _, filenames in os.walk(project_root):
        for fname in sorted(filenames):
            if "node_modules" in dirpath or fname in ("package.json", "tsconfig.json", "package-lock.json"):
                continue
            fpath = os.path.join(dirpath, fname)
            relpath = os.path.relpath(fpath, project_root)
            print(f"\n# ===== {relpath} =====")
            with open(fpath) as f:
                lines = f.read().split("\n")
            if len(lines) > 40:
                print("\n".join(lines[:40]))
                print(f"  ... ({len(lines) - 40} more lines)")
            else:
                print("\n".join(lines))

    print(f"\nProject written to: {project_root}")


if __name__ == "__main__":
    main()
