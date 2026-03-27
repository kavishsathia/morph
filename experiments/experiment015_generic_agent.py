"""
Generic Agent Experiment

Key change: ONE system prompt for all agents. The root is not special — it's the
same generic agent that receives a user message telling it to plan and delegate
rather than write code. The role comes from the input, not the system prompt.

This tests whether a single generic agent definition can handle both planning
(root) and implementation (children) based purely on the task it receives.

## Experiment Results (2026-03-27)

Model: claude-sonnet-4-6
Root task: Product dashboard (same as exp008-014).
7 agents, 20 API calls, 8K tokens + 61K cache reads.

### Timing Summary

    Total wall clock:     54s
    Total API calls:      20
    Total tokens:         8,013 (1.4K in, 6.6K out)
    Cache read tokens:    60,643
    Cache creation:       19,741

### Agent Timings

    architect          54.4s  (45s API, 9s waiting, 5 calls)
    sortcontrols       11.9s  (3 calls, 10K cache reads)
    productcard        10.6s  (2 calls, 6K cache reads)
    app-agent           9.6s  (2 calls, 6K cache reads)
    searchbar           9.5s  (3 calls, 10K cache reads)
    spinner             9.5s  (3 calls, 11K cache reads)
    hook-agent          7.4s  (2 calls, 6K cache reads)

    Parallelism speedup: 2.1x (113s serial -> 54s wall clock)

### Project Layout

    src/
      App.tsx                                   — root component with state
      types/index.ts                            — Product, SortKey
      utils/mockProducts.ts                     — 8 mock products
      hooks/useProducts.ts                      — filter + sort with useMemo
      components/
        SearchBar/SearchBar.tsx + index.ts       — controlled input
        SortControls/SortControls.tsx + index.ts — 3 sort buttons
        ProductCard/ProductCard.tsx + index.ts   — card with image, price, stars
        Spinner/Spinner.tsx + index.ts           — loading spinner

### Code Quality

- All imports are correct — children knew exact type names and file paths
  because they inherited the parent's context.
- Shared types (Product, SortKey) used consistently across all files.
- Hook imports both types AND mock data with correct relative paths.
- Barrel exports work correctly (export { default } from './X').
- No interface mismatches, no duplicate type definitions.

### Full Progression

    Exp010 (sequential):      356s  247K tokens
    Exp011 (pipelined):       361s  393K tokens
    Exp012 (self-routing):    188s  300K tokens
    Exp013 (light contracts): 130s  200K tokens
    Exp014 (forked agents):   109s   96K tokens + 97K cache
    Exp015 (generic agent):    54s    8K tokens + 61K cache

### Key Findings

- 54s and 8K tokens — 6.6x faster and 31x fewer tokens than exp010.
- One system prompt, one run_agent function for all agents. The root
  becomes an architect purely through its user message instruction.
- Architect root needed only 5 API calls (vs 12 in exp014, 27 in exp012).
  It wrote types + mock data, then forked 6 children in one batch.
- Children averaged 10s / 2-3 calls each, hitting cache hard.
- Prompt caching: 61K cache reads across 6 children. The shared parent
  conversation prefix is reused efficiently.
- Code quality is high — correct imports, shared types, barrel exports,
  no mismatches. Forking gives children full project context.
- The generic agent pattern proves that role specialization via input
  is as effective as role specialization via system prompt, and simpler.
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json
import os
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
# One system prompt for all agents
# ──────────────────────────────────────────────

AGENT_TOOLS = [
    {"name": "read_file", "description": "Read a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
    {"name": "append_to_file", "description": "Append to a file. Creates dirs if needed.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}},
    {"name": "replace_text", "description": "Replace text in a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["file_path", "old_text", "new_text"]}},
    {
        "name": "fork_and_assign",
        "description": (
            "Fork your conversation context to a child agent. The child inherits "
            "your full history and knows everything you know. Give it a file_path "
            "and a short task. Returns immediately — child runs in parallel."
        ),
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

Use .tsx for JSX, .ts for logic. Include imports. Call done() when finished.
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
# Generic agent — handles both planning and implementation
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

    # If forked, inherit parent context + new task. Otherwise start fresh.
    if parent_messages:
        messages = list(parent_messages) + [{"role": "user", "content": user_message}]
    else:
        messages = [{"role": "user", "content": user_message}]

    # At max depth, remove fork/wait tools
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

        # Fork children AFTER tool_results are appended (clean conversation state)
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

    # Collect orphans
    for tid, (future, info) in pending_futures.items():
        wait_start = time.monotonic()
        children.append(future.result())
        timing.wait_time += time.monotonic() - wait_start

    timing.end = time.monotonic()
    with _timings_lock:
        agent_timings.append(timing)

    safe_print(f"{indent}[depth={depth}] Agent done: {name} ({timing.total:.1f}s, cache_read={timing.cache_read_tokens:,})")
    return {"name": name, "children": children}


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

    # The root gets the SAME agent, just a different user message
    root_message = (
        f"{root_task}\n\n"
        "Take it easy on this one. Don't write component code yourself.\n"
        "Instead:\n"
        "1. Plan the project structure — decide what components, hooks, types, and utils you need.\n"
        "2. Write ONLY the shared types (src/types/index.ts) and mock data (src/utils/mockProducts.ts).\n"
        "3. Fork a child agent for EACH component and the hook. Give each a file_path and short task.\n"
        "4. Fork one child for App.tsx too — you're just the architect.\n"
        "5. Fork ALL children at once, then wait_all(), then done()."
    )

    project_root = tempfile.mkdtemp(prefix="morph_exp015_")
    total_start = time.monotonic()

    print("=" * 60)
    print("GENERIC AGENT EXPERIMENT")
    print("=" * 60)
    print(f"\nRoot task: {root_task}")
    print(f"Project root: {project_root}\n")

    tree = run_agent(
        name="architect",
        user_message=root_message,
        project_root=project_root,
        depth=0,
        max_depth=2,
    )

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

    # Timing
    print("\n" + "=" * 60)
    print("TIMING REPORT")
    print("=" * 60)

    total_api_calls = sum(len(t.api_calls) for t in agent_timings)
    total_api_time = sum(t.api_total for t in agent_timings)
    total_input = sum(t.input_tokens for t in agent_timings)
    total_output = sum(t.output_tokens for t in agent_timings)
    total_cache_read = sum(t.cache_read_tokens for t in agent_timings)
    total_cache_create = sum(t.cache_creation_tokens for t in agent_timings)

    print(f"\n  Total wall clock:        {total_time:.1f}s")
    print(f"  Total API calls:         {total_api_calls}")
    print(f"  Total API time:          {total_api_time:.1f}s")
    print(f"  Total input tokens:      {total_input:,}")
    print(f"  Total output tokens:     {total_output:,}")
    print(f"  Total tokens:            {total_input + total_output:,}")
    print(f"  Cache read tokens:       {total_cache_read:,}")
    print(f"  Cache creation tokens:   {total_cache_create:,}")

    print(f"\n  --- Agent Timings ({len(agent_timings)} agents) ---")
    print(f"  {'Name':<25} {'D':>1} {'Total':>7} {'API':>7} {'Wait':>7} {'#':>3} {'In':>8} {'Out':>7} {'CacheR':>8}")
    print(f"  {'-'*25} {'-'} {'-'*7} {'-'*7} {'-'*7} {'-'*3} {'-'*8} {'-'*7} {'-'*8}")
    for t in sorted(agent_timings, key=lambda x: x.start):
        print(f"  {t.name:<25} {t.depth} {t.total:>6.1f}s {t.api_total:>6.1f}s {t.wait_time:>6.1f}s {len(t.api_calls):>3} {t.input_tokens:>8,} {t.output_tokens:>7,} {t.cache_read_tokens:>8,}")

    serial_time = sum(t.total for t in agent_timings)
    print(f"\n  --- Parallelism ---")
    print(f"  Serial time:             {serial_time:.1f}s")
    print(f"  Wall clock:              {total_time:.1f}s")
    if total_time > 0:
        print(f"  Speedup:                 {serial_time / total_time:.1f}x")

    # Files on disk
    print(f"\n" + "=" * 60)
    print(f"FILES ON DISK ({project_root})")
    print("=" * 60)
    for dirpath, _, filenames in os.walk(project_root):
        for fname in sorted(filenames):
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
