"""
Pipelined React Agent Tree Experiment

Key change: agents submit their own code BEFORE spawning children. A persistent
router agent runs concurrently, processing submissions as they arrive via a
thread-safe queue. If the router is busy, submissions queue up and are processed
in order.

This pipelines generation and routing — by the time the last agent finishes,
most routing is already done. No more sequential Phase 1 -> Phase 2.

Flow:
1. Agent receives task/contract
2. Agent submits its OWN code first (goes into router queue)
3. Agent spawns children (which do the same thing recursively)
4. Agent waits for children
5. Meanwhile, the router is continuously dequeuing and writing files
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json
import os
import queue
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

    @property
    def total(self) -> float:
        return self.end - self.start

    @property
    def api_total(self) -> float:
        return sum(self.api_calls)

    @property
    def own_work(self) -> float:
        return self.total - self.wait_time


@dataclass
class RouteTiming:
    name: str
    duration: float = 0.0
    api_calls: list[float] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    queue_wait: float = 0.0  # time item sat in queue before processing


_timings_lock = threading.Lock()
agent_timings: list[AgentTiming] = []
route_timings: list[RouteTiming] = []

_print_lock = threading.Lock()


def safe_print(msg: str):
    with _print_lock:
        print(msg)


# ──────────────────────────────────────────────
# Router queue + persistent router agent
# ──────────────────────────────────────────────

@dataclass
class RouteItem:
    name: str
    kind: str
    code: str
    contract: dict | None
    enqueued_at: float


route_queue: queue.Queue[RouteItem | None] = queue.Queue()  # None = poison pill

# Shared mutable state for the router
file_index: dict[str, list[str]] = {}
assignments: dict[str, str] = {}
_index_lock = threading.Lock()

ROUTER_TOOLS = [
    {"name": "read_file", "description": "Read a file's contents.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
    {"name": "append_to_file", "description": "Append content to a file. Creates file/dirs if needed.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}},
    {"name": "replace_text", "description": "Replace text in a file.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["file_path", "old_text", "new_text"]}},
    {"name": "assign_file", "description": "Register this module in the index.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "file_path": {"type": "string"}}, "required": ["name", "file_path"]}},
    {"name": "done", "description": "Signal you are done placing this module.", "input_schema": {"type": "object", "properties": {}}},
]

ROUTER_SYSTEM = """\
You are a React project architect routing TypeScript modules into a well-structured project.

For each module: assign_file -> write to disk -> done.

