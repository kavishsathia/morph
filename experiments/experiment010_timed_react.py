"""
Timed React Agent Tree Experiment

Same as experiment009 (React + Sonnet) but with comprehensive timing:
- Total wall clock time
- Phase 1 (generation) vs Phase 2 (routing) time
- Per-agent execution time
- Per-API-call latency
- Time spent waiting for children vs doing own work
- Routing time per module

## Experiment Results (2026-03-27)

Model: claude-sonnet-4-6
Root task: Product dashboard (same as exp008/009).
9 agents, 9 routed modules, 71 total API calls, 247K tokens.

### Timing Summary

    Total wall clock:     356s (~6 min)
    Phase 1 (generate):   125s (35%)
    Phase 2 (route):      232s (65%)

    Total API calls:      71
    Total tokens:         247,014 (218K in, 29K out)

### Agent Timings (Phase 1)

    root                    124.7s  (82s API, 43s waiting for children)
    useProductDashboard      44.8s  (33s API, 12s waiting)
    ProductCard              34.0s  (27s API, 7s waiting)
    mockProducts (d1)        18.1s
    ProductTypes (d1)        13.8s
    mockProducts (d2)        14.1s
    StarRating                8.3s
    ProductTypes (d2)         6.3s
    ProductTypes (d2)         5.5s

    Parallelism speedup:     2.2x (270s serial -> 125s wall clock)

### Route Timings (Phase 2 — sequential)

    root                     71.5s  (6 API calls — scaffolded entire project)
    ProductCard              37.7s  (10 API calls — most complex routing)
    mockProducts             32.5s
    useProductDashboard      20.1s
    mockProducts             19.9s
    ProductTypes             16.7s
    ProductTypes             12.8s
    StarRating               11.1s
    ProductTypes              9.6s

### Key Findings

- Routing is the bottleneck at 65% of total time, running fully sequentially.
  Each module takes 10-40s to route. Parallelizing routing would cut total
  time significantly.
- API latency dominates — almost zero time on local work.
- Root agent spent 43s (34%) just waiting for children to finish.
- The root router call (71s) is the single most expensive operation —
  it tries to scaffold the whole project structure in one go.
- Parallelism gave 2.2x speedup in generation. Could be higher with more
  independent subtrees (this tree was only 2 levels deep).
- 247K tokens for a ~10 file React project. At Sonnet pricing ($3/$15 per M),
  that's roughly $0.65 input + $0.43 output = ~$1.08 total.
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json
import os
import tempfile
import threading
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from uuid import uuid4

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = anthropic.Anthropic()
executor = ThreadPoolExecutor(max_workers=8)

# ──────────────────────────────────────────────
# Timing infrastructure
# ──────────────────────────────────────────────

@dataclass
class AgentTiming:
    name: str
    kind: str
    depth: int
    start: float = 0.0
    end: float = 0.0
    api_calls: list[float] = field(default_factory=list)  # duration of each API call
    wait_time: float = 0.0  # time spent waiting for children
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


_timings_lock = threading.Lock()
agent_timings: list[AgentTiming] = []
route_timings: list[RouteTiming] = []

# ──────────────────────────────────────────────
# Phase 1: React generation (with timing)
# ──────────────────────────────────────────────

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Component or hook name."},
        "kind": {"type": "string", "enum": ["component", "hook", "util", "type"]},
        "props_interface": {"type": "string", "description": "TypeScript interface for props/arguments."},
        "behavior": {"type": "string", "description": "Behavioral spec: state, effects, events, rendering, data transforms."},
        "module_hint": {"type": "string", "description": "Where this belongs: components, hooks, utils, types, context, services."},
    },
    "required": ["name", "kind", "props_interface", "behavior"],
}

GEN_TOOLS = [
    {
        "name": "spawn_child",
        "description": "Spawn a child agent. Returns immediately with task_id.",
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
    {
        "name": "submit_code",
        "description": "Submit your implementation. Only YOUR code — import children by name.",
        "input_schema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
    },
]

GEN_SYSTEM = """\
You are a senior React/TypeScript developer. You implement components, hooks,
utilities, and types according to contracts.

Tools: spawn_child(contract), wait_for_child(task_id), wait_all(), submit_code(code).
Workflow: decompose into children -> spawn them -> wait -> submit your code.

When defining contracts for children, include BOTH:
1. props_interface — the full TypeScript interface
2. behavior — detailed behavioral spec: state, effects, events, rendering, data transforms.

React principles:
- Composition over inheritance. Break UI into focused, reusable components.
- Lift state up only when needed.
- Extract custom hooks for reusable stateful logic.
- Components should be presentational where possible; push logic into hooks.
- Use TypeScript strictly — no `any`.
- Keep components under ~80 lines.

