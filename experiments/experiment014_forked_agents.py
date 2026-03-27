"""
Forked Agents React Experiment

Key change: instead of spawning fresh child agents with only a contract,
we fork the parent's conversation. Each child inherits the parent's full
message history (project context, sibling info, decisions made so far)
then gets a focused task appended.

This is like Unix fork() — the child starts with the parent's memory.
It knows about the project structure, other components, shared types,
and import paths because it saw the parent discuss them.

With prompt caching, the shared prefix (parent's conversation up to the
fork point) should be cached and reused across all children.

## Experiment Results (2026-03-27)

Model: claude-sonnet-4-6
Root task: Product dashboard (same as exp008-013).
6 agents, 36 API calls, 96K tokens + 97K cache reads.

### Timing Summary

    Total wall clock:     109s
    Total API calls:      36
    Total tokens:         96,361 (83K in, 13K out)
    Cache read tokens:    97,428
    Cache creation:       42,961

### Agent Timings

    root              108.8s  (70s API, 39s waiting, 12 calls)
    SortControls       40.3s  (8 calls, 43K cache reads)
    ProductCard        36.0s  (5 calls, 23K cache reads)
    SearchBar          23.4s  (5 calls, 17K cache reads)
    mockProducts       20.6s  (3 calls, 5K cache reads)
    useProducts         8.9s  (3 calls, 10K cache reads)

    Parallelism speedup: 2.2x (238s serial -> 109s wall clock)

### Full progression

    Exp010 (sequential):      356s  247K tokens
    Exp011 (pipelined):       361s  393K tokens
    Exp012 (self-routing):    188s  300K tokens
    Exp013 (light contracts): 130s  200K tokens
    Exp014 (forked agents):   109s   96K tokens + 97K cache

### Key Findings

- Prompt caching works: 97K cache read tokens across 5 children.
  SortControls alone got 43K cache reads from the shared parent prefix.
- Only 6 agents total — root wrote types itself before forking, so no
  separate types agent needed. Children are more autonomous.
- 96K total tokens — cheapest experiment yet (down from 300K in exp012).
- Children have fewer API calls (3-8) because they don't waste turns
  figuring out project structure — they inherited it.
- Root still dominates at 109s / 12 calls, but children run in parallel
  during its 39s wait time.
- The fork pattern solves "global context blindness" — children know
  about siblings, shared types, and the project layout.
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
# Tools & prompts
# ──────────────────────────────────────────────

FS_TOOLS = [
    {"name": "read_file", "description": "Read a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
    {"name": "append_to_file", "description": "Append to a file. Creates dirs if needed.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}},
    {"name": "replace_text", "description": "Replace text in a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["file_path", "old_text", "new_text"]}},
    {"name": "done", "description": "Signal you are finished.", "input_schema": {"type": "object", "properties": {}}},
]

PLAN_TOOLS = FS_TOOLS + [
    {
        "name": "fork_and_assign",
        "description": (
            "Fork your current conversation context to a child agent and assign "
            "it a specific task. The child inherits your full conversation history "
            "(it knows everything you know). Specify the file_path it should write "
            "to and a short task description. Returns immediately — child runs in parallel."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Child name (e.g. 'SearchBar')."},
                "kind": {"type": "string", "enum": ["component", "hook", "util", "type"]},
                "file_path": {"type": "string", "description": "Where the child writes its code."},
                "task": {"type": "string", "description": "Short task (2-3 sentences). The child already has your full context."},
            },
            "required": ["name", "kind", "file_path", "task"],
        },
    },
    {
        "name": "wait_all",
        "description": "Wait for ALL forked children to finish.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

ROOT_SYSTEM = """\
You are a senior React/TypeScript developer building a project on disk.

You have filesystem tools and fork_and_assign to delegate work.

WORKFLOW:
1. Plan the project structure. Discuss what components, hooks, types, and utils
   you need. Write shared types and any scaffolding first.
2. Write YOUR code (App.tsx) using append_to_file.
3. Fork children using fork_and_assign. Each child INHERITS YOUR FULL CONTEXT —
   it knows everything you've discussed and written so far. So keep the task
   short (2-3 sentences) — the child already has the context.
4. Fork ALL children at once (they run in parallel).
5. wait_all(), then done().

PROJECT STRUCTURE:
    src/
      App.tsx
      components/ComponentName/ComponentName.tsx + index.ts
      hooks/useHookName.ts
      utils/utilName.ts
      types/index.ts

IMPORTANT:
- Before forking children, write shared types (src/types/index.ts) so children
  can import them. The children will see that you wrote it.
- Keep fork tasks SHORT — the child has your full memory.
- Max 6 children. Fork them all at once.
- Always call done() when finished.
"""

CHILD_SYSTEM = """\
You are a React/TypeScript developer. You have been forked from a parent agent
and inherit its full conversation context. You know about the project structure,
shared types, sibling components, and everything discussed so far.

Your specific task will be given to you. Implement it.

Tools: read_file, append_to_file, replace_text, done.

WORKFLOW:
1. Read any files you need to check (types, existing code).
2. Write your code to your assigned file using append_to_file.
3. Create barrel export (index.ts) if you're a component.
4. done().

RULES:
- You already know the project context. Use correct imports based on what you know.
- Write DIRECTLY to your assigned file.
- Keep it focused — just implement your task.
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
# Forked child agent
# ──────────────────────────────────────────────