Layout: src/components/Name/Name.tsx + index.ts, src/hooks/useX.ts, src/types/index.ts, src/utils/x.ts, src/App.tsx.
Rules: one component per file, barrel exports, .tsx for JSX, .ts for logic, relative imports, read before write.
"""


def execute_router_tool(tool_name, tool_input, project_root):
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
    elif tool_name == "assign_file":
        with _index_lock:
            assignments[tool_input["name"]] = tool_input["file_path"]
            file_index.setdefault(tool_input["file_path"], []).append(tool_input["name"])
        return f"Indexed: {tool_input['name']} -> {tool_input['file_path']}"
    elif tool_name == "done":
        return "Done."
    return "Unknown tool."


def timed_api_call(timing, **kwargs):
    t0 = time.monotonic()
    response = client.messages.create(**kwargs)
    dt = time.monotonic() - t0
    timing.api_calls.append(dt)
    timing.input_tokens += response.usage.input_tokens
    timing.output_tokens += response.usage.output_tokens
    return response


def route_one_item(item: RouteItem, project_root: str) -> RouteTiming:
    """Route a single item using the LLM router."""
    rt = RouteTiming(name=item.name, queue_wait=time.monotonic() - item.enqueued_at)
    rt_start = time.monotonic()

    with _index_lock:
        index_str = json.dumps(file_index, indent=2) if file_index else "(empty)"

    contract = item.contract
    contract_str = ""
    if contract:
        lines = [f"  Name: {contract['name']}", f"  Kind: {contract.get('kind', 'component')}"]
        if contract.get("props_interface"):
            lines.append(f"  Props: {contract['props_interface']}")
        if contract.get("behavior"):
            lines.append(f"  Behavior: {contract['behavior']}")
        if contract.get("module_hint"):
            lines.append(f"  Module hint: {contract['module_hint']}")
        contract_str = f"\n\nContract:\n" + "\n".join(lines)

    module_hint = contract.get("module_hint", "") if contract else ""
    hint_str = f"\nModule hint: {module_hint}" if module_hint else ""

    prompt = (
        f"Place this {item.kind} in the project:\n\n"
        f"Name: {item.name}\nKind: {item.kind}{hint_str}\n"
        f"```tsx\n{item.code}\n```{contract_str}\n\n"
        f"Current index:\n{index_str}"
    )

    messages = [{"role": "user", "content": prompt}]
    done = False

    while not done:
        response = timed_api_call(
            rt, model="claude-sonnet-4-6", max_tokens=2048,
            system=ROUTER_SYSTEM, tools=ROUTER_TOOLS, messages=messages,
        )
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": "Please use the tools."})
            continue

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in tool_use_blocks:
            result = execute_router_tool(block.name, block.input, project_root)
            safe_print(f"  [Router] {block.name}({json.dumps(block.input)[:60]}) -> {result[:50]}")
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            if block.name == "done":
                done = True
        messages.append({"role": "user", "content": tool_results})

    rt.duration = time.monotonic() - rt_start
    return rt


def router_worker(project_root: str):
    """Persistent router thread — dequeues items and routes them."""
    safe_print("[Router] Worker started, waiting for items...")

    while True:
        item = route_queue.get()
        if item is None:  # poison pill
            safe_print("[Router] Worker received shutdown signal.")
            break

        safe_print(f"  [Router] Processing: {item.name} (waited {time.monotonic() - item.enqueued_at:.1f}s in queue)")
        rt = route_one_item(item, project_root)
        route_timings.append(rt)
        safe_print(f"  [Router] {item.name} routed in {rt.duration:.1f}s (queued {rt.queue_wait:.1f}s)")
        route_queue.task_done()


# ──────────────────────────────────────────────
# Generation (submit-first)
# ──────────────────────────────────────────────

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Component or hook name."},
        "kind": {"type": "string", "enum": ["component", "hook", "util", "type"]},
        "props_interface": {"type": "string", "description": "TypeScript interface for props/arguments."},
        "behavior": {"type": "string", "description": "Behavioral spec: state, effects, events, rendering."},
        "module_hint": {"type": "string", "description": "Where this belongs: components, hooks, utils, types, context, services."},
    },
    "required": ["name", "kind", "props_interface", "behavior"],
}

GEN_TOOLS = [
    {
        "name": "submit_code",
        "description": (
            "Submit YOUR implementation first, before spawning children. "
            "Import children by name — they will be implemented by child agents."
        ),
        "input_schema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
    },
    {
        "name": "spawn_child",
        "description": "Spawn a child agent AFTER submitting your code. Returns immediately with task_id.",
        "input_schema": {"type": "object", "properties": {"contract": CONTRACT_SCHEMA}, "required": ["contract"]},
    },
    {
        "name": "wait_for_child",
        "description": "Wait for a previously spawned child to finish.",
        "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
    },
    {
        "name": "wait_all",
        "description": "Wait for ALL pending children at once.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

GEN_SYSTEM = """\
You are a senior React/TypeScript developer.

Tools: submit_code(code), spawn_child(contract), wait_for_child(task_id), wait_all().

IMPORTANT WORKFLOW — follow this order:
1. FIRST: submit_code with YOUR implementation. Import child components/hooks by
   name even though they don't exist yet — child agents will create them.
2. THEN: spawn_child for each child you need (they run in parallel).
3. FINALLY: wait_all() to ensure children finish.

This order matters because your code gets routed to a file immediately upon
submission, allowing the file router to work while children are being generated.

When defining contracts for children, include BOTH:
1. props_interface — the full TypeScript interface
2. behavior — detailed behavioral spec

React principles:
- Composition over inheritance.
- Lift state up only when needed.
- Extract custom hooks for reusable stateful logic.
- Components should be presentational where possible.
- Use TypeScript strictly — no `any`.