Rules:
- Max 4 children per agent.
- Don't re-implement children — import them by name.
- If a task is simple, just submit directly.
"""

_print_lock = threading.Lock()


def safe_print(msg: str):
    with _print_lock:
        print(msg)


def format_contract(contract: dict) -> str:
    lines = [f"  Name: {contract['name']}", f"  Kind: {contract.get('kind', 'component')}"]
    if contract.get("props_interface"):
        lines.append(f"  Props interface:\n    {contract['props_interface']}")
    if contract.get("behavior"):
        lines.append(f"  Behavior:\n    {contract['behavior']}")
    if contract.get("module_hint"):
        lines.append(f"  Module hint: {contract['module_hint']}")
    return "\n".join(lines)


def timed_api_call(timing: AgentTiming | RouteTiming, **kwargs):
    """Make an API call and record its duration and token usage."""
    t0 = time.monotonic()
    response = client.messages.create(**kwargs)
    dt = time.monotonic() - t0
    timing.api_calls.append(dt)
    timing.input_tokens += response.usage.input_tokens
    timing.output_tokens += response.usage.output_tokens
    return response


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

    tools = GEN_TOOLS if depth < max_depth else [GEN_TOOLS[3]]
    if depth >= max_depth:
        user_prompt += "\n\nMax depth. Implement and submit directly."

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
            if block.name == "spawn_child":
                child_contract = block.input["contract"]
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

            elif block.name == "submit_code":
                my_code = block.input.get("code", block.input.get("function_code", "// empty"))
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Submitted."})

        messages.append({"role": "user", "content": tool_results})
        if my_code is not None and response.stop_reason != "tool_use":
            break
        if my_code is not None:
            timed_api_call(timing, model="claude-sonnet-4-6", max_tokens=1024, system=GEN_SYSTEM, tools=tools, messages=messages)
            break

    for tid, (future, cc) in pending_futures.items():
        wait_start = time.monotonic()
        children.append(future.result())
        timing.wait_time += time.monotonic() - wait_start

    if my_code is None:
        my_code = "// empty"

    timing.end = time.monotonic()
    with _timings_lock:
        agent_timings.append(timing)

    safe_print(f"{indent}[depth={depth}] Agent done: {name} ({timing.total:.1f}s, {len(timing.api_calls)} API calls)")
    return {
        "name": name,
        "kind": contract.get("kind", "component") if contract else "component",
        "code": my_code,
        "contract": contract,
        "children": children,
    }


# ──────────────────────────────────────────────
# Phase 2: Routing (with timing)
# ──────────────────────────────────────────────

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


def execute_router_tool(tool_name, tool_input, project_root, file_index, assignments):
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
        assignments[tool_input["name"]] = tool_input["file_path"]
        file_index.setdefault(tool_input["file_path"], []).append(tool_input["name"])
        return f"Indexed: {tool_input['name']} -> {tool_input['file_path']}"
    elif tool_name == "done":
        return "Done."
    return "Unknown tool."


def route_all_modules(queue: deque[dict], project_root: str) -> dict[str, str]:
    file_index: dict[str, list[str]] = {}
    assignments: dict[str, str] = {}

    print(f"\n[Router] Writing to: {project_root}")

    while queue:
        mod = queue.popleft()
        name = mod["name"]
        kind = mod.get("kind", "component")
        code = mod["code"]
        contract = mod.get("contract")

        rt = RouteTiming(name=name)
        rt_start = time.monotonic()

        index_str = json.dumps(file_index, indent=2) if file_index else "(empty)"
        contract_str = f"\n\nContract:\n{format_contract(contract)}" if contract else ""
        module_hint = contract.get("module_hint", "") if contract else ""
        hint_str = f"\nModule hint: {module_hint}" if module_hint else ""

        prompt = (
            f"Place this {kind} in the project:\n\n"
            f"Name: {name}\nKind: {kind}{hint_str}\n"
            f"```tsx\n{code}\n```{contract_str}\n\n"
            f"Current index:\n{index_str}\nRemaining: {len(queue)}"
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
                result = execute_router_tool(block.name, block.input, project_root, file_index, assignments)
                print(f"  [Router] {block.name}({json.dumps(block.input)[:60]}) -> {result[:50]}")
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
                if block.name == "done":
                    done = True
            messages.append({"role": "user", "content": tool_results})

        rt.duration = time.monotonic() - rt_start
        route_timings.append(rt)
        print(f"  [Router] {name} routed in {rt.duration:.1f}s ({len(rt.api_calls)} API calls)")

    return assignments


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def pre_order_collect(node):
    result = [{"name": node["name"], "kind": node.get("kind", "component"), "code": node["code"], "contract": node.get("contract")}]
    for child in node["children"]:
        result.extend(pre_order_collect(child))
    return result


def print_tree(node, assignments, indent=0):
    prefix = "  " * indent
    name = node["name"]
    kind = node.get("kind", "component")
    path = assignments.get(name, "?")
    print(f"{prefix}{name} ({kind})  [{path}]")
    for child in node["children"]:
        print_tree(child, assignments, indent + 1)


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

    project_root = tempfile.mkdtemp(prefix="morph_exp010_")
    total_start = time.monotonic()

    print("=" * 60)
    print("TIMED REACT AGENT TREE EXPERIMENT")
    print("=" * 60)
    print(f"\nRoot task: {root_task}")
    print(f"Project root: {project_root}\n")

    # Phase 1
    print("--- Phase 1: Generate ---\n")
    phase1_start = time.monotonic()
    tree = run_agent(root_task, depth=0, max_depth=2)
    phase1_time = time.monotonic() - phase1_start

    # Phase 2
    print("\n--- Phase 2: Route + Write ---")
    phase2_start = time.monotonic()
    pre_order = pre_order_collect(tree)
    queue = deque(pre_order)
    print(f"\nQueue ({len(queue)} modules): {[m['name'] for m in queue]}")
    assignments = route_all_modules(queue, project_root)
    phase2_time = time.monotonic() - phase2_start

    total_time = time.monotonic() - total_start

    # Results
    print("\n" + "=" * 60)
    print("COMPONENT TREE")
    print("=" * 60)
    print_tree(tree, assignments)

    print("\n" + "=" * 60)
    print("FILE INDEX")
    print("=" * 60)
    index: dict[str, list[str]] = {}
    for name, path in assignments.items():
        index.setdefault(path, []).append(name)
    for path, names in sorted(index.items()):
        print(f"  {path}: {', '.join(names)}")

    # Timing report
    print("\n" + "=" * 60)
    print("TIMING REPORT")
    print("=" * 60)

    print(f"\n  Total wall clock:     {total_time:.1f}s")
    print(f"  Phase 1 (generate):   {phase1_time:.1f}s")
    print(f"  Phase 2 (route):      {phase2_time:.1f}s")

    total_api_calls = sum(len(t.api_calls) for t in agent_timings) + sum(len(t.api_calls) for t in route_timings)
    total_api_time = sum(t.api_total for t in agent_timings) + sum(sum(t.api_calls) for t in route_timings)
    total_input = sum(t.input_tokens for t in agent_timings) + sum(t.input_tokens for t in route_timings)
    total_output = sum(t.output_tokens for t in agent_timings) + sum(t.output_tokens for t in route_timings)

    print(f"\n  Total API calls:      {total_api_calls}")
    print(f"  Total API time:       {total_api_time:.1f}s")
    print(f"  Total input tokens:   {total_input:,}")
    print(f"  Total output tokens:  {total_output:,}")
    print(f"  Total tokens:         {total_input + total_output:,}")

    # Per-agent breakdown
    print(f"\n  --- Agent Timings ({len(agent_timings)} agents) ---")
    print(f"  {'Name':<25} {'Kind':<12} {'Depth'} {'Total':>7} {'API':>7} {'Wait':>7} {'Own':>7} {'Calls':>5} {'In Tok':>8} {'Out Tok':>8}")
    print(f"  {'-'*25} {'-'*12} {'-'*5} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*5} {'-'*8} {'-'*8}")
    for t in sorted(agent_timings, key=lambda x: x.start):
        print(f"  {t.name:<25} {t.kind:<12} {t.depth:>5} {t.total:>6.1f}s {t.api_total:>6.1f}s {t.wait_time:>6.1f}s {t.own_work:>6.1f}s {len(t.api_calls):>5} {t.input_tokens:>8,} {t.output_tokens:>8,}")

    # Per-route breakdown
    print(f"\n  --- Route Timings ({len(route_timings)} modules) ---")
    print(f"  {'Name':<25} {'Total':>7} {'API':>7} {'Calls':>5} {'In Tok':>8} {'Out Tok':>8}")
    print(f"  {'-'*25} {'-'*7} {'-'*7} {'-'*5} {'-'*8} {'-'*8}")
    for rt in route_timings:
        api_t = sum(rt.api_calls)
        print(f"  {rt.name:<25} {rt.duration:>6.1f}s {api_t:>6.1f}s {len(rt.api_calls):>5} {rt.input_tokens:>8,} {rt.output_tokens:>8,}")

    # Parallelism analysis
    print(f"\n  --- Parallelism ---")
    serial_agent_time = sum(t.total for t in agent_timings)
    print(f"  Sum of all agent times (serial): {serial_agent_time:.1f}s")
    print(f"  Actual phase 1 wall clock:       {phase1_time:.1f}s")
    if serial_agent_time > 0:
        print(f"  Parallelism speedup:             {serial_agent_time / phase1_time:.1f}x")

    print(f"\n  Project written to: {project_root}")
    executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