def run_forked_child(
    name: str,
    kind: str,
    file_path: str,
    task: str,
    parent_messages: list[dict],
    project_root: str,
    depth: int,
) -> dict:
    """Run a child agent that inherits the parent's conversation context."""
    timing = AgentTiming(name=name, kind=kind, depth=depth, start=time.monotonic())
    indent = "  " * depth
    safe_print(f"{indent}[depth={depth}] Forked child started: {name} ({kind}) -> {file_path}")

    # Fork: copy parent messages + append the child's specific task
    messages = list(parent_messages) + [
        {"role": "user", "content": (
            f"You have been forked to implement: {name} ({kind})\n"
            f"Write to: {file_path}\n"
            f"Task: {task}\n\n"
            f"You have my full context. Implement this now."
        )}
    ]

    is_done = False
    while not is_done:
        response = timed_api_call(
            timing, model="claude-sonnet-4-6", max_tokens=4096,
            system=CHILD_SYSTEM, tools=FS_TOOLS, messages=messages,
            cache_control={"type": "ephemeral"},
        )
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" and not tool_use_blocks:
            break
        if not tool_use_blocks:
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

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
            elif block.name == "done":
                is_done = True
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Done."})

        messages.append({"role": "user", "content": tool_results})

    timing.end = time.monotonic()
    with _timings_lock:
        agent_timings.append(timing)

    safe_print(f"{indent}[depth={depth}] Forked child done: {name} ({timing.total:.1f}s, cache_read={timing.cache_read_tokens:,})")
    return {"name": name, "kind": kind, "file_path": file_path}


# ──────────────────────────────────────────────
# Root agent
# ──────────────────────────────────────────────

def run_root(task: str, project_root: str) -> dict:
    timing = AgentTiming(name="root", kind="component", depth=0, start=time.monotonic())
    safe_print("[depth=0] Root agent started")

    messages = [{"role": "user", "content": f"Build this React application:\n\n{task}"}]
    children = []
    pending_futures: dict[str, tuple[Future, dict]] = {}
    pending_forks: list[tuple[str, dict]] = []  # (task_id, input) — fork after tool_results
    is_done = False

    while not is_done:
        response = timed_api_call(
            timing, model="claude-sonnet-4-6", max_tokens=4096,
            system=ROOT_SYSTEM, tools=PLAN_TOOLS, messages=messages,
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
                            if "root" not in file_index[fp]:
                                file_index[fp].append("root")
                safe_print(f"  [{block.name}] {block.input.get('file_path', '?')[:50]} -> {result[:40]}")
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})

            elif block.name == "fork_and_assign":
                task_id = str(uuid4())[:8]
                safe_print(f"  -> Will fork: {block.input['name']} [{task_id}]")
                pending_forks.append((task_id, block.input))
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"task_id": task_id, "status": "forked"})})

            elif block.name == "wait_all":
                if pending_futures:
                    safe_print(f"  <- Waiting for {len(pending_futures)} forked children...")
                    wait_start = time.monotonic()
                    results_list = []
                    for tid, (future, info) in list(pending_futures.items()):
                        child_result = future.result()
                        children.append(child_result)
                        safe_print(f"  <- Done: {info['name']}")
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

        # Now fork children — messages is clean (tool_results appended)
        for task_id, fork_input in pending_forks:
            child_name = fork_input["name"]
            child_kind = fork_input.get("kind", "component")
            child_path = fork_input["file_path"]
            child_task = fork_input["task"]

            safe_print(f"  -> Forking now: {child_name} ({child_kind}) -> {child_path} [{task_id}]")

            future = executor.submit(
                run_forked_child,
                name=child_name, kind=child_kind, file_path=child_path,
                task=child_task, parent_messages=list(messages),
                project_root=project_root, depth=1,
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

    safe_print(f"[depth=0] Root done ({timing.total:.1f}s)")
    return {"name": "root", "kind": "component", "file_path": "src/App.tsx", "children": children}


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def print_tree(node, indent=0):
    prefix = "  " * indent
    print(f"{prefix}{node['name']} ({node.get('kind', '?')})  [{node.get('file_path', '?')}]")
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

    project_root = tempfile.mkdtemp(prefix="morph_exp014_")
    total_start = time.monotonic()

    print("=" * 60)
    print("FORKED AGENTS REACT EXPERIMENT")
    print("=" * 60)
    print(f"\nRoot task: {root_task}")
    print(f"Project root: {project_root}\n")

    tree = run_root(root_task, project_root)

    total_time = time.monotonic() - total_start

    # Results
    print("\n" + "=" * 60)
    print("COMPONENT TREE")
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
    print(f"  {'Name':<25} {'Kind':<12} {'D':>1} {'Total':>7} {'API':>7} {'Wait':>7} {'#':>3} {'In':>8} {'Out':>7} {'CacheR':>8}")
    print(f"  {'-'*25} {'-'*12} {'-'} {'-'*7} {'-'*7} {'-'*7} {'-'*3} {'-'*8} {'-'*7} {'-'*8}")
    for t in sorted(agent_timings, key=lambda x: x.start):
        print(f"  {t.name:<25} {t.kind:<12} {t.depth} {t.total:>6.1f}s {t.api_total:>6.1f}s {t.wait_time:>6.1f}s {len(t.api_calls):>3} {t.input_tokens:>8,} {t.output_tokens:>7,} {t.cache_read_tokens:>8,}")

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