Rules:
- Max 4 children per agent.
- Submit YOUR code first, then spawn children.
- If a task is simple, just submit directly without spawning.
"""


def format_contract(contract: dict) -> str:
    lines = [f"  Name: {contract['name']}", f"  Kind: {contract.get('kind', 'component')}"]
    if contract.get("props_interface"):
        lines.append(f"  Props interface:\n    {contract['props_interface']}")
    if contract.get("behavior"):
        lines.append(f"  Behavior:\n    {contract['behavior']}")
    if contract.get("module_hint"):
        lines.append(f"  Module hint: {contract['module_hint']}")
    return "\n".join(lines)


def run_agent(task: str, contract: dict | None = None, depth: int = 0, max_depth: int = 2) -> dict:
    indent = "  " * depth
    if contract:
        name = contract["name"]
        kind = contract.get("kind", "component")
    else:
        name = "root"
        kind = "component"

    timing = AgentTiming(name=name, kind=kind, depth=depth, start=time.monotonic())
    safe_print(f"{indent}[depth={depth}] Agent started: {name} ({kind})")

    if contract:
        user_prompt = f"Implement this {kind} according to the contract:\n\n{format_contract(contract)}"
    else:
        user_prompt = f"Build this React application: {task}"

    tools = GEN_TOOLS if depth < max_depth else [GEN_TOOLS[0]]  # submit_code only at max depth
    if depth >= max_depth:
        user_prompt += "\n\nMax depth. Just implement and submit directly."

    messages = [{"role": "user", "content": user_prompt}]
    children = []
    pending_futures: dict[str, tuple[Future, dict]] = {}
    my_code = None

    while True:
        response = timed_api_call(
            timing, model="claude-sonnet-4-6", max_tokens=4096,
            system=GEN_SYSTEM, tools=tools, messages=messages,
        )
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" and not tool_use_blocks:
            if my_code is None:
                text = next((b.text for b in response.content if b.type == "text"), "")
                my_code = text
            break
        if not tool_use_blocks:
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for block in tool_use_blocks:
            if block.name == "submit_code":
                my_code = block.input.get("code", block.input.get("function_code", "// empty"))
                # Immediately enqueue for routing
                route_queue.put(RouteItem(
                    name=name, kind=kind, code=my_code,
                    contract=contract, enqueued_at=time.monotonic(),
                ))
                safe_print(f"{indent}  >> Submitted code -> router queue")
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Submitted and queued for routing."})

            elif block.name == "spawn_child":
                child_contract = block.input["contract"]
                if isinstance(child_contract, str):
                    try:
                        child_contract = json.loads(child_contract)
                    except json.JSONDecodeError:
                        child_contract = {"name": child_contract, "kind": "component", "props_interface": "", "behavior": child_contract}
                child_name = child_contract["name"]
                child_kind = child_contract.get("kind", "component")
                module_hint = child_contract.get("module_hint", "")
                task_id = str(uuid4())[:8]
                hint_str = f" -> {module_hint}" if module_hint else ""
                safe_print(f"{indent}  -> Spawning: {child_name} ({child_kind}{hint_str}) [{task_id}]")
                future = executor.submit(run_agent, child_name, child_contract, depth + 1, max_depth)
                pending_futures[task_id] = (future, child_contract)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"task_id": task_id})})

            elif block.name == "wait_for_child":
                task_id = block.input["task_id"]
                if task_id not in pending_futures:
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"success": False}), "is_error": True})
                else:
                    future, cc = pending_futures.pop(task_id)
                    safe_print(f"{indent}  <- Waiting: {cc['name']}")
                    wait_start = time.monotonic()
                    child_node = future.result()
                    timing.wait_time += time.monotonic() - wait_start
                    children.append(child_node)
                    safe_print(f"{indent}  <- Done: {cc['name']}")
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"success": True})})

            elif block.name == "wait_all":
                safe_print(f"{indent}  <- Waiting for all {len(pending_futures)} children...")
                wait_start = time.monotonic()
                results_list = []
                for tid, (future, cc) in list(pending_futures.items()):
                    child_node = future.result()
                    children.append(child_node)
                    safe_print(f"{indent}  <- Done: {cc['name']}")
                    results_list.append({"name": cc["name"], "success": True})
                timing.wait_time += time.monotonic() - wait_start
                pending_futures.clear()
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"results": results_list})})

        messages.append({"role": "user", "content": tool_results})
        if my_code is not None and not pending_futures and response.stop_reason != "tool_use":
            break

    # Collect any orphan children
    for tid, (future, cc) in pending_futures.items():
        wait_start = time.monotonic()
        children.append(future.result())
        timing.wait_time += time.monotonic() - wait_start

    if my_code is None:
        my_code = "// empty"
        route_queue.put(RouteItem(name=name, kind=kind, code=my_code, contract=contract, enqueued_at=time.monotonic()))

    timing.end = time.monotonic()
    with _timings_lock:
        agent_timings.append(timing)

    safe_print(f"{indent}[depth={depth}] Agent done: {name} ({timing.total:.1f}s)")
    return {"name": name, "kind": kind, "code": my_code, "contract": contract, "children": children}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def print_tree(node, indent=0):
    prefix = "  " * indent
    name = node["name"]
    kind = node.get("kind", "component")
    with _index_lock:
        path = assignments.get(name, "?")
    print(f"{prefix}{name} ({kind})  [{path}]")
    for child in node["children"]:
        print_tree(child, indent + 1)


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
        "- The product data can be hardcoded as mock data in a utils file"
    )

    project_root = tempfile.mkdtemp(prefix="morph_exp011_")
    total_start = time.monotonic()

    print("=" * 60)
    print("PIPELINED REACT AGENT TREE EXPERIMENT")
    print("=" * 60)
    print(f"\nRoot task: {root_task}")
    print(f"Project root: {project_root}\n")

    # Start the router worker thread
    router_thread = threading.Thread(target=router_worker, args=(project_root,), daemon=True)
    router_thread.start()

    # Generate (submissions stream into router as they happen)
    print("--- Generation + Routing (pipelined) ---\n")
    gen_start = time.monotonic()
    tree = run_agent(root_task, depth=0, max_depth=2)
    gen_time = time.monotonic() - gen_start

    # Signal router to finish and wait
    safe_print("\n[Main] Generation done. Waiting for router to drain queue...")
    drain_start = time.monotonic()
    route_queue.join()  # wait for all queued items to be processed
    route_queue.put(None)  # poison pill
    router_thread.join()
    drain_time = time.monotonic() - drain_start

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
            print(f"  {path}: {', '.join(names)}")

    # Timing report
    print("\n" + "=" * 60)
    print("TIMING REPORT")
    print("=" * 60)

    print(f"\n  Total wall clock:        {total_time:.1f}s")
    print(f"  Generation time:         {gen_time:.1f}s")
    print(f"  Post-gen drain time:     {drain_time:.1f}s  (router finishing remaining items)")
    print(f"  Pipeline overlap:        {gen_time - drain_time:.1f}s  (routing done during generation)")

    total_api_calls = sum(len(t.api_calls) for t in agent_timings) + sum(len(t.api_calls) for t in route_timings)
    total_api_time = sum(t.api_total for t in agent_timings) + sum(sum(t.api_calls) for t in route_timings)
    total_input = sum(t.input_tokens for t in agent_timings) + sum(t.input_tokens for t in route_timings)
    total_output = sum(t.output_tokens for t in agent_timings) + sum(t.output_tokens for t in route_timings)

    print(f"\n  Total API calls:         {total_api_calls}")
    print(f"  Total API time:          {total_api_time:.1f}s")
    print(f"  Total input tokens:      {total_input:,}")
    print(f"  Total output tokens:     {total_output:,}")
    print(f"  Total tokens:            {total_input + total_output:,}")

    # Per-agent breakdown
    print(f"\n  --- Agent Timings ({len(agent_timings)} agents) ---")
    print(f"  {'Name':<25} {'Kind':<12} {'D':>1} {'Total':>7} {'API':>7} {'Wait':>7} {'Own':>7} {'#':>3} {'In':>8} {'Out':>7}")
    print(f"  {'-'*25} {'-'*12} {'-'} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*3} {'-'*8} {'-'*7}")
    for t in sorted(agent_timings, key=lambda x: x.start):
        print(f"  {t.name:<25} {t.kind:<12} {t.depth} {t.total:>6.1f}s {t.api_total:>6.1f}s {t.wait_time:>6.1f}s {t.own_work:>6.1f}s {len(t.api_calls):>3} {t.input_tokens:>8,} {t.output_tokens:>7,}")

    # Per-route breakdown
    print(f"\n  --- Route Timings ({len(route_timings)} modules) ---")
    print(f"  {'Name':<25} {'Total':>7} {'QueueW':>7} {'API':>7} {'#':>3} {'In':>8} {'Out':>7}")
    print(f"  {'-'*25} {'-'*7} {'-'*7} {'-'*7} {'-'*3} {'-'*8} {'-'*7}")
    for rt in route_timings:
        api_t = sum(rt.api_calls)
        print(f"  {rt.name:<25} {rt.duration:>6.1f}s {rt.queue_wait:>6.1f}s {api_t:>6.1f}s {len(rt.api_calls):>3} {rt.input_tokens:>8,} {rt.output_tokens:>7,}")

    # Parallelism
    print(f"\n  --- Parallelism ---")
    serial_agent = sum(t.total for t in agent_timings)
    serial_route = sum(rt.duration for rt in route_timings)
    print(f"  Serial agent time:       {serial_agent:.1f}s")
    print(f"  Serial route time:       {serial_route:.1f}s")
    print(f"  Serial total:            {serial_agent + serial_route:.1f}s")
    print(f"  Actual wall clock:       {total_time:.1f}s")
    if total_time > 0:
        print(f"  Overall speedup:         {(serial_agent + serial_route) / total_time:.1f}x")

    # Show files on disk
    print(f"\n" + "=" * 60)
    print(f"FILES ON DISK ({project_root})")
    print("=" * 60)
    for dirpath, _, filenames in os.walk(project_root):
        for fname in sorted(filenames):
            fpath = os.path.join(dirpath, fname)
            relpath = os.path.relpath(fpath, project_root)
            print(f"\n# ===== {relpath} =====")
            with open(fpath) as f:
                content = f.read()
            # Truncate long files for readability
            lines = content.split("\n")
            if len(lines) > 40:
                print("\n".join(lines[:40]))
                print(f"  ... ({len(lines) - 40} more lines)")
            else:
                print(content)

    print(f"\nProject written to: {project_root}")
    executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
