### Install the Claude Agent SDK for TypeScript or Python

Source: https://platform.claude.com/docs/en/agent-sdk/quickstart

These commands demonstrate how to install the Claude Agent SDK package using different package managers for TypeScript and Python. For TypeScript, `npm` is used. For Python, both `uv` (a fast Python package manager) and `pip` (standard Python package installer with virtual environment setup) options are provided.

```bash
npm install @anthropic-ai/claude-agent-sdk
```

```bash
uv init && uv add claude-agent-sdk
```

```bash
python3 -m venv .venv && source .venv/bin/activate
pip3 install claude-agent-sdk
```

---

### Set Custom System Prompt for Claude Agent (Python, TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/quickstart

This code shows how to configure a custom system prompt for a Claude agent, guiding its behavior and persona. It also specifies allowed tools and a permission mode for automatic approval of file edits, ensuring the agent follows specific guidelines.

```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Edit", "Glob"],
    permission_mode="acceptEdits",
    system_prompt="You are a senior Python developer. Always follow PEP 8 style guidelines.",
)
```

```typescript
const _ = {
  options: {
    allowedTools: ["Read", "Edit", "Glob"],
    permissionMode: "acceptEdits",
    systemPrompt:
      "You are a senior Python developer. Always follow PEP 8 style guidelines.",
  },
};
```

---

### Create a new project directory for the quickstart

Source: https://platform.claude.com/docs/en/agent-sdk/quickstart

This command creates a new directory named `my-agent` and then changes the current working directory into it. This directory will serve as the root for your agent project, allowing the SDK to access files within it and its subdirectories by default.

```bash
mkdir my-agent && cd my-agent
```

---

### List sessions example - Query and display sessions

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Example demonstrating how to use listSessions to retrieve sessions for a specific project or across all projects. Shows filtering by directory, limiting results, and displaying session information.

```typescript
import { listSessions } from "@anthropic-ai/claude-agent-sdk";

// List sessions for a specific project
const sessions = await listSessions({ dir: "/path/to/project" });

for (const session of sessions) {
  console.log(
    `${session.summary} (${new Date(session.lastModified).toLocaleDateString()})`,
  );
}

// List all sessions across all projects, limited to 10
const recent = await listSessions({ limit: 10 });
```

---

### Example of `query()` with options in Python

Source: https://docs.claude.com/en/api/agent-sdk/python

This example demonstrates how to use the `query()` function with custom `ClaudeAgentOptions` to configure the interaction. It sets a system prompt, permission mode, and current working directory, then asynchronously iterates through messages returned by Claude for a given prompt. This shows how to perform a single, configured interaction with Claude.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are an expert Python developer",
        permission_mode="acceptEdits",
        cwd="/home/user/project",
    )

    async for message in query(prompt="Create a Python web server", options=options):
        print(message)


asyncio.run(main())
```

---

### Configure and Query MCP Server with Multiple Tools

Source: https://platform.claude.com/docs/en/agent-sdk/custom-tools

This example demonstrates how to define multiple tools (calculate, translate, search_web) within an MCP server and then query the server while explicitly allowing only a subset of these tools. It shows the setup of the server and the `query` function call with `allowedTools` options for selective tool invocation.

```typescript
const multiToolServer = createSdkMcpServer({
  name: "utilities",
  version: "1.0.0",
  tools: [
    tool(
      "calculate",
      "Perform calculations",
      {
        /* ... */
      },
      async (args) => {
        // ...
      },
    ),
    tool(
      "translate",
      "Translate text",
      {
        /* ... */
      },
      async (args) => {
        // ...
      },
    ),
    tool(
      "search_web",
      "Search the web",
      {
        /* ... */
      },
      async (args) => {
        // ...
      },
    ),
  ],
});

// Allow only specific tools with streaming input
async function* generateMessages() {
  yield {
    type: "user" as const,
    message: {
      role: "user" as const,
      content: "Calculate 5 + 3 and translate 'hello' to Spanish",
    },
  };
}

for await (const message of query({
  prompt: generateMessages(), // Use async generator for streaming input
  options: {
    mcpServers: {
      utilities: multiToolServer,
    },
    allowedTools: [
      "mcp__utilities__calculate", // Allow calculator
      "mcp__utilities__translate", // Allow translator
      // "mcp__utilities__search_web" is NOT allowed
    ],
  },
})) {
  // Process messages
}
```

```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server,
)
from typing import Any
import asyncio


# Define multiple tools using the @tool decorator
@tool("calculate", "Perform calculations", {"expression": str})
async def calculate(args: dict[str, Any]) -> dict[str, Any]:
    result = eval(args["expression"])  # Use safe eval in production
    return {"content": [{"type": "text", "text": f"Result: {result}"}]}


@tool("translate", "Translate text", {"text": str, "target_lang": str})
async def translate(args: dict[str, Any]) -> dict[str, Any]:
    # Translation logic here
    return {"content": [{"type": "text", "text": f"Translated: {args['text']}"}]}


@tool("search_web", "Search the web", {"query": str})
async def search_web(args: dict[str, Any]) -> dict[str, Any]:
    # Search logic here
    return {
        "content": [{"type": "text", "text": f"Search results for: {args['query']}"}]
    }


multi_tool_server = create_sdk_mcp_server(
    name="utilities",
    version="1.0.0",
    tools=[calculate, translate, search_web],  # Pass decorated functions
)


# Allow only specific tools with streaming input
async def message_generator():
    yield {
        "type": "user",
        "message": {
            "role": "user",
            "content": "Calculate 5 + 3 and translate 'hello' to Spanish",
        },
    }


async for message in query(
    prompt=message_generator(),  # Use async generator for streaming input
    options=ClaudeAgentOptions(
        mcp_servers={"utilities": multi_tool_server},
        allowed_tools=[
            "mcp__utilities__calculate",  # Allow calculator
            "mcp__utilities__translate",  # Allow translator
            # "mcp__utilities__search_web" is NOT allowed
        ],
    ),
):
    if hasattr(message, "result"):
        print(message.result)
```

---

### Example SdkPluginConfig Usage for Claude Agent SDK (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This example demonstrates how to define a list of `SdkPluginConfig` objects. It shows both relative and absolute paths for local plugins. This configuration list can be passed to the SDK to load multiple plugins.

```python
plugins = [
    {"type": "local", "path": "./my-plugin"},
    {"type": "local", "path": "/absolute/path/to/plugin"},
]
```

---

### Example of `query()` with custom options in Python

Source: https://platform.claude.com/docs/en/agent-sdk/python

This example demonstrates how to use the `query()` function with `ClaudeAgentOptions` to configure a Claude Code interaction. It sets a system prompt, permission mode, and current working directory for the agent, then asynchronously queries Claude and prints the resulting messages.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are an expert Python developer",
        permission_mode="acceptEdits",
        cwd="/home/user/project"
    )

    async for message in query(prompt="Create a Python web server", options=options):
        print(message)


asyncio.run(main())
```

---

### Structured Output Example - Recipe Data

Source: https://platform.claude.com/docs/en/agent-sdk/structured-outputs

Example of structured output for a recipe agent that returns validated JSON with recipe metadata, ingredients, and cooking instructions instead of free-form text.

```json
{
  "name": "Chocolate Chip Cookies",
  "prep_time_minutes": 15,
  "cook_time_minutes": 10,
  "ingredients": [
    { "item": "all-purpose flour", "amount": 2.25, "unit": "cups" },
    { "item": "butter, softened", "amount": 1, "unit": "cup" }
  ],
  "steps": ["Preheat oven to 375°F", "Cream butter and sugar"]
}
```

---

### Configure Claude Agent with Custom MCP Server and Tools (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This example demonstrates how to define custom tools using the `@tool` decorator, create an MCP (Multi-Component Protocol) server with `create_sdk_mcp_server`, and integrate it into `ClaudeAgentOptions`. The `create_sdk_mcp_server` function returns an `McpSdkServerConfig` object, which is then passed to `ClaudeAgentOptions.mcp_servers` along with a list of allowed tools. This setup enables Claude to utilize the custom-defined 'add' and 'multiply' tools.

```python
from claude_agent_sdk import tool, create_sdk_mcp_server


@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args):
    return {"content": [{"type": "text", "text": f"Sum: {args['a'] + args['b']}"}]}


@tool("multiply", "Multiply two numbers", {"a": float, "b": float})
async def multiply(args):
    return {"content": [{"type": "text", "text": f"Product: {args['a'] * args['b']}"}]}


calculator = create_sdk_mcp_server(
    name="calculator",
    version="2.0.0",
    tools=[add, multiply],  # Pass decorated functions
)

# Use with Claude
options = ClaudeAgentOptions(
    mcp_servers={"calc": calculator},
    allowed_tools=["mcp__calc__add", "mcp__calc__multiply"],
)
```

---

### Implement `canUseTool` with user approval in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This TypeScript example illustrates how to use the `canUseTool` callback to prompt a user for approval before allowing a tool to execute. It includes a helper function to get user input from the terminal, displays details about the requested tool, and then returns an 'allow' or 'deny' behavior based on the user's response.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";
import * as readline from "readline";

// Helper to prompt user for input in the terminal
function prompt(question: string): Promise<string> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  return new Promise((resolve) =>
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer);
    }),
  );
}

for await (const message of query({
  prompt: "Create a test file in /tmp and then delete it",
  options: {
    canUseTool: async (toolName, input) => {
      // Display the tool request
      console.log(`\nTool: ${toolName}`);
      if (toolName === "Bash") {
        console.log(`Command: ${input.command}`);
        if (input.description) console.log(`Description: ${input.description}`);
      } else {
        console.log(`Input: ${JSON.stringify(input, null, 2)}`);
      }

      // Get user approval
      const response = await prompt("Allow this action? (y/n): ");

      // Return allow or deny based on user's response
      if (response.toLowerCase() === "y") {
        // Allow: tool executes with the original (or modified) input
        return { behavior: "allow", updatedInput: input };
      } else {
        // Deny: tool doesn't execute, Claude sees the message
        return { behavior: "deny", message: "User denied this action" };
      }
    },
  },
})) {
  if ("result" in message) console.log(message.result);
}
```

---

### Install Sandbox Runtime Package for Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/secure-deployment

This command installs the `@anthropic-ai/sandbox-runtime` package using npm. This package enables lightweight OS-level isolation for Agent SDK applications, enforcing filesystem and network restrictions. It's a foundational step for setting up the sandbox runtime environment without Docker or VMs.

```bash
npm install @anthropic-ai/sandbox-runtime
```

---

### Verify plugin installation and check loaded plugins

Source: https://platform.claude.com/docs/en/agent-sdk/plugins

Verify that plugins have loaded successfully by inspecting the system initialization message. Access the plugins list and available slash commands from the init message to confirm plugin availability and discover custom commands provided by loaded plugins.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Hello",
  options: {
    plugins: [{ type: "local", path: "./my-plugin" }],
  },
})) {
  if (message.type === "system" && message.subtype === "init") {
    // Check loaded plugins
    console.log("Plugins:", message.plugins);
    // Example: [{ name: "my-plugin", path: "./my-plugin" }]

    // Check available commands from plugins
    console.log("Commands:", message.slash_commands);
    // Example: ["/help", "/compact", "my-plugin:custom-command"]
  }
}
```

```python
import asyncio
from claude_agent_sdk import query


async def main():
    async for message in query(
        prompt="Hello", options={"plugins": [{"type": "local", "path": "./my-plugin"}]}
    ):
        if message.type == "system" and message.subtype == "init":
            # Check loaded plugins
            print("Plugins:", message.data.get("plugins"))
            # Example: [{"name": "my-plugin", "path": "./my-plugin"}]

            # Check available commands from plugins
            print("Commands:", message.data.get("slash_commands"))
            # Example: ["/help", "/compact", "my-plugin:custom-command"]


asyncio.run(main())
```

---

### Method ClaudeSDKClient.connect

Source: https://platform.claude.com/docs/en/agent-sdk/python

Establishes a connection for the conversation session, optionally starting with an initial prompt.

````APIDOC
## METHOD ClaudeSDKClient.connect

### Description
Establishes a connection for the conversation session, optionally starting with an initial prompt.

### Method
Async Class Method

### Endpoint
async def connect(self, prompt: str | AsyncIterable[dict] | None = None) -> None

### Parameters
#### Request Body
- **prompt** (str | AsyncIterable[dict] | None) - Optional - The initial prompt or messages to send when connecting.

### Request Example
```python
# Assuming 'client' is an initialized ClaudeSDKClient instance
await client.connect("Hello Claude!")
````

### Response

#### Success Response (200)

- **None** - The method returns nothing upon successful connection.

#### Response Example

```python
# No explicit return value
```

````

--------------------------------

### Example of defining a custom tool in Python

Source: https://docs.claude.com/en/api/agent-sdk/python

This example demonstrates how to define a custom tool using the `@tool` decorator. It creates a 'greet' tool that takes a 'name' as input and returns a greeting message. This illustrates the practical application of the `tool()` decorator for integrating custom functionalities into the Claude Agent SDK.

```python
from claude_agent_sdk import tool
from typing import Any


@tool("greet", "Greet a user", {"name": str})
async def greet(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Hello, {args['name']}!"}]}
````

---

### Example CLAUDE.md File Content

Source: https://platform.claude.com/docs/en/agent-sdk/modifying-system-prompts

Illustrates the structure and content of a CLAUDE.md file, which can include project guidelines, code style rules, testing requirements, and common commands. This file serves as persistent, project-specific instructions for Claude.

```markdown
# Project Guidelines

## Code Style

- Use TypeScript strict mode
- Prefer functional components in React
- Always include JSDoc comments for public APIs

## Testing

- Run `npm test` before committing
- Maintain >80% code coverage
- Use jest for unit tests, playwright for E2E

## Commands

- Build: `npm run build`
- Dev server: `npm run dev`
- Type check: `npm run typecheck`
```

---

### Configure your Anthropic API key in a .env file

Source: https://platform.claude.com/docs/en/agent-sdk/quickstart

This step involves creating a `.env` file in your project directory and adding your Anthropic API key to it. This allows the SDK to authenticate with the Claude API. Alternative authentication methods for Amazon Bedrock, Google Vertex AI, and Microsoft Azure are also mentioned.

```bash
ANTHROPIC_API_KEY=your-api-key
```

---

### Implement complete file checkpointing flow with Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/file-checkpointing

This example demonstrates the complete file checkpointing workflow using the Claude Agent SDK. It covers enabling checkpointing, capturing the checkpoint UUID and session ID from the response stream, and subsequently resuming the session to rewind files to a previous state.

```python
import asyncio
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    UserMessage,
    ResultMessage,
)


async def main():
    # Step 1: Enable checkpointing
    options = ClaudeAgentOptions(
        enable_file_checkpointing=True,
        permission_mode="acceptEdits",  # Auto-accept file edits without prompting
        extra_args={
            "replay-user-messages": None
        },  # Required to receive checkpoint UUIDs in the response stream
    )

    checkpoint_id = None
    session_id = None

    # Run the query and capture checkpoint UUID and session ID
    async with ClaudeSDKClient(options) as client:
        await client.query("Refactor the authentication module")

        # Step 2: Capture checkpoint UUID from the first user message
        async for message in client.receive_response():
            if isinstance(message, UserMessage) and message.uuid and not checkpoint_id:
                checkpoint_id = message.uuid
            if isinstance(message, ResultMessage) and not session_id:
                session_id = message.session_id

    # Step 3: Later, rewind by resuming the session with an empty prompt
    if checkpoint_id and session_id:
        async with ClaudeSDKClient(
            ClaudeAgentOptions(enable_file_checkpointing=True, resume=session_id)
        ) as client:
            await client.query("")  # Empty prompt to open the connection
            async for message in client.receive_response():
                await client.rewind_files(checkpoint_id)
                break
        print(f"Rewound to checkpoint: {checkpoint_id}")


asyncio.run(main())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

async function main() {
  // Step 1: Enable checkpointing
  const opts = {
    enableFileCheckpointing: true,
    permissionMode: "acceptEdits" as const, // Auto-accept file edits without prompting
    extraArgs: { "replay-user-messages": null }, // Required to receive checkpoint UUIDs in the response stream
  };

  const response = query({
    prompt: "Refactor the authentication module",
    options: opts,
  });

  let checkpointId: string | undefined;
  let sessionId: string | undefined;

  // Step 2: Capture checkpoint UUID from the first user message
  for await (const message of response) {
    if (message.type === "user" && message.uuid && !checkpointId) {
      checkpointId = message.uuid;
    }
    if ("session_id" in message && !sessionId) {
      sessionId = message.session_id;
    }
  }

  // Step 3: Later, rewind by resuming the session with an empty prompt
  if (checkpointId && sessionId) {
    const rewindQuery = query({
      prompt: "", // Empty prompt to open the connection
      options: { ...opts, resume: sessionId },
    });

    for await (const msg of rewindQuery) {
      await rewindQuery.rewindFiles(checkpointId);
      break;
    }
    console.log(`Rewound to checkpoint: ${checkpointId}`);
  }
}

main();
```

---

### Execute Claude Agent from Command Line (Bash)

Source: https://platform.claude.com/docs/en/agent-sdk/quickstart

This snippet provides the command-line instructions to run the Claude agent created with the SDK. It includes separate commands for executing the agent script in both Python and TypeScript environments, demonstrating the final step to activate the agent's automated code analysis and fixing capabilities.

```bash
python3 agent.py
```

```bash
npx tsx agent.ts
```

---

### Define intentionally buggy Python utility functions

Source: https://platform.claude.com/docs/en/agent-sdk/quickstart

This Python code snippet creates a `utils.py` file containing two functions, `calculate_average` and `get_user_name`, which are designed with specific bugs. These bugs (division by zero and TypeError) serve as targets for the AI agent to identify and fix during the quickstart.

```python
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)


def get_user_name(user):
    return user["name"].upper()
```

---

### Approving Tool Execution As-Is in Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This example demonstrates how to approve a tool's execution without modifying its input, passing the original input through. This is useful when the user explicitly allows the action as Claude requested.

```python
async def can_use_tool(tool_name, input_data, context):
    print(f"Claude wants to use {tool_name}")
    approved = await ask_user("Allow this action?")

    if approved:
        return PermissionResultAllow(updated_input=input_data)
    return PermissionResultDeny(message="User declined")
```

```typescript
canUseTool: async (toolName, input) => {
  console.log(`Claude wants to use ${toolName}`);
  const approved = await askUser("Allow this action?");

  if (approved) {
    return { behavior: "allow", updatedInput: input };
  }
  return { behavior: "deny", message: "User declined" };
};
```

---

### Rejecting Tool Execution with Explanation in Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This example demonstrates how to block a tool's execution and provide a specific message to Claude explaining why. Claude will read this message and may try a different approach based on the feedback.

```python
async def can_use_tool(tool_name, input_data, context):
    approved = await ask_user(f"Allow {tool_name}?")

    if not approved:
        return PermissionResultDeny(message="User rejected this action")
    return PermissionResultAllow(updated_input=input_data)
```

```typescript
canUseTool: async (toolName, input) => {
  const approved = await askUser(`Allow ${toolName}?`);

  if (!approved) {
    return {
      behavior: "deny",
      message: "User rejected this action",
    };
  }
  return { behavior: "allow", updatedInput: input };
};
```

---

### Example Claude Agent Input Question Structure (JSON)

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This JSON example illustrates the structure of a question object provided to a Claude agent. It defines fields such as `question` for the full text, `header` for a short label, `options` for available choices, and `multiSelect` to indicate if multiple options can be selected. This format helps the agent understand and present questions to the user.

```json
{
  "questions": [
    {
      "question": "How should I format the output?",
      "header": "Format",
      "options": [
        { "label": "Summary", "description": "Brief overview of key points" },
        { "label": "Detailed", "description": "Full explanation with examples" }
      ],
      "multiSelect": false
    }
  ]
}
```

---

### Monitor Todo Changes with Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/todo-tracking

Stream and monitor todo updates from the Claude Agent SDK query. This example demonstrates how to listen for TodoWrite tool calls in the message stream, extract todo items, and display their current status (pending, in_progress, or completed) with visual indicators. Requires the Claude Agent SDK to be installed and configured.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Optimize my React app performance and track progress with todos",
  options: { maxTurns: 15 },
})) {
  // Todo updates are reflected in the message stream
  if (message.type === "assistant") {
    for (const block of message.message.content) {
      if (block.type === "tool_use" && block.name === "TodoWrite") {
        const todos = block.input.todos;

        console.log("Todo Status Update:");
        todos.forEach((todo, index) => {
          const status =
            todo.status === "completed"
              ? "✅"
              : todo.status === "in_progress"
                ? "🔧"
                : "❌";
          console.log(`${index + 1}. ${status} ${todo.content}`);
        });
      }
    }
  }
}
```

```python
from claude_agent_sdk import query, AssistantMessage, ToolUseBlock

async for message in query(
    prompt="Optimize my React app performance and track progress with todos",
    options={"max_turns": 15},
):
    # Todo updates are reflected in the message stream
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, ToolUseBlock) and block.name == "TodoWrite":
                todos = block.input["todos"]

                print("Todo Status Update:")
                for i, todo in enumerate(todos):
                    status = (
                        "✅"
                        if todo["status"] == "completed"
                        else "🔧"
                        if todo["status"] == "in_progress"
                        else "❌"
                    )
                    print(f"{i + 1}. {status} {todo['content']}")
```

---

### Hook Usage Example - Security and Logging

Source: https://platform.claude.com/docs/en/agent-sdk/python

Demonstrates how to register and configure multiple hooks for the Claude Agent SDK. This example shows a security hook that blocks dangerous bash commands and a logging hook for audit trails, with hook matchers to control which tools trigger each hook.

````APIDOC
## Hook Registration and Configuration

### Description
Registers security and logging hooks for the Claude Agent SDK to validate tool usage and maintain audit logs.

### Hook Types

#### PreToolUse Hook - validate_bash_command
Validates and blocks dangerous bash commands before execution.

**Parameters:**
- **input_data** (dict[str, Any]) - Required - Tool execution data containing tool_name and tool_input
- **tool_use_id** (str | None) - Optional - Unique identifier for the tool use
- **context** (HookContext) - Required - Hook execution context

**Returns:**
- **hookSpecificOutput** (dict) - Optional - Contains permissionDecision ("deny"/"allow") and permissionDecisionReason

#### PreToolUse Hook - log_tool_use
Logs all tool usage for auditing purposes.

**Parameters:**
- **input_data** (dict[str, Any]) - Required - Tool execution data
- **tool_use_id** (str | None) - Optional - Tool use identifier
- **context** (HookContext) - Required - Hook execution context

**Returns:**
- Empty dict on successful logging

### Configuration

**ClaudeAgentOptions.hooks** structure:
- **PreToolUse** (list[HookMatcher]) - Hooks executed before tool execution
  - **HookMatcher.matcher** (str) - Optional - Tool name filter (e.g., "Bash")
  - **HookMatcher.hooks** (list[callable]) - Required - Hook functions to execute
  - **HookMatcher.timeout** (int) - Optional - Timeout in seconds (default 60s)
- **PostToolUse** (list[HookMatcher]) - Hooks executed after tool execution

### Request Example
```python
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher, HookContext
from typing import Any

async def validate_bash_command(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Validate and potentially block dangerous bash commands."""
    if input_data["tool_name"] == "Bash":
        command = input_data["tool_input"].get("command", "")
        if "rm -rf /" in command:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Dangerous command blocked",
                }
            }
    return {}

async def log_tool_use(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Log all tool usage for auditing."""
    print(f"Tool used: {input_data.get('tool_name')}")
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(
                matcher="Bash", hooks=[validate_bash_command], timeout=120
            ),
            HookMatcher(
                hooks=[log_tool_use]
            ),
        ],
        "PostToolUse": [HookMatcher(hooks=[log_tool_use])],
    }
)

async for message in query(prompt="Analyze this codebase", options=options):
    print(message)
````

````

--------------------------------

### Create an AI Agent to List Directory Files with Claude Agent SDK (Python/TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/overview

This example illustrates how to build an AI agent that can list files in the current directory using the SDK's built-in `Bash` and `Glob` tools. The agent processes the prompt and prints the results returned by Claude.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    async for message in query(
        prompt="What files are in this directory?",
        options=ClaudeAgentOptions(allowed_tools=["Bash", "Glob"]),
    ):
            if hasattr(message, "result"):
                print(message.result)


asyncio.run(main())
````

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "What files are in this directory?",
  options: { allowedTools: ["Bash", "Glob"] },
})) {
  if ("result" in message) console.log(message.result);
}
```

---

### Custom System Prompt with Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/migration-guide

Demonstrates how to set a custom system prompt when querying the Claude Agent SDK. This provides better control over agent behavior without inheriting default CLI-focused instructions. The example shows an async query with custom options.

```python
async for message in query(
    prompt="Hello",
    options=ClaudeAgentOptions(system_prompt="You are a helpful coding assistant"),
):
    print(message)
```

---

### Load All Filesystem Settings in Claude Agent SDK (Legacy)

Source: https://docs.claude.com/en/api/agent-sdk/python

This Python example demonstrates how to configure the Claude Agent SDK to load all available filesystem settings, including user, project, and local configurations. This mirrors the legacy behavior of SDK versions prior to `v0.0.x` and is achieved by explicitly listing all `SettingSource` values in `setting_sources`.

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Analyze this code",
    options=ClaudeAgentOptions(
        setting_sources=["user", "project", "local"]  # Load all settings
    ),
):
    print(message)
```

---

### Client Method: connect(prompt)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Establishes a connection to Claude, optionally providing an initial prompt or message stream to start a conversation. This method is typically called after client initialization.

````APIDOC
## Client Method: connect(prompt)

### Description
Connect to Claude with an optional initial prompt or message stream. This method initiates the communication session.

### Method
connect

### Parameters
#### Arguments
- **prompt** (string | async generator) - Optional - An initial text prompt or an asynchronous generator yielding message objects to start the conversation.

### Request Example
```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient

async def main():
    async with ClaudeSDKClient() as client:
        await client.connect("Hello Claude, let's begin.")
        # Or with a message stream:
        # async def initial_stream():
        #     yield {"type": "user", "message": {"role": "user", "content": "Initial message"}}
        # await client.connect(initial_stream())

asyncio.run(main())
````

### Response

#### Return Value

- **None** - This method does not return a direct value; it establishes the connection.

#### Response Example

```json
null
```

````

--------------------------------

### Implement Streaming UI with Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/streaming-output

This example demonstrates how to create a streaming user interface using the Claude Agent SDK, combining real-time text output with status indicators for tool execution. It utilizes `StreamEvent` messages to detect tool starts and stops, managing an `in_tool` flag to control when text is streamed and when tool status messages are displayed. The `query` function is used with `include_partial_messages` enabled to receive granular updates.

```python
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from claude_agent_sdk.types import StreamEvent
import asyncio
import sys


async def streaming_ui():
    options = ClaudeAgentOptions(
        include_partial_messages=True,
        allowed_tools=["Read", "Bash", "Grep"],
    )

    # Track whether we're currently in a tool call
    in_tool = False

    async for message in query(
        prompt="Find all TODO comments in the codebase", options=options
    ):
        if isinstance(message, StreamEvent):
            event = message.event
            event_type = event.get("type")

            if event_type == "content_block_start":
                content_block = event.get("content_block", {})
                if content_block.get("type") == "tool_use":
                    # Tool call is starting - show status indicator
                    tool_name = content_block.get("name")
                    print(f"\n[Using {tool_name}...]", end="", flush=True)
                    in_tool = True

            elif event_type == "content_block_delta":
                delta = event.get("delta", {})
                # Only stream text when not executing a tool
                if delta.get("type") == "text_delta" and not in_tool:
                    sys.stdout.write(delta.get("text", ""))
                    sys.stdout.flush()

            elif event_type == "content_block_stop":
                if in_tool:
                    # Tool call finished
                    print(" done", flush=True)
                    in_tool = False

        elif isinstance(message, ResultMessage):
            # Agent finished all work
            print(f"\n\n--- Complete ---")


asyncio.run(streaming_ui())
````

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Track whether we're currently in a tool call
let inTool = false;

for await (const message of query({
  prompt: "Find all TODO comments in the codebase",
  options: {
    includePartialMessages: true,
    allowedTools: ["Read", "Bash", "Grep"],
  },
})) {
  if (message.type === "stream_event") {
    const event = message.event;

    if (event.type === "content_block_start") {
      if (event.content_block.type === "tool_use") {
        // Tool call is starting - show status indicator
        process.stdout.write(`\n[Using ${event.content_block.name}...]`);
        inTool = true;
      }
    } else if (event.type === "content_block_delta") {
      // Only stream text when not executing a tool
      if (event.delta.type === "text_delta" && !inTool) {
        process.stdout.write(event.delta.text);
      }
    } else if (event.type === "content_block_stop") {
      if (inTool) {
        // Tool call finished
        console.log(" done");
        inTool = false;
      }
    }
  } else if (message.type === "result") {
    // Agent finished all work
    console.log("\n\n--- Complete ---");
  }
}
```

---

### Load and Inspect Local Plugins in Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/plugins

This comprehensive example illustrates how to load a local plugin, query the Claude agent for available commands, and process system initialization messages to inspect loaded plugins and their slash commands. It demonstrates dynamic path resolution for plugins and handling different message types.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";
import * as path from "path";

async function runWithPlugin() {
  const pluginPath = path.join(__dirname, "plugins", "my-plugin");

  console.log("Loading plugin from:", pluginPath);

  for await (const message of query({
    prompt: "What custom commands do you have available?",
    options: {
      plugins: [{ type: "local", path: pluginPath }],
      maxTurns: 3,
    },
  })) {
    if (message.type === "system" && message.subtype === "init") {
      console.log("Loaded plugins:", message.plugins);
      console.log("Available commands:", message.slash_commands);
    }

    if (message.type === "assistant") {
      console.log("Assistant:", message.content);
    }
  }
}

runWithPlugin().catch(console.error);
```

```python
#!/usr/bin/env python3
"""Example demonstrating how to use plugins with the Agent SDK."""

from pathlib import Path
import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    query,
)


async def run_with_plugin():
    """Example using a custom plugin."""
    plugin_path = Path(__file__).parent / "plugins" / "demo-plugin"

    print(f"Loading plugin from: {plugin_path}")

    options = ClaudeAgentOptions(
        plugins=[{"type": "local", "path": str(plugin_path)}],
        max_turns=3,
    )

    async for message in query(
        prompt="What custom commands do you have available?", options=options
    ):
        if message.type == "system" and message.subtype == "init":
            print(f"Loaded plugins: {message.data.get('plugins')}")
            print(f"Available commands: {message.data.get('slash_commands')}")

        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Assistant: {block.text}")


if __name__ == "__main__":
    anyio.run(run_with_plugin)
```

---

### Load CLAUDE.md Project Instructions with Claude Agent SDK

Source: https://docs.claude.com/en/api/agent-sdk/python

This Python example shows how to load project-specific instructions from `CLAUDE.md` files using the Claude Agent SDK. It configures a preset system prompt (`claude_code`) and crucially sets `setting_sources=['project']`, which is required for the SDK to access and incorporate `CLAUDE.md` files from the project directory.

```python
async for message in query(
    prompt="Add a new feature following project conventions",
    options=ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",  # Use Claude Code's system prompt
        },
        setting_sources=["project"],  # Required to load CLAUDE.md from project
        allowed_tools=["Read", "Write", "Edit"],
    ),
):
    print(message)
```

---

### Implement Claude Agent for Automated Bug Fixing (Python/TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/quickstart

This code demonstrates how to build an AI agent using the Claude Agent SDK in both Python and TypeScript. It initializes an agentic loop with a prompt to review and fix bugs in `utils.py`, configuring `allowedTools` (Read, Edit, Glob) and `permissionMode` to `acceptEdits`. The `async for` loop streams messages, allowing real-time output of Claude's reasoning, tool calls, and final results as it autonomously performs code analysis and modifications.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage


async def main():
    # Agentic loop: streams messages as Claude works
    async for message in query(
        prompt="Review utils.py for bugs that would cause crashes. Fix any issues you find.",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Glob"],  # Tools Claude can use
            permission_mode="acceptEdits",  # Auto-approve file edits
        ),
    ):
        # Print human-readable output
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)  # Claude's reasoning
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")  # Tool being called
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")  # Final result


asyncio.run(main())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Agentic loop: streams messages as Claude works
for await (const message of query({
  prompt:
    "Review utils.py for bugs that would cause crashes. Fix any issues you find.",
  options: {
    allowedTools: ["Read", "Edit", "Glob"], // Tools Claude can use
    permissionMode: "acceptEdits", // Auto-approve file edits
  },
})) {
  // Print human-readable output
  if (message.type === "assistant" && message.message?.content) {
    for (const block of message.message.content) {
      if ("text" in block) {
        console.log(block.text); // Claude's reasoning
      } else if ("name" in block) {
        console.log(`Tool: ${block.name}`); // Tool being called
      }
    }
  } else if (message.type === "result") {
    console.log(`Done: ${message.subtype}`); // Final result
  }
}
```

---

### Query with Sandbox Settings Configuration

Source: https://docs.claude.com/en/api/agent-sdk/python

Demonstrates how to initialize and execute a query with custom sandbox settings using the Claude Agent SDK. This example enables sandbox mode with bash auto-allow and local network binding for development servers. The async iterator pattern allows streaming responses from the agent.

```python
from claude_agent_sdk import query, ClaudeAgentOptions, SandboxSettings

sandbox_settings: SandboxSettings = {
    "enabled": True,
    "autoAllowBashIfSandboxed": True,
    "network": {"allowLocalBinding": True},
}

async for message in query(
    prompt="Build and test my project",
    options=ClaudeAgentOptions(sandbox=sandbox_settings),
):
    print(message)
```

---

### Getting Session ID - TypeScript and Python

Source: https://platform.claude.com/docs/en/agent-sdk/sessions

Demonstrates how to capture the session ID from the initial system message when starting a new query. The SDK automatically creates a session and returns the ID in the first system init message, which can be saved for later resumption.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

let sessionId: string | undefined;

const response = query({
  prompt: "Help me build a web application",
  options: {
    model: "claude-opus-4-6",
  },
});

for await (const message of response) {
  // The first message is a system init message with the session ID
  if (message.type === "system" && message.subtype === "init") {
    sessionId = message.session_id;
    console.log(`Session started with ID: ${sessionId}`);
    // You can save this ID for later resumption
  }

  // Process other messages...
  console.log(message);
}

// Later, you can use the saved sessionId to resume
if (sessionId) {
  const resumedResponse = query({
    prompt: "Continue where we left off",
    options: {
      resume: sessionId,
    },
  });
}
```

```python
from claude_agent_sdk import query, ClaudeAgentOptions

session_id = None

async for message in query(
    prompt="Help me build a web application",
    options=ClaudeAgentOptions(model="claude-opus-4-6"),
):
    # The first message is a system init message with the session ID
    if hasattr(message, "subtype") and message.subtype == "init":
        session_id = message.data.get("session_id")
        print(f"Session started with ID: {session_id}")
        # You can save this ID for later resumption

    # Process other messages...
    print(message)

# Later, you can use the saved session_id to resume
if session_id:
    async for message in query(
        prompt="Continue where we left off",
        options=ClaudeAgentOptions(resume=session_id),
    ):
        print(message)
```

---

### Implement `can_use_tool` with streaming in Python

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This Python example demonstrates how to set up the `can_use_tool` callback for the Claude Agent SDK in streaming mode. It includes a `dummy_hook` to maintain the stream's open state, defines a `prompt_stream` for initial user input, and shows how to integrate these components within the `main` function to query the agent and process its responses.

```python
async def dummy_hook(input_data, tool_use_id, context):
    return {"continue_": True}


async def prompt_stream():
    yield {
        "type": "user",
        "message": {
            "role": "user",
            "content": "Create a test file in /tmp and then delete it",
        },
    }


async def main():
    async for message in query(
        prompt=prompt_stream(),
        options=ClaudeAgentOptions(
            can_use_tool=can_use_tool,
            hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[dummy_hook])]}
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
```

---

### Install Claude Agent Python SDK

Source: https://docs.claude.com/en/api/agent-sdk/python

This command installs the Claude Agent Python SDK using pip, the Python package installer. It's the first step to integrate the SDK into your Python projects, allowing access to Claude's functionalities.

```bash
pip install claude-agent-sdk
```

---

### GET /tools/ListMcpResources

Source: https://docs.claude.com/en/api/agent-sdk/python

Lists all available MCP (Model Context Protocol) resources, optionally filtered by server name. Returns a collection of resources with their metadata.

````APIDOC
## GET /tools/ListMcpResources

### Description
Lists all available MCP (Model Context Protocol) resources, optionally filtered by server name. Returns a collection of resources with their metadata.

### Method
GET

### Endpoint
/tools/ListMcpResources

### Tool Name
ListMcpResources

### Parameters
#### Request Body
- **server** (string | null) - Optional - Server name to filter resources by

### Request Example
```json
{
  "server": "my-mcp-server"
}
````

### Response

#### Success Response (200)

- **resources** (array) - Array of resource objects
  - **uri** (string) - Resource URI identifier
  - **name** (string) - Resource name
  - **description** (string | null) - Resource description
  - **mimeType** (string | null) - MIME type of the resource
  - **server** (string) - MCP server name
- **total** (integer) - Total number of resources returned

#### Response Example

```json
{
  "resources": [
    {
      "uri": "resource://file1",
      "name": "File 1",
      "description": "Sample resource file",
      "mimeType": "text/plain",
      "server": "my-mcp-server"
    }
  ],
  "total": 1
}
```

````

--------------------------------

### Get the total cost of a query using Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/cost-tracking

This example demonstrates how to retrieve the total cost of a `query()` call using the Claude Agent SDK. It iterates over the message stream and prints the `total_cost_usd` from the final `result` message, which provides the cumulative cost for all steps within that specific query. This method works for both successful and erroneous queries.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({ prompt: "Summarize this project" })) {
  if (message.type === "result") {
    console.log(`Total cost: $${message.total_cost_usd}`);
  }
}
````

```python
from claude_agent_sdk import query, ResultMessage
import asyncio


async def main():
    async for message in query(prompt="Summarize this project"):
        if isinstance(message, ResultMessage):
            print(f"Total cost: ${message.total_cost_usd or 0}")


asyncio.run(main())
```

---

### Configure TypeScript Agent with `allowedTools` and `dontAsk` Permission Mode

Source: https://platform.claude.com/docs/en/agent-sdk/permissions

This TypeScript example demonstrates how to configure a Claude Agent SDK instance to use specific `allowedTools` in conjunction with the `dontAsk` permission mode. This setup ensures that only the listed tools (`Read`, `Glob`, `Grep`) are automatically approved, and any other unlisted tools are explicitly denied without prompting the user, providing a locked-down agent behavior.

```typescript
const options = {
  allowedTools: ["Read", "Glob", "Grep"],
  permissionMode: "dontAsk",
};
```

---

### Suggesting Alternatives After Denying Tool Execution in Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This snippet shows how to deny a tool's execution but also guide Claude towards a preferred alternative action by including specific suggestions in the denial message. Claude will use this feedback to decide how to proceed.

```python
async def can_use_tool(tool_name, input_data, context):
    if tool_name == "Bash" and "rm" in input_data.get("command", ""):
        # User doesn't want to delete, suggest archiving instead
        return PermissionResultDeny(
            message="User doesn't want to delete files. They asked if you could compress them into an archive instead."
        )
    return PermissionResultAllow(updated_input=input_data)
```

```typescript
canUseTool: async (toolName, input) => {
  if (toolName === "Bash" && input.command.includes("rm")) {
    // User doesn't want to delete, suggest archiving instead
    return {
      behavior: "deny",
      message:
```

---

### Example of AskUserQuestion Input Structure

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This JSON snippet demonstrates the structure of the `input` data received when Claude calls `AskUserQuestion`. It contains a `questions` array, where each object specifies the question text, options, and whether multiple selections are allowed.

```json
{
  "questions": [
    {
      "question": "How should I format the output?",
      "header": "Format",
      "options": [
        { "label": "Summary", "description": "Brief overview" },
        { "label": "Detailed", "description": "Full explanation" }
      ],
      "multiSelect": false
    },
    {
      "question": "Which sections should I include?",
      "header": "Sections",
      "options": [
        { "label": "Introduction", "description": "Opening context" },
        { "label": "Conclusion", "description": "Final summary" }
      ],
      "multiSelect": true
    }
  ]
}
```

---

### Fork a Claude Agent SDK Session in TypeScript and Python

Source: https://platform.claude.com/docs/en/agent-sdk/sessions

This example demonstrates how to initiate a conversational session with the Claude Agent SDK, capture its unique session ID, and then fork that session to pursue a different conversational direction without altering the original. It also shows how to resume the original session later. This pattern is useful for exploring multiple design options or scenarios from a common starting point.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// First, capture the session ID
let sessionId: string | undefined;

const response = query({
  prompt: "Help me design a REST API",
  options: { model: "claude-opus-4-6" },
});

for await (const message of response) {
  if (message.type === "system" && message.subtype === "init") {
    sessionId = message.session_id;
    console.log(`Original session: ${sessionId}`);
  }
}

// Fork the session to try a different approach
const forkedResponse = query({
  prompt: "Now let's redesign this as a GraphQL API instead",
  options: {
    resume: sessionId,
    forkSession: true, // Creates a new session ID
    model: "claude-opus-4-6",
  },
});

for await (const message of forkedResponse) {
  if (message.type === "system" && message.subtype === "init") {
    console.log(`Forked session: ${message.session_id}`);
    // This will be a different session ID
  }
}

// The original session remains unchanged and can still be resumed
const originalContinued = query({
  prompt: "Add authentication to the REST API",
  options: {
    resume: sessionId,
    forkSession: false, // Continue original session (default)
    model: "claude-opus-4-6",
  },
});
```

```python
from claude_agent_sdk import query, ClaudeAgentOptions

# First, capture the session ID
session_id = None

async for message in query(
    prompt="Help me design a REST API",
    options=ClaudeAgentOptions(model="claude-opus-4-6"),
):
    if hasattr(message, "subtype") and message.subtype == "init":
        session_id = message.data.get("session_id")
        print(f"Original session: {session_id}")

# Fork the session to try a different approach
async for message in query(
    prompt="Now let's redesign this as a GraphQL API instead",
    options=ClaudeAgentOptions(
        resume=session_id,
        fork_session=True,  # Creates a new session ID
        model="claude-opus-4-6",
    ),
):
    if hasattr(message, "subtype") and message.subtype == "init":
        forked_id = message.data.get("session_id")
        print(f"Forked session: {forked_id}")
        # This will be a different session ID

# The original session remains unchanged and can still be resumed
async for message in query(
    prompt="Add authentication to the REST API",
    options=ClaudeAgentOptions(
        resume=session_id,
        fork_session=False,  # Continue original session (default)
        model="claude-opus-4-6",
    ),
):
    print(message)
```

---

### Example of `SdkPluginConfig` Usage in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Illustrates how to configure local plugins using the `SdkPluginConfig` type within an array. Each entry specifies `type: "local"` and the `path` to the plugin directory, demonstrating both relative and absolute path usage.

```typescript
plugins: [
  { type: "local", path: "./my-plugin" },
  { type: "local", path: "/absolute/path/to/plugin" },
];
```

---

### Configure Local Filesystem MCP Server In-Code (TypeScript/Python)

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

This example demonstrates how to define a local filesystem MCP server directly within the `mcpServers` option of the `query()` function. It uses `npx` to run the `@modelcontextprotocol/server-filesystem` command, allowing the agent to interact with the local file system. The `allowedTools` option grants access to all tools provided by this server.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "List files in my project",
  options: {
    mcpServers: {
      filesystem: {
        command: "npx",
        args: [
          "-y",
          "@modelcontextprotocol/server-filesystem",
          "/Users/me/projects",
        ],
      },
    },
    allowedTools: ["mcp__filesystem__*"],
  },
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}
```

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


async def main():
    options = ClaudeAgentOptions(
        mcp_servers={
            "filesystem": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "/Users/me/projects",
                ],
            }
        },
        allowed_tools=["mcp__filesystem__*"],
    )

    async for message in query(prompt="List files in my project", options=options):
        if isinstance(message, ResultMessage) and message.subtype == "success":
            print(message.result)


asyncio.run(main())
```

---

### Enable Web Search Capability for Claude Agent (Python, TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/quickstart

This snippet demonstrates how to add web search functionality to a Claude agent by including 'WebSearch' in the `allowed_tools` (Python) or `allowedTools` (TypeScript) option. It also sets the `permission_mode` to 'acceptEdits' for automatic approval of file edits.

```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Edit", "Glob", "WebSearch"], permission_mode="acceptEdits"
)
```

```typescript
const _ = {
  options: {
    allowedTools: ["Read", "Edit", "Glob", "WebSearch"],
    permissionMode: "acceptEdits",
  },
};
```

---

### Install TypeScript Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Install the @anthropic-ai/claude-agent-sdk package which includes the V2 interface. This is a prerequisite for using the V2 SDK features.

```bash
npm install @anthropic-ai/claude-agent-sdk
```

---

### Define a Custom Command with File References in Markdown

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

This example shows how to include the contents of local files directly into a custom command's prompt using the `@` prefix. The `/review-config` command is designed to review specified configuration files (e.g., `package.json`, `tsconfig.json`, `.env`) for issues like security vulnerabilities or misconfigurations.

```markdown
---
description: Review configuration files
---

Review the following configuration files for issues:

- Package config: @package.json
- TypeScript config: @tsconfig.json
- Environment config: @.env

Check for security issues, outdated dependencies, and misconfigurations.
```

---

### Configure Project-Specific Plugin Loading (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/plugins

This example demonstrates how to configure the Claude Agent SDK to load plugins from a directory relative to your project. This approach ensures that all team members use the same plugin versions and configurations, promoting consistency for project-specific extensions.

```typescript
plugins: [{ type: "local", path: "./project-plugins/team-workflows" }];
```

---

### Dynamically Configure Claude Subagents (Python, TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/subagents

This example illustrates how to create agent definitions dynamically based on runtime conditions, such as varying security levels. It uses a factory function pattern to customize an agent's prompt, tools, and model, allowing for flexible configuration at query time. This enables using more capable models for high-stakes reviews.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition


# Factory function that returns an AgentDefinition
# This pattern lets you customize agents based on runtime conditions
def create_security_agent(security_level: str) -> AgentDefinition:
    is_strict = security_level == "strict"
    return AgentDefinition(
        description="Security code reviewer",
        # Customize the prompt based on strictness level
        prompt=f"You are a {'strict' if is_strict else 'balanced'} security reviewer...",
        tools=["Read", "Grep", "Glob"],
        # Key insight: use a more capable model for high-stakes reviews
        model="opus" if is_strict else "sonnet",
    )


async def main():
    # The agent is created at query time, so each request can use different settings
    async for message in query(
        prompt="Review this PR for security issues",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Grep", "Glob", "Task"],
            agents={
                # Call the factory with your desired configuration
                "security-reviewer": create_security_agent("strict")
            },
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
```

```typescript
import { query, type AgentDefinition } from "@anthropic-ai/claude-agent-sdk";

// Factory function that returns an AgentDefinition
// This pattern lets you customize agents based on runtime conditions
function createSecurityAgent(
  securityLevel: "basic" | "strict",
): AgentDefinition {
  const isStrict = securityLevel === "strict";
  return {
    description: "Security code reviewer",
    // Customize the prompt based on strictness level
    prompt: `You are a ${isStrict ? "strict" : "balanced"} security reviewer...`,
    tools: ["Read", "Grep", "Glob"],
    // Key insight: use a more capable model for high-stakes reviews
    model: isStrict ? "opus" : "sonnet",
  };
}

// The agent is created at query time, so each request can use different settings
for await (const message of query({
  prompt: "Review this PR for security issues",
  options: {
    allowedTools: ["Read", "Grep", "Glob", "Task"],
    agents: {
      // Call the factory with your desired configuration
      "security-reviewer": createSecurityAgent("strict"),
    },
  },
})) {
  if ("result" in message) console.log(message.result);
}
```

---

### Configuring Ephemeral Writable Locations with tmpfs for Agent (Docker)

Source: https://platform.claude.com/docs/en/agent-sdk/secure-deployment

This example shows how to configure ephemeral, in-memory writable locations using `tmpfs` mounts for an agent running in a Docker container. This ensures that any files written by the agent are temporary and cleared when the container stops, enhancing security and preventing persistent changes to the host filesystem. It also sets the container to be read-only overall, except for the specified `tmpfs` mounts.

```bash
docker run \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=100m \
  --tmpfs /workspace:rw,noexec,size=500m \
  agent-image
```

---

### Configure Claude Agent SDK for Sandbox and Tool Use (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

This Python snippet illustrates the setup of the Claude Agent SDK, demonstrating how to define a `dummy_hook` for `can_use_tool` to maintain stream activity, a `prompt_stream` for user interaction, and a `main` function to initiate a `query`. It configures `ClaudeAgentOptions` to enable sandbox features, permit unsandboxed commands, and integrate a `PreToolUse` hook with the `dummy_hook`.

```python
async def dummy_hook(input_data, tool_use_id, context):
    return {"continue_": True}


async def prompt_stream():
    yield {
        "type": "user",
        "message": {"role": "user", "content": "Deploy my application"},
    }


async def main():
    async for message in query(
        prompt=prompt_stream(),
        options=ClaudeAgentOptions(
            sandbox={
                "enabled": True,
                "allowUnsandboxedCommands": True,
            },
            permission_mode="default",
            can_use_tool=can_use_tool,
            hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[dummy_hook])]},
        ),
    ):
        print(message)
```

---

### Rewind Files from CLI (Bash)

Source: https://platform.claude.com/docs/en/agent-sdk/file-checkpointing

This command-line example demonstrates how to rewind files using the `claude` CLI tool. It requires a previously captured session ID and checkpoint UUID to restore the files associated with that session to the specified checkpoint.

```bash
claude --resume <session-id> --rewind-files <checkpoint-uuid>
```

---

### Configure Claude Agent SDK hooks with regex matchers (Python, TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/hooks

This snippet demonstrates how to configure `PreToolUse` hooks in the Claude Agent SDK using regex patterns to selectively trigger different hooks based on tool names. It shows examples for matching specific tool names (e.g., 'Write|Edit|Delete'), tools starting with a prefix (e.g., '^mcp\_\_'), and a global matcher for all tools, enabling fine-grained control over hook execution.

```Python
options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            # Match file modification tools
            HookMatcher(matcher="Write|Edit|Delete", hooks=[file_security_hook]),
            # Match all MCP tools
            HookMatcher(matcher="^mcp__", hooks=[mcp_audit_hook]),
            # Match everything (no matcher)
            HookMatcher(hooks=[global_logger]),
        ]
    }
)
```

```TypeScript
const options = {
  hooks: {
    PreToolUse: [
      // Match file modification tools
      { matcher: "Write|Edit|Delete", hooks: [fileSecurityHook] },

      // Match all MCP tools
      { matcher: "^mcp__", hooks: [mcpAuditHook] },

      // Match everything (no matcher)
      { hooks: [globalLogger] }
    ]
  }
};
```

---

### Query Custom Commands with Python SDK

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

Python implementation demonstrating how to invoke custom slash commands through the Claude Agent SDK using async/await patterns. Shows examples for running code review and test commands with configurable max_turns for multi-turn conversations.

```python
import asyncio
from claude_agent_sdk import query


async def main():
    # Run code review
    async for message in query(prompt="/code-review", options={"max_turns": 3}):
        # Process review feedback
        pass

    # Run specific tests
    async for message in query(prompt="/test auth", options={"max_turns": 5}):
        # Handle test results
        pass


asyncio.run(main())
```

---

### Dynamically Change Claude Agent SDK Permission Mode During Session (Python, TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/permissions

This example illustrates how to alter the Claude Agent SDK's permission mode dynamically while a session is active. By calling `set_permission_mode()` (Python) or `setPermissionMode()` (TypeScript) on the query object, the new mode takes immediate effect for all subsequent tool requests. This allows for flexible permission management, such as starting restrictively and then loosening permissions as needed.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    q = query(
        prompt="Help me refactor this code",
        options=ClaudeAgentOptions(
            permission_mode="default",  # Start in default mode
        ),
    )

    # Change mode dynamically mid-session
    await q.set_permission_mode("acceptEdits")

    # Process messages with the new permission mode
    async for message in q:
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

async function main() {
  const q = query({
    prompt: "Help me refactor this code",
    options: {
      permissionMode: "default", // Start in default mode
    },
  });

  // Change mode dynamically mid-session
  await q.setPermissionMode("acceptEdits");

  // Process messages with the new permission mode
  for await (const message of q) {
    if ("result" in message) {
      console.log(message.result);
    }
  }
}

main();
```

---

### Query GitHub MCP Server to List Repository Issues

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

Connect to the GitHub MCP server using a personal access token to list recent issues from a repository. The example demonstrates MCP server initialization verification, tool call logging, and result retrieval using the Claude Agent SDK query interface.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "List the 3 most recent issues in anthropics/claude-code",
  options: {
    mcpServers: {
      github: {
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-github"],
        env: {
          GITHUB_TOKEN: process.env.GITHUB_TOKEN,
        },
      },
    },
    allowedTools: ["mcp__github__list_issues"],
  },
})) {
  // Verify MCP server connected successfully
  if (message.type === "system" && message.subtype === "init") {
    console.log("MCP servers:", message.mcp_servers);
  }

  // Log when Claude calls an MCP tool
  if (message.type === "assistant") {
    for (const block of message.content) {
      if (block.type === "tool_use" && block.name.startsWith("mcp__")) {
        console.log("MCP tool called:", block.name);
      }
    }
  }

  // Print the final result
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}
```

```python
import asyncio
import os
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    AssistantMessage,
)


async def main():
    options = ClaudeAgentOptions(
        mcp_servers={
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": os.environ["GITHUB_TOKEN"]},
            }
        },
        allowed_tools=["mcp__github__list_issues"],
    )

    async for message in query(
        prompt="List the 3 most recent issues in anthropics/claude-code",
        options=options,
    ):
        # Verify MCP server connected successfully
        if isinstance(message, SystemMessage) and message.subtype == "init":
            print("MCP servers:", message.data.get("mcp_servers"))

        # Log when Claude calls an MCP tool
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "name") and block.name.startswith("mcp__"):
                    print("MCP tool called:", block.name)

        # Print the final result
        if isinstance(message, ResultMessage) and message.subtype == "success":
            print(message.result)


asyncio.run(main())
```

---

### Implement Interactive Streaming with Claude Agent SDK Client (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This Python example demonstrates how to establish an interactive, streaming conversation with the Claude Agent SDK. It shows sending initial and follow-up queries and asynchronously processing responses received from the client.

```python
from claude_agent_sdk import ClaudeSDKClient
import asyncio


async def interactive_session():
    async with ClaudeSDKClient() as client:
        # Send initial message
        await client.query("What's the weather like?")

        # Process responses
        async for msg in client.receive_response():
            print(msg)

        # Send follow-up
        await client.query("Tell me more about that")

        # Process follow-up response
        async for msg in client.receive_response():
            print(msg)


asyncio.run(interactive_session())
```

---

### Create an MCP Server with Multiple Tools in Python

Source: https://platform.claude.com/docs/en/agent-sdk/python

Illustrates the creation of an in-process MCP server named 'calculator' using `create_sdk_mcp_server`, registering two distinct tools ('add' and 'multiply') defined with the `@tool` decorator. This example also shows how to integrate the created server into `ClaudeAgentOptions` for use with a Claude agent, specifying allowed tools.

```python
from claude_agent_sdk import tool, create_sdk_mcp_server


@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args):
    return {"content": [{"type": "text", "text": f"Sum: {args['a'] + args['b']}"}]}


@tool("multiply", "Multiply two numbers", {"a": float, "b": float})
async def multiply(args):
    return {"content": [{"type": "text", "text": f"Product: {args['a'] * args['b']}"}]}


calculator = create_sdk_mcp_server(
    name="calculator",
    version="2.0.0",
    tools=[add, multiply]
)

# Use with Claude
options = ClaudeAgentOptions(
    mcp_servers={"calc": calculator},
    allowed_tools=["mcp__calc__add", "mcp__calc__multiply"]
)
```

---

### Load Specific Project Settings in Claude Agent SDK

Source: https://docs.claude.com/en/api/agent-sdk/python

This Python example shows how to configure the Claude Agent SDK to load settings only from the project-specific configuration file (`.claude/settings.json`). By specifying `setting_sources=['project']`, it ignores user and local settings, ensuring that only shared project configurations are applied.

```python
async for message in query(
    prompt="Run CI checks",
    options=ClaudeAgentOptions(
        setting_sources=["project"]  # Only .claude/settings.json
    ),
):
    print(message)
```

---

### Define SetupHookInput Type in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the input type for setup hook events. Extends BaseHookInput with trigger property (init or maintenance). Triggered during agent initialization or maintenance operations.

```typescript
type SetupHookInput = BaseHookInput & {
  hook_event_name: "Setup";
  trigger: "init" | "maintenance";
};
```

---

### Install new Claude Agent SDK package

Source: https://platform.claude.com/docs/en/agent-sdk/migration-guide

Commands to add the new Claude Agent SDK package to your project, applicable for both TypeScript/JavaScript (npm) and Python (pip) environments.

```bash
npm install @anthropic-ai/claude-agent-sdk
```

```bash
pip install claude-agent-sdk
```

---

### Discover Available Skills in Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/skills

This example illustrates how to prompt Claude to list all currently available Skills within an SDK application. By setting `allowed_tools` to only include 'Skill', the agent focuses on skill discovery. Skills are loaded from the filesystem via `setting_sources`.

```python
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Load Skills from filesystem
    allowed_tools=["Skill"],
)

async for message in query(prompt="What Skills are available?", options=options):
    print(message)
```

```typescript
for await (const message of query({
  prompt: "What Skills are available?",
  options: {
    settingSources: ["user", "project"], // Load Skills from filesystem
    allowedTools: ["Skill"],
  },
})) {
  console.log(message);
}
```

---

### Client Method: **init**(options)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Initializes the Claude Agent SDK client with optional configuration settings. This method sets up the client for subsequent interactions with Claude.

````APIDOC
## Client Method: __init__(options)

### Description
Initialize the client with optional configuration. This constructor prepares the client for connecting to Claude.

### Method
__init__

### Parameters
#### Arguments
- **options** (object) - Optional - An object containing configuration options for the client. Specific options are not detailed here but typically include API keys, endpoint URLs, etc.

### Request Example
```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient

async def main():
    # Initialize with default options
    client = ClaudeSDKClient()
    # Or with custom options
    # client = ClaudeSDKClient(api_key="your_api_key", base_url="https://api.example.com")
    await client.disconnect() # Clean up

asyncio.run(main())
````

### Response

#### Return Value

- **None** - The constructor does not return a value; it initializes the client instance.

#### Response Example

```json
null
```

````

--------------------------------

### Connect to Claude Code Docs MCP Server (TypeScript/Python)

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

This example demonstrates how to connect to an HTTP-based Model Context Protocol (MCP) server, specifically the Claude Code documentation server. It uses the `query` function from the SDK to send a prompt and retrieve information, allowing all tools from the server using a wildcard in `allowedTools`. The output is logged to the console upon successful retrieval.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Use the docs MCP server to explain what hooks are in Claude Code",
  options: {
    mcpServers: {
      "claude-code-docs": {
        type: "http",
        url: "https://code.claude.com/docs/mcp"
      }
    },
    allowedTools: ["mcp__claude-code-docs__*"]
  }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}
````

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


async def main():
    options = ClaudeAgentOptions(
        mcp_servers={
            "claude-code-docs": {
                "type": "http",
                "url": "https://code.claude.com/docs/mcp",
            }
        },
        allowed_tools=["mcp__claude-code-docs__*"],
    )

    async for message in query(
        prompt="Use the docs MCP server to explain what hooks are in Claude Code",
        options=options,
    ):
        if isinstance(message, ResultMessage) and message.subtype == "success":
            print(message.result)


asyncio.run(main())
```

---

### Configure Claude Agent SDK for Programmatic-Only Applications

Source: https://docs.claude.com/en/api/agent-sdk/python

This Python example demonstrates configuring the Claude Agent SDK for applications that define all settings programmatically, without relying on filesystem configurations. By omitting `setting_sources` (which defaults to `None`), the SDK ensures no filesystem dependencies, providing isolation and allowing full programmatic control over agents, servers, and tools.

```python
async for message in query(
    prompt="Review this PR",
    options=ClaudeAgentOptions(
        # setting_sources=None is the default, no need to specify
        agents={...},
        mcp_servers={...},
        allowed_tools=["Read", "Grep", "Glob"],
    ),
):
    print(message)
```

---

### Configure Agent SDK Setting Sources in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

These TypeScript examples demonstrate how to explicitly control which filesystem-based settings the Agent SDK loads using the `settingSources` option within a `query` call. They cover scenarios like loading all settings (legacy behavior), loading only specific project settings, ensuring consistent behavior in CI by excluding local settings, and relying solely on programmatic configuration without filesystem dependencies.

```typescript
// Load all settings like SDK v0.0.x did
const result = query({
  prompt: "Analyze this code",
  options: {
    settingSources: ["user", "project", "local"], // Load all settings
  },
});
```

```typescript
// Load only project settings, ignore user and local
const result = query({
  prompt: "Run CI checks",
  options: {
    settingSources: ["project"], // Only .claude/settings.json
  },
});
```

```typescript
// Ensure consistent behavior in CI by excluding local settings
const result = query({
  prompt: "Run tests",
  options: {
    settingSources: ["project"], // Only team-shared settings
    permissionMode: "bypassPermissions",
  },
});
```

```typescript
// Define everything programmatically (default behavior)
// No filesystem dependencies - settingSources defaults to []
const result = query({
  prompt: "Review this PR",
  options: {
    // settingSources: [] is the default, no need to specify
    agents: {
      /* ... */
    },
    mcpServers: {
      /* ... */
    },
    allowedTools: ["Read", "Grep", "Glob"],
  },
});
```

```typescript
// Load project settings to include CLAUDE.md files
const result = query({
  prompt: "Add a new feature following project conventions",
  options: {
    systemPrompt: {
      type: "preset",
      preset: "claude_code", // Required to use CLAUDE.md
    },
    settingSources: ["project"], // Loads CLAUDE.md from project directory
    allowedTools: ["Read", "Write", "Edit"],
  },
});
```

---

### Define a Custom Command with Frontmatter in Markdown

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

This example illustrates how to define a custom command with additional metadata using YAML frontmatter within the Markdown file. The `/security-check` command specifies allowed tools, a description, and a particular model to use for its execution.

```markdown
---
allowed-tools: Read, Grep, Glob
description: Run security vulnerability scan
model: claude-opus-4-6
---

Analyze the codebase for security vulnerabilities including:

- SQL injection risks
- XSS vulnerabilities
- Exposed credentials
- Insecure configurations
```

---

### Create Read-Only Code Analysis Agent with Tool Restrictions

Source: https://platform.claude.com/docs/en/agent-sdk/subagents

Demonstrates how to create a subagent with restricted tool access that can examine code using Read, Grep, and Glob tools but cannot modify files or execute commands. The agent is configured through the ClaudeAgentOptions with an allowed_tools list and agent-specific tools restriction. This example shows how to query the agent asynchronously and handle results.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition


async def main():
    async for message in query(
        prompt="Analyze the architecture of this codebase",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Grep", "Glob", "Task"],
            agents={
                "code-analyzer": AgentDefinition(
                    description="Static code analysis and architecture review",
                    prompt="""You are a code architecture analyst. Analyze code structure,
identify patterns, and suggest improvements without making changes.""",
                    # Read-only tools: no Edit, Write, or Bash access
                    tools=["Read", "Grep", "Glob"],
                )
            },
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Analyze the architecture of this codebase",
  options: {
    allowedTools: ["Read", "Grep", "Glob", "Task"],
    agents: {
      "code-analyzer": {
        description: "Static code analysis and architecture review",
        prompt: `You are a code architecture analyst. Analyze code structure,
identify patterns, and suggest improvements without making changes.`,
        // Read-only tools: no Edit, Write, or Bash access
        tools: ["Read", "Grep", "Glob"],
      },
    },
  },
})) {
  if ("result" in message) console.log(message.result);
}
```

---

### Implement `canUseTool` callback for Claude Agent SDK in Python

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This Python example demonstrates how to implement the `can_use_tool` asynchronous callback function within the Claude Agent SDK. It shows how to display details of a tool request (e.g., Bash command, description, or generic input) to the user, prompt for their approval, and then return either `PermissionResultAllow` to proceed with the tool's execution or `PermissionResultDeny` to block it, providing a custom message to Claude.

```python
import asyncio

from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import (
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)


async def can_use_tool(
    tool_name: str, input_data: dict, context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    # Display the tool request
    print(f"\nTool: {tool_name}")
    if tool_name == "Bash":
        print(f"Command: {input_data.get('command')}")
        if input_data.get("description"):
            print(f"Description: {input_data.get('description')}")
    else:
        print(f"Input: {input_data}")

    # Get user approval
    response = input("Allow this action? (y/n): ")

    # Return allow or deny based on user's response
    if response.lower() == "y":
        # Allow: tool executes with the original (or modified) input
        return PermissionResultAllow(updated_input=input_data)
    else:
        # Deny: tool doesn't execute, Claude sees the message
        return PermissionResultDeny(message="User denied this action")
```

---

### Configure Claude Agent SDK for CI/Testing Environments

Source: https://docs.claude.com/en/api/agent-sdk/python

This Python example illustrates how to configure the Claude Agent SDK for consistent behavior in CI or testing environments. It loads only project-shared settings by setting `setting_sources=['project']` and uses `permission_mode='bypassPermissions'` to ensure tests run without interactive permission prompts.

```python
async for message in query(
    prompt="Run tests",
    options=ClaudeAgentOptions(
        setting_sources=["project"],  # Only team-shared settings
        permission_mode="bypassPermissions",
    ),
):
    print(message)
```

---

### Initialize User Message Stream - Python

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

Async generator that yields the initial user message to Claude. Provides the starting prompt for the agent to begin processing and asking clarifying questions about the mobile app tech stack decision.

```python
async def prompt_stream():
    yield {
        "type": "user",
        "message": {
            "role": "user",
            "content": "Help me decide on the tech stack for a new mobile app",
        },
    }
```

---

### Rewind Files After Stream Completion (Python, TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/file-checkpointing

This example shows how to rewind files to a previously captured checkpoint after the message stream has completed. It involves resuming the session using the `session_id` with an empty prompt to re-establish the connection, and then calling `rewind_files()` with the `checkpoint_id`.

```python
async with ClaudeSDKClient(
    ClaudeAgentOptions(enable_file_checkpointing=True, resume=session_id)
) as client:
    await client.query("")  # Empty prompt to open the connection
    async for message in client.receive_response():
        await client.rewind_files(checkpoint_id)
        break
```

```typescript
const rewindQuery = query({
  prompt: "", // Empty prompt to open the connection
  options: { ...opts, resume: sessionId },
});

for await (const msg of rewindQuery) {
  await rewindQuery.rewindFiles(checkpointId);
  break;
}
```

---

### Track Per-Step Token Usage with Deduplication in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/cost-tracking

This example demonstrates how to accumulate input and output tokens across all steps of an agent's execution. It specifically addresses parallel tool calls by using a Set to deduplicate message IDs, ensuring accurate token counts by only counting each unique message ID once.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

const seenIds = new Set<string>();
let totalInputTokens = 0;
let totalOutputTokens = 0;

for await (const message of query({ prompt: "Summarize this project" })) {
  if (message.type === "assistant") {
    const msgId = message.message.id;

    // Parallel tool calls share the same ID, only count once
    if (!seenIds.has(msgId)) {
      seenIds.add(msgId);
      totalInputTokens += message.message.usage.input_tokens;
      totalOutputTokens += message.message.usage.output_tokens;
    }
  }
}

console.log(`Steps: ${seenIds.size}`);
console.log(`Input tokens: ${totalInputTokens}`);
console.log(`Output tokens: ${totalOutputTokens}`);
```

---

### Configure Agent Skills with SDK - Python

Source: https://platform.claude.com/docs/en/agent-sdk/skills

Initialize the Claude Agent SDK with Skills enabled by configuring settingSources to load Skills from filesystem and adding 'Skill' to allowed_tools. This example demonstrates setting up Skills from both user and project directories with other tools like Read, Write, and Bash.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    options = ClaudeAgentOptions(
        cwd="/path/to/project",  # Project with .claude/skills/
        setting_sources=["user", "project"],  # Load Skills from filesystem
        allowed_tools=["Skill", "Read", "Write", "Bash"],  # Enable Skill tool
    )

    async for message in query(
        prompt="Help me process this PDF document", options=options
    ):
        print(message)


asyncio.run(main())
```

---

### Return User Answers to Claude

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This Python example shows how to construct the `answers` object within the `updated_input` for `PermissionResultAllow`. The `answers` object maps the original question text to the user's selected option labels, handling multi-select questions by joining labels with a comma.

```python
return PermissionResultAllow(
    updated_input={
        "questions": input_data.get("questions", []),
        "answers": {
            "How should I format the output?": "Summary",
            "Which sections should I include?": "Introduction, Conclusion",
        },
    }
```

---

### Connect to External Systems via MCP with Claude Agent SDK (Python/TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/overview

This example illustrates how to integrate external systems using the Model Context Protocol (MCP) in the Claude Agent SDK. It connects to a Playwright MCP server to enable browser automation, allowing the agent to open a webpage and describe its content.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    async for message in query(
        prompt="Open example.com and describe what you see",
        options=ClaudeAgentOptions(
            mcp_servers={
                "playwright": {"command": "npx", "args": ["@playwright/mcp@latest"]}
            }
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Open example.com and describe what you see",
  options: {
    mcpServers: {
      playwright: { command: "npx", args: ["@playwright/mcp@latest"] },
    },
  },
})) {
  if ("result" in message) console.log(message.result);
}
```

---

### SystemPromptPreset Configuration

Source: https://platform.claude.com/docs/en/agent-sdk/python

Configuration for using Claude Code's preset system prompt with optional custom additions. This allows leveraging pre-built system prompts while customizing behavior with additional instructions.

````APIDOC
## SystemPromptPreset Configuration

### Description
Configuration for using Claude Code's preset system prompt with optional custom additions. Enables use of pre-configured system prompts with the ability to append custom instructions.

### Type Definition
```python
class SystemPromptPreset(TypedDict):
    type: Literal["preset"]
    preset: Literal["claude_code"]
    append: NotRequired[str]
````

### Parameters

#### type

- **Type**: `Literal["preset"]`
- **Required**: Yes
- **Description**: Must be `"preset"` to indicate use of a preset system prompt configuration.

#### preset

- **Type**: `Literal["claude_code"]`
- **Required**: Yes
- **Description**: Must be `"claude_code"` to use Claude Code's pre-configured system prompt.

#### append

- **Type**: `string`
- **Required**: No
- **Description**: Optional additional instructions to append to the preset system prompt, allowing customization of the base prompt behavior.

### Request Example

```python
{
    "type": "preset",
    "preset": "claude_code",
    "append": "Always prioritize security and performance optimization."
}
```

````

--------------------------------

### Use ClaudeSDKClient as an Async Context Manager (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This example demonstrates how to use the `ClaudeSDKClient` as an asynchronous context manager (`async with`). This pattern ensures automatic connection and disconnection, simplifying resource management. Within the `async with` block, a query is sent, and messages are received from Claude using `receive_response()`, which yields messages until a `ResultMessage` is encountered.

```python
async with ClaudeSDKClient() as client:
    await client.query("Hello Claude")
    async for message in client.receive_response():
        print(message)
````

---

### Query Custom Commands with TypeScript SDK

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

TypeScript implementation demonstrating how to invoke custom slash commands through the Claude Agent SDK using the query function. Shows examples for running code review and test commands with configurable max turns for multi-turn conversations.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Run code review
for await (const message of query({
  prompt: "/code-review",
  options: { maxTurns: 3 },
})) {
  // Process review feedback
}

// Run specific tests
for await (const message of query({
  prompt: "/test auth",
  options: { maxTurns: 5 },
})) {
  // Handle test results
}
```

---

### Resume Claude Subagent Session with SDK

Source: https://platform.claude.com/docs/en/agent-sdk/subagents

This example demonstrates the full flow for resuming a subagent. It first performs a query to initiate a subagent task, capturing the `session_id` and the subagent's `agentId` from the message stream. Subsequently, it performs a second query, passing the captured `session_id` to the `resume` option and the `agentId` in the prompt, allowing the subagent to continue its work with its previous context.

```typescript
import { query, type SDKMessage } from "@anthropic-ai/claude-agent-sdk";

// Helper to extract agentId from message content
// Stringify to avoid traversing different block types (TextBlock, ToolResultBlock, etc.)
function extractAgentId(message: SDKMessage): string | undefined {
  if (!("message" in message)) return undefined;
  // Stringify the content so we can search it without traversing nested blocks
  const content = JSON.stringify(message.message.content);
  const match = content.match(/agentId:\s*([a-f0-9-]+)/);
  return match?.[1];
}

let agentId: string | undefined;
let sessionId: string | undefined;

// First invocation - use the Explore agent to find API endpoints
for await (const message of query({
  prompt: "Use the Explore agent to find all API endpoints in this codebase",
  options: { allowedTools: ["Read", "Grep", "Glob", "Task"] },
})) {
  // Capture session_id from ResultMessage (needed to resume this session)
  if ("session_id" in message) sessionId = message.session_id;
  // Search message content for the agentId (appears in Task tool results)
  const extractedId = extractAgentId(message);
  if (extractedId) agentId = extractedId;
  // Print the final result
  if ("result" in message) console.log(message.result);
}

// Second invocation - resume and ask follow-up
if (agentId && sessionId) {
  for await (const message of query({
    prompt: `Resume agent ${agentId} and list the top 3 most complex endpoints`,
    options: {
      allowedTools: ["Read", "Grep", "Glob", "Task"],
      resume: sessionId,
    },
  })) {
    if ("result" in message) console.log(message.result);
  }
}
```

```python
import asyncio
import json
import re
from claude_agent_sdk import query, ClaudeAgentOptions


def extract_agent_id(text: str) -> str | None:
    """Extract agentId from Task tool result text."""
    match = re.search(r"agentId:\s*([a-f0-9-]+)", text)
    return match.group(1) if match else None


async def main():
    agent_id = None
    session_id = None

    # First invocation - use the Explore agent to find API endpoints
    async for message in query(
        prompt="Use the Explore agent to find all API endpoints in this codebase",
        options=ClaudeAgentOptions(allowed_tools=["Read", "Grep", "Glob", "Task"]),
    ):
        # Capture session_id from ResultMessage (needed to resume this session)
        if hasattr(message, "session_id"):
            session_id = message.session_id
        # Search message content for the agentId (appears in Task tool results)
        if hasattr(message, "content"):
            # Stringify the content so we can search it without traversing nested blocks
            content_str = json.dumps(message.content, default=str)
            extracted = extract_agent_id(content_str)
            if extracted:
                agent_id = extracted
        # Print the final result
        if hasattr(message, "result"):
            print(message.result)

    # Second invocation - resume and ask follow-up
    if agent_id and session_id:
        async for message in query(
            prompt=f"Resume agent {agent_id} and list the top 3 most complex endpoints",
            options=ClaudeAgentOptions(
                allowed_tools=["Read", "Grep", "Glob", "Task"], resume=session_id
            ),
        ):
            if hasattr(message, "result"):
                print(message.result)


asyncio.run(main())
```

---

### Define ConfigOutput Type - TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the output type for configuration get and set operations indicating success status, operation type, setting name, and both previous and new values. Includes optional error information for failed operations.

```typescript
type ConfigOutput = {
  success: boolean;
  operation?: "get" | "set";
  setting?: string;
  value?: unknown;
  previousValue?: unknown;
  newValue?: unknown;
  error?: string;
};
```

---

### Manage Agent Sessions for Context Persistence with Claude Agent SDK (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/overview

This example shows how to manage sessions in the Claude Agent SDK to maintain context across multiple queries. It captures a session ID from an initial query and then resumes the session for a subsequent query, allowing the agent to remember previous actions and conversation history.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    session_id = None

    # First query: capture the session ID
    async for message in query(
        prompt="Read the authentication module",
        options=ClaudeAgentOptions(allowed_tools=["Read", "Glob"]),
    ):
        if hasattr(message, "subtype") and message.subtype == "init":
            session_id = message.session_id

    # Resume with full context from the first query
    async for message in query(
        prompt="Now find all places that call it",  # "it" = auth module
        options=ClaudeAgentOptions(resume=session_id),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
```

---

### Execute Docker Container Using gVisor Runtime

Source: https://platform.claude.com/docs/en/agent-sdk/secure-deployment

After configuring the Docker daemon, this command shows how to run a container with the gVisor runtime enabled. Using `--runtime=runsc` ensures that gVisor intercepts system calls, providing an additional layer of isolation and reducing the attack surface against the host kernel, especially for untrusted workloads.

```bash
docker run --runtime=runsc agent-image
```

---

### Method: Transport.end_input()

Source: https://docs.claude.com/en/api/agent-sdk/python

Signals the end of the input stream for the transport. For example, this might close the stdin for subprocess-based transports.

````APIDOC
## METHOD Transport.end_input()

### Description
Signals the end of the input stream for the transport. For example, this might close the stdin for subprocess-based transports.

### Method
`async`

### Endpoint
`Transport.end_input`

### Parameters
#### Method Parameters
- No parameters.

### Request Example
```python
# Assuming 'my_transport_instance' is an instance of a class implementing Transport
await my_transport_instance.end_input()
````

### Response

#### Success Response (200)

- Returns `None` upon successfully signaling the end of input.

#### Response Example

```json
{}
```

````

--------------------------------

### Troubleshoot Missing Skills: Configure settingSources in Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/skills

This example highlights a common pitfall where Skills are not loaded because `settingSources` is not configured. It contrasts incorrect usage (missing `settingSources`) with correct usage, emphasizing that `settingSources` is essential for loading Skills from the filesystem in both Python and TypeScript SDKs.

```python
# Wrong - Skills won't be loaded
options = ClaudeAgentOptions(allowed_tools=["Skill"])

# Correct - Skills will be loaded
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Required to load Skills
    allowed_tools=["Skill"],
)
````

```typescript
// Wrong - Skills won't be loaded
const options = {
  allowedTools: ["Skill"],
};

// Correct - Skills will be loaded
const options = {
  settingSources: ["user", "project"], // Required to load Skills
  allowedTools: ["Skill"],
};
```

---

### Define SDKTaskStartedMessage Type for Task Initialization

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines a TypeScript type for task started messages emitted when a background task begins. Includes task identification, optional tool use reference, description, and session tracking.

```typescript
type SDKTaskStartedMessage = {
  type: "system";
  subtype: "task_started";
  task_id: string;
  tool_use_id?: string;
  description: string;
  task_type?: string;
  uuid: UUID;
  session_id: string;
};
```

---

### Access Cache Token Data in Python

Source: https://platform.claude.com/docs/en/agent-sdk/cost-tracking

Retrieve cache token information from the ResultMessage.usage dictionary in Python. Use the get() method with a default value to safely access cache_read_input_tokens and cache_creation_input_tokens keys.

```python
# Access cache tokens from ResultMessage.usage dict
cache_read_tokens = message.usage.get("cache_read_input_tokens", 0)
cache_creation_tokens = message.usage.get("cache_creation_input_tokens", 0)
standard_input_tokens = message.usage.get("input_tokens", 0)
total_cost = message.total_cost_usd
```

---

### Accumulate Total Cost Across Multiple Agent SDK Calls

Source: https://platform.claude.com/docs/en/agent-sdk/cost-tracking

This example demonstrates how to track the cumulative cost across multiple `query()` calls, as the SDK does not provide a session-level total. It iterates through a series of prompts, executes a `query()` for each, and sums the `total_cost_usd` from each result message to provide a running total of expenditure.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Track cumulative cost across multiple query() calls
let totalSpend = 0;

const prompts = [
  "Read the files in src/ and summarize the architecture",
  "List all exported functions in src/auth.ts",
];

for (const prompt of prompts) {
  for await (const message of query({ prompt })) {
    if (message.type === "result") {
      totalSpend += message.total_cost_usd ?? 0;
      console.log(`This call: $${message.total_cost_usd}`);
    }
  }
}

console.log(`Total spend: $${totalSpend.toFixed(4)}`);
```

```python
from claude_agent_sdk import query, ResultMessage
import asyncio


async def main():
    # Track cumulative cost across multiple query() calls
    total_spend = 0.0

    prompts = [
        "Read the files in src/ and summarize the architecture",
        "List all exported functions in src/auth.ts",
    ]

    for prompt in prompts:
        async for message in query(prompt=prompt):
            if isinstance(message, ResultMessage):
                cost = message.total_cost_usd or 0
                total_spend += cost
                print(f"This call: ${cost}")

    print(f"Total spend: ${total_spend:.4f}")


asyncio.run(main())
```

---

### Define SubagentStartHookInput Type in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the input type for subagent start hook events. Extends BaseHookInput with agent_id and agent_type properties. Triggered when a subagent begins execution.

```typescript
type SubagentStartHookInput = BaseHookInput & {
  hook_event_name: "SubagentStart";
  agent_id: string;
  agent_type: string;
};
```

---

### Define CLI Not Found Error (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines `CLINotFoundError`, an exception raised when the Claude Code CLI is either not installed on the system or cannot be located by the SDK. It allows for a custom error message and can optionally specify the `cli_path` that was searched.

```python
class CLINotFoundError(CLIConnectionError):
    def __init__(
        self, message: str = "Claude Code not found", cli_path: str | None = None
    ):
        """
        Args:
            message: Error message (default: "Claude Code not found")
            cli_path: Optional path to the CLI that was not found
        """
```

---

### Configure Agent Skills with SDK - TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/skills

Initialize the Claude Agent SDK with Skills enabled by configuring settingSources to load Skills from filesystem and adding 'Skill' to allowedTools. This example demonstrates setting up Skills from both user and project directories with other tools like Read, Write, and Bash.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Help me process this PDF document",
  options: {
    cwd: "/path/to/project", // Project with .claude/skills/
    settingSources: ["user", "project"], // Load Skills from filesystem
    allowedTools: ["Skill", "Read", "Write", "Bash"], // Enable Skill tool
  },
})) {
  console.log(message);
}
```

---

### Modify User Prompts with Context Hooks in Python

Source: https://docs.claude.com/en/api/agent-sdk/python

Implement a UserPromptSubmit hook to intercept and enhance user prompts with additional context before they reach Claude. This example adds a timestamp to the prompt, demonstrating how hooks can enrich input data. Returns hookSpecificOutput with additionalContext that Claude will receive.

```python
async def user_prompt_modifier(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Add context to user prompts."""
    original_prompt = input_data.get("prompt", "")

    # Add a timestamp as additional context for Claude to see
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": f"[Submitted at {timestamp}] Original prompt: {original_prompt}",
        }
    }


options = ClaudeAgentOptions(
    hooks={
        "UserPromptSubmit": [HookMatcher(hooks=[user_prompt_modifier])],
    },
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Your prompt here")
```

---

### Configure Local Plugin Loading for Development (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/plugins

This configuration snippet shows how to specify a local plugin path within the plugins option of the Claude Agent SDK. This is useful for development and testing, allowing you to load plugins directly from your file system without global installation.

```typescript
plugins: [{ type: "local", path: "./dev-plugins/my-plugin" }];
```

---

### Handle MCP Server Connection and Execution Errors in Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

This example illustrates how to implement error handling for MCP servers within the Claude Agent SDK. It checks the `system` message with `init` subtype to detect server connection failures and monitors for `result` messages with `error_during_execution` subtype for runtime errors during the agent's operation.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Process data",
  options: {
    mcpServers: {
      "data-processor": dataServer,
    },
  },
})) {
  if (message.type === "system" && message.subtype === "init") {
    const failedServers = message.mcp_servers.filter(
      (s) => s.status !== "connected",
    );

    if (failedServers.length > 0) {
      console.warn("Failed to connect:", failedServers);
    }
  }

  if (
    message.type === "result" &&
    message.subtype === "error_during_execution"
  ) {
    console.error("Execution failed");
  }
}
```

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, SystemMessage, ResultMessage


async def main():
    options = ClaudeAgentOptions(mcp_servers={"data-processor": data_server})

    async for message in query(prompt="Process data", options=options):
        if isinstance(message, SystemMessage) and message.subtype == "init":
            failed_servers = [
                s
                for s in message.data.get("mcp_servers", [])
                if s.get("status") != "connected"
            ]

            if failed_servers:
                print(f"Failed to connect: {failed_servers}")

        if (
            isinstance(message, ResultMessage)
            and message.subtype == "error_during_execution"
        ):
            print("Execution failed")


asyncio.run(main())
```

---

### Define SDKHookStartedMessage Type for Hook Execution Start in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the `SDKHookStartedMessage` TypeScript type, emitted when a hook begins executing. It includes identifiers for the `hook_id`, `hook_name`, and `hook_event`, along with the message `uuid` and `session_id`.

```typescript
type SDKHookStartedMessage = {
  type: "system";
  subtype: "hook_started";
  hook_id: string;
  hook_name: string;
  hook_event: string;
  uuid: UUID;
  session_id: string;
};
```

---

### Forward Claude Agent SDK Notifications to Slack

Source: https://platform.claude.com/docs/en/agent-sdk/hooks

This example demonstrates how to use Claude Agent SDK's `Notification` hooks to capture system events (e.g., `permission_prompt`, `idle_prompt`) and forward them to a Slack channel. It requires a pre-configured Slack incoming webhook URL to send messages.

```Python
import asyncio
import json
import urllib.request

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, HookMatcher


def _send_slack_notification(message):
    """Synchronous helper that sends a message to Slack via incoming webhook."""
    data = json.dumps({"text": f"Agent status: {message}"}).encode()
    req = urllib.request.Request(
        "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req)


async def notification_handler(input_data, tool_use_id, context):
    try:
        # Run the blocking HTTP call in a thread to avoid blocking the event loop
        await asyncio.to_thread(_send_slack_notification, input_data.get("message", ""))
    except Exception as e:
        print(f"Failed to send notification: {e}")

    # Return empty object. Notification hooks don't modify agent behavior
    return {}


async def main():
    options = ClaudeAgentOptions(
        hooks={
            # Register the hook for Notification events (no matcher needed)
            "Notification": [HookMatcher(hooks=[notification_handler])],
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Analyze this codebase")
        async for message in client.receive_response():
            print(message)


asyncio.run(main())
```

```TypeScript
import { query, HookCallback, NotificationHookInput } from "@anthropic-ai/claude-agent-sdk";

// Define a hook callback that sends notifications to Slack
const notificationHandler: HookCallback = async (input, toolUseID, { signal }) => {
  // Cast to NotificationHookInput to access the message field
  const notification = input as NotificationHookInput;

  try {
    // POST the notification message to a Slack incoming webhook
    await fetch("https://hooks.slack.com/services/YOUR/WEBHOOK/URL", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: `Agent status: ${notification.message}`
      }),
      // Pass signal so the request cancels if the hook times out
      signal
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      console.log("Notification cancelled");
    } else {
      console.error("Failed to send notification:", error);
    }
  }

  // Return empty object. Notification hooks don't modify agent behavior
  return {};
};

// Register the hook for Notification events (no matcher needed)
for await (const message of query({
  prompt: "Analyze this codebase",
  options: {
    hooks: {
      Notification: [{ hooks: [notificationHandler] }]
    }
  }
})) {
  console.log(message);
}
```

---

### Enable Terminal Command Execution for Claude Agent (Python, TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/quickstart

This snippet illustrates how to grant a Claude agent the ability to execute terminal commands by adding 'Bash' to its `allowed_tools` (Python) or `allowedTools` (TypeScript). The `permission_mode` is set to 'acceptEdits' for streamlined operation, allowing the agent to run commands without interactive prompts.

```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Edit", "Glob", "Bash"], permission_mode="acceptEdits"
)
```

```typescript
const _ = {
  options: {
    allowedTools: ["Read", "Edit", "Glob", "Bash"],
    permissionMode: "acceptEdits",
  },
};
```

---

### Invoke Custom Command with Arguments in Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

This example illustrates how to pass arguments to a custom command (e.g., `/fix-issue 123 high`) when querying the Claude Agent SDK. The command then processes these arguments using its defined placeholders, allowing for dynamic behavior based on user input.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Pass arguments to custom command
for await (const message of query({
  prompt: "/fix-issue 123 high",
  options: { maxTurns: 5 },
})) {
  // Command will process with $1="123" and $2="high"
  if (message.type === "result") {
    console.log("Issue fixed:", message.result);
  }
}
```

```python
import asyncio
from claude_agent_sdk import query


async def main():
    # Pass arguments to custom command
    async for message in query(prompt="/fix-issue 123 high", options={"max_turns": 5}):
        # Command will process with $1="123" and $2="high"
        if message.type == "result":
            print("Issue fixed:", message.result)


asyncio.run(main())
```

---

### Custom System Prompt with Query - TypeScript and Python

Source: https://platform.claude.com/docs/en/agent-sdk/modifying-system-prompts

Demonstrates how to provide a custom system prompt string to the query function to replace default instructions. The example creates a Python coding specialist prompt with specific guidelines for code quality, type hints, and documentation. This approach provides complete control over Claude's behavior but requires manually including any needed tool instructions.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

const customPrompt = `You are a Python coding specialist.
Follow these guidelines:
- Write clean, well-documented code
- Use type hints for all functions
- Include comprehensive docstrings
- Prefer functional programming patterns when appropriate
- Always explain your code choices`;

const messages = [];

for await (const message of query({
  prompt: "Create a data processing pipeline",
  options: {
    systemPrompt: customPrompt,
  },
})) {
  messages.push(message);
  if (message.type === "assistant") {
    console.log(message.message.content);
  }
}
```

```python
from claude_agent_sdk import query, ClaudeAgentOptions

custom_prompt = """You are a Python coding specialist.
Follow these guidelines:
- Write clean, well-documented code
- Use type hints for all functions
- Include comprehensive docstrings
- Prefer functional programming patterns when appropriate
- Always explain your code choices"""

messages = []

async for message in query(
    prompt="Create a data processing pipeline",
    options=ClaudeAgentOptions(system_prompt=custom_prompt),
):
    messages.append(message)
    if message.type == "assistant":
        print(message.message.content)
```

---

### Example Claude Agent Output Answer Structure (JSON)

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This JSON snippet demonstrates the expected format for the `answers` object within a Claude agent's response. It shows how to map the full question text to the selected label(s), with multi-select answers joined by a comma and space. This structure allows the agent to process and utilize user selections effectively.

```json
{
  "questions": [
    // ...
  ],
  "answers": {
    "How should I format the output?": "Summary",
    "Which sections should I include?": "Introduction, Conclusion"
  }
}
```

---

### Define SessionStartHookInput Type in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the input type for session start hook events. Extends BaseHookInput with source (startup, resume, clear, compact), optional agent_type, and optional model properties. Triggered when a new session begins.

```typescript
type SessionStartHookInput = BaseHookInput & {
  hook_event_name: "SessionStart";
  source: "startup" | "resume" | "clear" | "compact";
  agent_type?: string;
  model?: string;
};
```

---

### Define Subagent Start Hook Input Data Structure (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This Python class outlines the input data structure for 'SubagentStart' hook events. It includes the hook event name, a unique identifier for the subagent, and the type of the subagent. This structure is essential for hooks that need to react to or manage the initiation of a subagent.

```python
class SubagentStartHookInput(BaseHookInput):
    hook_event_name: Literal["SubagentStart"]
    agent_id: str
    agent_type: str
```

---

### Check Structured Output Success Status - Python

Source: https://platform.claude.com/docs/en/agent-sdk/structured-outputs

Demonstrates how to check the subtype field in result messages to determine if structured output was generated successfully or if a validation error occurred. Handles both success and error_max_structured_output_retries subtypes with appropriate fallback logic.

```python
async for message in query(
    prompt="Extract contact info from the document",
    options=ClaudeAgentOptions(
        output_format={"type": "json_schema", "schema": contact_schema}
    ),
):
    if isinstance(message, ResultMessage):
        if message.subtype == "success" and message.structured_output:
            # Use the validated output
            print(message.structured_output)
        elif message.subtype == "error_max_structured_output_retries":
            # Handle the failure
            print("Could not produce valid output")
```

---

### Define JSON Schema and Query Agent with Structured Output

Source: https://platform.claude.com/docs/en/agent-sdk/structured-outputs

Define a JSON Schema describing the desired output structure, then pass it to the query function via the outputFormat option. The agent researches the topic and returns validated structured data matching the schema in the structured_output field.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Define the shape of data you want back
const schema = {
  type: "object",
  properties: {
    company_name: { type: "string" },
    founded_year: { type: "number" },
    headquarters: { type: "string" },
  },
  required: ["company_name"],
};

for await (const message of query({
  prompt: "Research Anthropic and provide key company information",
  options: {
    outputFormat: {
      type: "json_schema",
      schema: schema,
    },
  },
})) {
  // The result message contains structured_output with validated data
  if (message.type === "result" && message.structured_output) {
    console.log(message.structured_output);
    // { company_name: "Anthropic", founded_year: 2021, headquarters: "San Francisco, CA" }
  }
}
```

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

# Define the shape of data you want back
schema = {
    "type": "object",
    "properties": {
        "company_name": {"type": "string"},
        "founded_year": {"type": "number"},
        "headquarters": {"type": "string"},
    },
    "required": ["company_name"],
}


async def main():
    async for message in query(
        prompt="Research Anthropic and provide key company information",
        options=ClaudeAgentOptions(
            output_format={"type": "json_schema", "schema": schema}
        ),
    ):
        # The result message contains structured_output with validated data
        if isinstance(message, ResultMessage) and message.structured_output:
            print(message.structured_output)
            # {'company_name': 'Anthropic', 'founded_year': 2021, 'headquarters': 'San Francisco, CA'}


asyncio.run(main())
```

---

### Configure Agent Hooks with ClaudeAgentOptions - Python

Source: https://platform.claude.com/docs/en/agent-sdk/hooks

Sets up hooks in Python using ClaudeAgentOptions with a PreToolUse hook matcher for Bash commands. The hooks are passed to ClaudeSDKClient and executed asynchronously when the matched event occurs. This example demonstrates filtering callbacks by tool name using the matcher pattern.

```python
options = ClaudeAgentOptions(
    hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[my_callback])]}
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Your prompt")
    async for message in client.receive_response():
        print(message)
```

---

### Check Structured Output Success Status - TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/structured-outputs

Demonstrates how to check the subtype field in result messages to determine if structured output was generated successfully or if a validation error occurred. Handles both success and error_max_structured_output_retries subtypes with appropriate fallback logic.

```typescript
for await (const msg of query({
  prompt: "Extract contact info from the document",
  options: {
    outputFormat: {
      type: "json_schema",
      schema: contactSchema,
    },
  },
})) {
  if (msg.type === "result") {
    if (msg.subtype === "success" && msg.structured_output) {
      // Use the validated output
      console.log(msg.structured_output);
    } else if (msg.subtype === "error_max_structured_output_retries") {
      // Handle the failure - retry with simpler prompt, fall back to unstructured, etc.
      console.error("Could not produce valid output");
    }
  }
}
```

---

### Returning Updated Input in PreToolUse Hook (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/hooks

This TypeScript example demonstrates the correct structure for returning an `updatedInput` within a `PreToolUse` hook. It shows that `updatedInput` must be nested inside `hookSpecificOutput` and requires `permissionDecision: 'allow'` and `hookEventName` for the modification to be applied successfully.

```typescript
return {
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "allow",
    updatedInput: { command: "new command" },
  },
};
```

---

### Load Settings from Filesystem Sources - Python

Source: https://platform.claude.com/docs/en/agent-sdk/migration-guide

Demonstrates how to explicitly load settings from filesystem sources in Python after the v0.1.0 migration. Previously all settings were loaded automatically; now you must specify which sources to load using ClaudeAgentOptions. Supports selective loading of user, project, and local settings.

```python
# BEFORE (v0.0.x) - Loaded all settings automatically
async for message in query(prompt="Hello"):
    print(message)
# Would read from:
# - ~/.claude/settings.json (user)
# - .claude/settings.json (project)
# - .claude/settings.local.json (local)
# - CLAUDE.md files
# - Custom slash commands

# AFTER (v0.1.0) - No settings loaded by default
# To get the old behavior:
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Hello",
    options=ClaudeAgentOptions(setting_sources=["user", "project", "local"]),
):
    print(message)

# Or load only specific sources:
async for message in query(
    prompt="Hello",
    options=ClaudeAgentOptions(
        setting_sources=["project"]  # Only project settings
    ),
):
    print(message)
```

---

### Custom Tool Permission Handler with Sandbox Bypass - Python

Source: https://platform.claude.com/docs/en/agent-sdk/python

Implements a custom permission handler that checks if the model is requesting unsandboxed command execution. This example demonstrates how to intercept `dangerouslyDisableSandbox` requests and apply custom authorization logic before allowing commands to run outside the sandbox.

```python
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)


async def can_use_tool(
    tool: str, input: dict, context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    # Check if the model is requesting to bypass the sandbox
    if tool == "Bash" and input.get("dangerouslyDisableSandbox"):
        # The model is requesting to run this command outside the sandbox
        print(f"Unsandboxed command requested: {input.get('command')}")

        if is_command_authorized(input.get("command")):
            return PermissionResultAllow()
        return PermissionResultDeny(
            message="Command not authorized for unsandboxed execution"
        )
    return PermissionResultAllow()
```

---

### Create Custom MCP Server with Tool Definition

Source: https://platform.claude.com/docs/en/agent-sdk/custom-tools

Define a type-safe custom tool using createSdkMcpServer and tool helper functions. This example creates a weather tool that fetches temperature data from an API using latitude and longitude coordinates. The tool uses Zod for schema validation and returns formatted temperature data.

```typescript
import {
  query,
  tool,
  createSdkMcpServer,
} from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";

// Create an SDK MCP server with custom tools
const customServer = createSdkMcpServer({
  name: "my-custom-tools",
  version: "1.0.0",
  tools: [
    tool(
      "get_weather",
      "Get current temperature for a location using coordinates",
      {
        latitude: z.number().describe("Latitude coordinate"),
        longitude: z.number().describe("Longitude coordinate"),
      },
      async (args) => {
        const response = await fetch(
          `https://api.open-meteo.com/v1/forecast?latitude=${args.latitude}&longitude=${args.longitude}&current=temperature_2m&temperature_unit=fahrenheit`,
        );
        const data = await response.json();

        return {
          content: [
            {
              type: "text",
              text: `Temperature: ${data.current.temperature_2m}°F`,
            },
          ],
        };
      },
    ),
  ],
});
```

```python
from claude_agent_sdk import (
    tool,
    create_sdk_mcp_server,
    ClaudeSDKClient,
    ClaudeAgentOptions,
)
from typing import Any
import aiohttp


# Define a custom tool using the @tool decorator
@tool(
    "get_weather",
    "Get current temperature for a location using coordinates",
    {"latitude": float, "longitude": float},
)
async def get_weather(args: dict[str, Any]) -> dict[str, Any]:
    # Call weather API
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={args['latitude']}&longitude={args['longitude']}&current=temperature_2m&temperature_unit=fahrenheit"
        ) as response:
            data = await response.json()

    return {
        "content": [
            {
                "type": "text",
                "text": f"Temperature: {data['current']['temperature_2m']}°F",
            }
        ]
    }


# Create an SDK MCP server with the custom tool
custom_server = create_sdk_mcp_server(
    name="my-custom-tools",
    version="1.0.0",
    tools=[get_weather],  # Pass the decorated function
)
```

---

### Tool Loop Implementation - Client SDK vs Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/overview

Compares manual tool loop implementation using the Anthropic Client SDK with the automatic tool handling provided by the Agent SDK. The Client SDK requires explicit tool execution logic, while the Agent SDK handles tool invocation autonomously.

```python
# Client SDK: You implement the tool loop
response = client.messages.create(...)
while response.stop_reason == "tool_use":
    result = your_tool_executor(response.tool_use)
    response = client.messages.create(tool_result=result, **params)

# Agent SDK: Claude handles tools autonomously
async for message in query(prompt="Fix the bug in auth.py"):
    print(message)
```

```typescript
// Client SDK: You implement the tool loop
let response = await client.messages.create({ ...params });
while (response.stop_reason === "tool_use") {
  const result = yourToolExecutor(response.tool_use);
  response = await client.messages.create({ tool_result: result, ...params });
}

// Agent SDK: Claude handles tools autonomously
for await (const message of query({ prompt: "Fix the bug in auth.py" })) {
  console.log(message);
}
```

---

### Persist and Resume Claude Agent SDK Sessions

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Illustrates how to save a session's context and resume it later using its ID, enabling long-running workflows or conversation persistence across application restarts. Examples are provided for both the V2 API, utilizing `unstable_v2_resumeSession`, and the V1 API, which uses the `resume` option in the `query` function.

```typescript
import {
  unstable_v2_createSession,
  unstable_v2_resumeSession,
  type SDKMessage,
} from "@anthropic-ai/claude-agent-sdk";

// Helper to extract text from assistant messages
function getAssistantText(msg: SDKMessage): string | null {
  if (msg.type !== "assistant") return null;
  return msg.message.content
    .filter((block) => block.type === "text")
    .map((block) => block.text)
    .join("");
}

// Create initial session and have a conversation
const session = unstable_v2_createSession({
  model: "claude-opus-4-6",
});

await session.send("Remember this number: 42");

// Get the session ID from any received message
let sessionId: string | undefined;
for await (const msg of session.stream()) {
  sessionId = msg.session_id;
  const text = getAssistantText(msg);
  if (text) console.log("Initial response:", text);
}

console.log("Session ID:", sessionId);
session.close();

// Later: resume the session using the stored ID
await using resumedSession = unstable_v2_resumeSession(sessionId!, {
  model: "claude-opus-4-6",
});

await resumedSession.send("What number did I ask you to remember?");
for await (const msg of resumedSession.stream()) {
  const text = getAssistantText(msg);
  if (text) console.log("Resumed response:", text);
}
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Create initial session
const initialQuery = query({
  prompt: "Remember this number: 42",
  options: { model: "claude-opus-4-6" },
});

// Get session ID from any message
let sessionId: string | undefined;
for await (const msg of initialQuery) {
  sessionId = msg.session_id;
  if (msg.type === "assistant") {
    const text = msg.message.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("");
    console.log("Initial response:", text);
  }
}

console.log("Session ID:", sessionId);

// Later: resume the session
const resumedQuery = query({
  prompt: "What number did I ask you to remember?",
  options: {
    model: "claude-opus-4-6",
    resume: sessionId,
  },
});

for await (const msg of resumedQuery) {
  if (msg.type === "assistant") {
    const text = msg.message.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("");
    console.log("Resumed response:", text);
  }
}
```

---

### Enable and Process Streaming Responses with Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/streaming-output

This example demonstrates how to configure the Claude Agent SDK to receive partial message streams. It shows how to iterate through `StreamEvent` messages, extract `content_block_delta` events, and print `text_delta` chunks as they arrive, providing real-time output from the agent. This requires setting `include_partial_messages` to `true` in the query options.

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import StreamEvent
import asyncio


async def stream_response():
    options = ClaudeAgentOptions(
        include_partial_messages=True,
        allowed_tools=["Bash", "Read"],
    )

    async for message in query(prompt="List the files in my project", options=options):
        if isinstance(message, StreamEvent):
            event = message.event
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    print(delta.get("text", ""), end="", flush=True)


asyncio.run(stream_response())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "List the files in my project",
  options: {
    includePartialMessages: true,
    allowedTools: ["Bash", "Read"],
  },
})) {
  if (message.type === "stream_event") {
    const event = message.event;
    if (event.type === "content_block_delta") {
      if (event.delta.type === "text_delta") {
        process.stdout.write(event.delta.text);
      }
    }
  }
}
```

---

### Build Continuous Conversation Interface with ClaudeSDKClient - Python

Source: https://docs.claude.com/en/api/agent-sdk/python

Implements a stateful conversation session that maintains context across multiple turns with Claude. Supports commands for interrupting tasks, starting new sessions, and exiting. Uses async/await for non-blocking communication and processes streaming responses with message type checking.

```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)
import asyncio


class ConversationSession:
    """Maintains a single conversation session with Claude."""

    def __init__(self, options: ClaudeAgentOptions | None = None):
        self.client = ClaudeSDKClient(options)
        self.turn_count = 0

    async def start(self):
        await self.client.connect()
        print("Starting conversation session. Claude will remember context.")
        print(
            "Commands: 'exit' to quit, 'interrupt' to stop current task, 'new' for new session"
        )

        while True:
            user_input = input(f"\n[Turn {self.turn_count + 1}] You: ")

            if user_input.lower() == "exit":
                break
            elif user_input.lower() == "interrupt":
                await self.client.interrupt()
                print("Task interrupted!")
                continue
            elif user_input.lower() == "new":
                # Disconnect and reconnect for a fresh session
                await self.client.disconnect()
                await self.client.connect()
                self.turn_count = 0
                print("Started new conversation session (previous context cleared)")
                continue

            # Send message - the session retains all previous messages
            await self.client.query(user_input)
            self.turn_count += 1

            # Process response
            print(f"[Turn {self.turn_count}] Claude: ", end="")
            async for message in self.client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end="")
            print()  # New line after response

        await self.client.disconnect()
        print(f"Conversation ended after {self.turn_count} turns.")


async def main():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"], permission_mode="acceptEdits"
    )
    session = ConversationSession(options)
    await session.start()


asyncio.run(main())
```

---

### Implement Custom Authorization for Unsandboxed Commands (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

This example demonstrates how to enable and handle requests for unsandboxed command execution using the `canUseTool` handler in the Claude Agent SDK. It shows how to audit, allowlist, or deny commands where the model sets `dangerouslyDisableSandbox: true`, emphasizing the need for careful validation due to full system access.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Deploy my application",
  options: {
    sandbox: {
      enabled: true,
      allowUnsandboxedCommands: true, // Model can request unsandboxed execution
    },
    permissionMode: "default",
    canUseTool: async (tool, input) => {
      // Check if the model is requesting to bypass the sandbox
      if (tool === "Bash" && input.dangerouslyDisableSandbox) {
        // The model is requesting to run this command outside the sandbox
        console.log(`Unsandboxed command requested: ${input.command}`);

        if (isCommandAuthorized(input.command)) {
          return { behavior: "allow" as const, updatedInput: input };
        }
        return {
          behavior: "deny" as const,
          message: "Command not authorized for unsandboxed execution",
        };
      }
      return { behavior: "allow" as const, updatedInput: input };
    },
  },
})) {
  if ("result" in message) console.log(message.result);
}
```

---

### Implement Continuous Conversation with ClaudeSDKClient (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

This Python code demonstrates how to build a continuous conversation interface using `ClaudeSDKClient`. The `ConversationSession` class manages the connection, sends user queries, and processes Claude's responses, maintaining context across turns. It includes commands for exiting, interrupting tasks, and starting a new session.

```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)
import asyncio


class ConversationSession:
    """Maintains a single conversation session with Claude."""

    def __init__(self, options: ClaudeAgentOptions | None = None):
        self.client = ClaudeSDKClient(options)
        self.turn_count = 0

    async def start(self):
        await self.client.connect()
        print("Starting conversation session. Claude will remember context.")
        print(
            "Commands: 'exit' to quit, 'interrupt' to stop current task, 'new' for new session"
        )

        while True:
            user_input = input(f"\n[Turn {self.turn_count + 1}] You: ")

            if user_input.lower() == "exit":
                break
            elif user_input.lower() == "interrupt":
                await self.client.interrupt()
                print("Task interrupted!")
                continue
            elif user_input.lower() == "new":
                # Disconnect and reconnect for a fresh session
                await self.client.disconnect()
                await self.client.connect()
                self.turn_count = 0
                print("Started new conversation session (previous context cleared)")
                continue

            # Send message - the session retains all previous messages
            await self.client.query(user_input)
            self.turn_count += 1

            # Process response
            print(f"[Turn {self.turn_count}] Claude: ", end="")
            async for message in self.client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end="")
            print()  # New line after response

        await self.client.disconnect()
        print(f"Conversation ended after {self.turn_count} turns.")


async def main():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"], permission_mode="acceptEdits"
    )
    session = ConversationSession(options)
    await session.start()


# Example conversation:
# Turn 1 - You: "Create a file called hello.py"
# Turn 1 - Claude: "I'll create a hello.py file for you..."
# Turn 2 - You: "What's in that file?"
# Turn 2 - Claude: "The hello.py file I just created contains..." (remembers!)
# Turn 3 - You: "Add a main function to it"
# Turn 3 - Claude: "I'll add a main function to hello.py..." (knows which file!)

asyncio.run(main())
```

---

### Register PreToolUse Hook with Matcher in Python

Source: https://platform.claude.com/docs/en/agent-sdk/hooks

Demonstrates how to register a PreToolUse hook with a matcher pattern to intercept file-writing tool calls. The hook checks if the target file is a .env file and returns a deny permission decision to block the operation. This example shows the basic structure of importing required modules and setting up hook callbacks.

```python
import asyncio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
)
```

---

### Define Claude Agent SDK Response Behavior in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This TypeScript snippet demonstrates how to construct the return object for a Claude agent. It specifies the agent's `behavior` as "allow" and provides `updatedInput` containing the original questions and pre-defined answers. This structure is used to guide the agent's subsequent actions based on user input or programmatic selections.

```typescript
return {
  behavior: "allow",
  updatedInput: {
    questions: input.questions,
    answers: {
      "How should I format the output?": "Summary",
      "Which sections should I include?": "Introduction, Conclusion",
    },
  },
};
```

---

### Agent SDK Session Configuration Parameters

Source: https://platform.claude.com/docs/en/agent-sdk/python

Reference documentation for all available configuration parameters when initializing an Agent SDK session. These parameters control budget limits, tool permissions, model selection, file handling, and CLI behavior.

````APIDOC
## Agent SDK Configuration Parameters

### Overview
Configuration parameters for initializing and managing Agent SDK sessions with Claude models.

### Parameters

#### Budget & Resource Management
- **max_budget_usd** (float | None) - Optional - Maximum budget in USD for the session. Default: `None`

#### Tool Management
- **disallowed_tools** (list[str]) - Optional - Tools to always deny. Deny rules are checked first and override `allowed_tools` and `permission_mode` (including `bypassPermissions`). Default: `[]`
- **permission_prompt_tool_name** (str | None) - Optional - MCP tool name for permission prompts. Default: `None`

#### File Handling
- **enable_file_checkpointing** (bool) - Optional - Enable file change tracking for rewinding. See File checkpointing documentation for details. Default: `False`
- **cwd** (str | Path | None) - Optional - Current working directory. Default: `None`
- **add_dirs** (list[str | Path]) - Optional - Additional directories Claude can access. Default: `[]`

#### Model Configuration
- **model** (str | None) - Optional - Claude model to use. Default: `None`
- **fallback_model** (str | None) - Optional - Fallback model to use if the primary model fails. Default: `None`
- **betas** (list[SdkBeta]) - Optional - Beta features to enable. See SdkBeta documentation for available options. Default: `[]`
- **output_format** (dict[str, Any] | None) - Optional - Output format for structured responses (e.g., `{"type": "json_schema", "schema": {...}}`). See Structured outputs documentation for details. Default: `None`

#### CLI Configuration
- **cli_path** (str | Path | None) - Optional - Custom path to the Claude Code CLI executable. Default: `None`
- **settings** (str | None) - Optional - Path to settings file. Default: `None`
- **env** (dict[str, str]) - Optional - Environment variables. Default: `{}`
- **extra_args** (dict[str, str | None]) - Optional - Additional CLI arguments to pass directly to the CLI. Default: `{}`
- **max_buffer_size** (int | None) - Optional - Maximum bytes when buffering CLI stdout. Default: `None`

#### Output & Debugging
- **stderr** (Callable[[str], None] | None) - Optional - Callback function for stderr output from CLI. Default: `None`
- **debug_stderr** (Any) - Deprecated - File-like object for debug output. Use `stderr` callback instead. Default: `sys.stderr`

### Configuration Example
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "fallback_model": "claude-3-opus-20250219",
  "max_budget_usd": 10.0,
  "disallowed_tools": ["dangerous_tool"],
  "enable_file_checkpointing": true,
  "betas": ["beta_feature_1"],
  "output_format": {
    "type": "json_schema",
    "schema": {}
  },
  "cwd": "/home/user/project",
  "add_dirs": ["/home/user/data"],
  "env": {
    "API_KEY": "value"
  },
  "extra_args": {
    "arg_name": "arg_value"
  }
}
````

````

--------------------------------

### createSdkMcpServer()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Creates an MCP server instance that runs in the same process as your application.

```APIDOC
## Function createSdkMcpServer()

### Description
Creates an MCP server instance that runs in the same process as your application.

### Method
Function

### Endpoint
createSdkMcpServer()

### Parameters
#### Path Parameters
(None)

#### Query Parameters
(None)

#### Request Body
- **options.name** (string) - Required - The name of the MCP server
- **options.version** (string) - Optional - Optional version string
- **options.tools** (Array<SdkMcpToolDefinition>) - Optional - Array of tool definitions created with `tool()`

### Request Example
```typescript
import { createSdkMcpServer, tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";

const myTool = tool(
  "echo",
  "Echoes the input back",
  z.object({ message: z.string() }),
  async (args) => ({ type: "success", result: args.message })
);

const serverConfig = createSdkMcpServer({
  name: "MyAgentServer",
  version: "1.0.0",
  tools: [myTool]
});

// serverConfig can now be used to start the server
````

### Response

#### Success Response (Returns McpSdkServerConfigWithInstance)

- **McpSdkServerConfigWithInstance** (object) - An MCP server configuration object with an instance.

#### Response Example

```json
{
  "name": "MyAgentServer",
  "version": "1.0.0",
  "tools": [
    {
      "name": "echo",
      "description": "Echoes the input back",
      "input_schema": {
        "type": "object",
        "properties": {
          "message": {
            "type": "string"
          }
        },
        "required": ["message"]
      }
    }
  ]
}
```

````

--------------------------------

### Define type-safe schema with Pydantic (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/structured-outputs

Creates Pydantic models for a feature implementation plan with nested Step model, converts to JSON Schema, and uses it with the Claude Agent SDK query function. Demonstrates async iteration over query results and validation using model_validate() with full type hints.

```python
import asyncio
from pydantic import BaseModel
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


class Step(BaseModel):
    step_number: int
    description: str
    estimated_complexity: str  # 'low', 'medium', 'high'


class FeaturePlan(BaseModel):
    feature_name: str
    summary: str
    steps: list[Step]
    risks: list[str]


async def main():
    async for message in query(
        prompt="Plan how to add dark mode support to a React app. Break it into implementation steps.",
        options=ClaudeAgentOptions(
            output_format={
                "type": "json_schema",
                "schema": FeaturePlan.model_json_schema(),
            }
        ),
    ):
        if isinstance(message, ResultMessage) and message.structured_output:
            # Validate and get fully typed result
            plan = FeaturePlan.model_validate(message.structured_output)
            print(f"Feature: {plan.feature_name}")
            print(f"Summary: {plan.summary}")
            for step in plan.steps:
                print(
                    f"{step.step_number}. [{step.estimated_complexity}] {step.description}"
                )


asyncio.run(main())
````

---

### Handle Claude Agent SDK Exceptions in Python

Source: https://docs.claude.com/en/api/agent-sdk/python

Implement error handling for common Claude Agent SDK exceptions including CLINotFoundError (CLI not installed), ProcessError (process execution failure), and CLIJSONDecodeError (response parsing failure). Each exception provides specific information about the failure for appropriate user feedback or recovery actions.

```python
from claude_agent_sdk import query, CLINotFoundError, ProcessError, CLIJSONDecodeError

try:
    async for message in query(prompt="Hello"):
        print(message)
except CLINotFoundError:
    print(
        "Claude Code CLI not found. Try reinstalling: pip install --force-reinstall claude-agent-sdk"
    )
except ProcessError as e:
    print(f"Process failed with exit code: {e.exit_code}")
except CLIJSONDecodeError as e:
    print(f"Failed to parse response: {e}")
```

---

### Discover Available MCP Tools in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

Query the system init message to inspect available MCP tools from configured servers. This approach allows runtime discovery of tool capabilities without manual documentation review.

```typescript
for await (const message of query({ prompt: "...", options })) {
  if (message.type === "system" && message.subtype === "init") {
    console.log("Available MCP tools:", message.mcp_servers);
  }
}
```

---

### Python Claude Agent SDK: Handling `can_use_tool` with a Dummy Hook

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This Python snippet demonstrates how to use a `dummy_hook` with the `PreToolUse` hook to ensure the stream remains open for the `can_use_tool` callback in the Claude Agent SDK. It sets up an asynchronous query to the agent, printing results as they arrive.

```python
async def dummy_hook(input_data, tool_use_id, context):
    return {"continue_": True}


async def main():
    async for message in query(
        prompt=prompt_stream(),
        options=ClaudeAgentOptions(
            can_use_tool=can_use_tool,
            hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[dummy_hook])]}
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
```

---

### Implement Claude Agent SDK Hooks for Behavior Modification (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

This snippet demonstrates how to use `PreToolUse`, `PostToolUse`, and `UserPromptSubmit` hooks to modify or monitor agent behavior. It includes examples for logging tool usage, blocking dangerous commands, and adding contextual information to user prompts before they are processed by the agent. Hooks are registered via `ClaudeAgentOptions`.

```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    HookContext,
)
import asyncio
from typing import Any


async def pre_tool_logger(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Log all tool usage before execution."""
    tool_name = input_data.get("tool_name", "unknown")
    print(f"[PRE-TOOL] About to use: {tool_name}")

    # You can modify or block the tool execution here
    if tool_name == "Bash" and "rm -rf" in str(input_data.get("tool_input", {})):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Dangerous command blocked",
            }
        }
    return {}


async def post_tool_logger(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Log results after tool execution."""
    tool_name = input_data.get("tool_name", "unknown")
    print(f"[POST-TOOL] Completed: {tool_name}")
    return {}


async def user_prompt_modifier(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Add context to user prompts."""
    original_prompt = input_data.get("prompt", "")

    # Add a timestamp as additional context for Claude to see
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": f"[Submitted at {timestamp}] Original prompt: {original_prompt}",
        }
    }


async def main():
    options = ClaudeAgentOptions(
        hooks={
            "PreToolUse": [
                HookMatcher(hooks=[pre_tool_logger]),
                HookMatcher(matcher="Bash", hooks=[pre_tool_logger]),
            ],
            "PostToolUse": [HookMatcher(hooks=[post_tool_logger])],
            "UserPromptSubmit": [HookMatcher(hooks=[user_prompt_modifier])],
        },
        allowed_tools=["Read", "Write", "Bash"],
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("List files in current directory")

        async for message in client.receive_response():
            # Hooks will automatically log tool usage
            pass


asyncio.run(main())
```

---

### Basic Tool Permission Control in Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This snippet demonstrates the fundamental ways to either allow or deny a tool's execution within the Claude Agent SDK, providing a simple message for denial. It shows the basic return structures for both Python and TypeScript.

```python
return PermissionResultDeny(message="User rejected this action")
```

```typescript
// Allow the tool to execute
return { behavior: "allow", updatedInput: input };

// Block the tool
return { behavior: "deny", message: "User rejected this action" };
```

---

### Define McpServerConfig Union Type for Claude Agent SDK (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This union type aggregates all possible MCP server configurations within the SDK. It allows for flexible server setup by combining standard I/O, SSE, HTTP, and SDK-specific server configurations. This provides a unified interface for various server types.

```python
McpServerConfig = (
    McpStdioServerConfig | McpSSEServerConfig | McpHttpServerConfig | McpSdkServerConfig
)
```

---

### Track Streaming Tool Calls and Accumulate Input (Python, TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/streaming-output

This snippet demonstrates how to track streaming tool calls from the Claude Agent SDK. It shows how to use `content_block_start` to detect a new tool call, `content_block_delta` with `input_json_delta` to accumulate the tool's JSON input incrementally, and `content_block_stop` to signal the completion of a tool call. The example prints the tool name and its accumulated input.

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import StreamEvent
import asyncio


async def stream_tool_calls():
    options = ClaudeAgentOptions(
        include_partial_messages=True,
        allowed_tools=["Read", "Bash"],
    )

    # Track the current tool and accumulate its input JSON
    current_tool = None
    tool_input = ""

    async for message in query(prompt="Read the README.md file", options=options):
        if isinstance(message, StreamEvent):
            event = message.get("event")
            event_type = event.get("type")

            if event_type == "content_block_start":
                # New tool call is starting
                content_block = event.get("content_block", {})
                if content_block.get("type") == "tool_use":
                    current_tool = content_block.get("name")
                    tool_input = ""
                    print(f"Starting tool: {current_tool}")

            elif event_type == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "input_json_delta":
                    # Accumulate JSON input as it streams in
                    chunk = delta.get("partial_json", "")
                    tool_input += chunk
                    print(f"  Input chunk: {chunk}")

            elif event_type == "content_block_stop":
                # Tool call complete - show final input
                if current_tool:
                    print(f"Tool {current_tool} called with: {tool_input}")
                    current_tool = None


asyncio.run(stream_tool_calls())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Track the current tool and accumulate its input JSON
let currentTool: string | null = null;
let toolInput = "";

for await (const message of query({
  prompt: "Read the README.md file",
  options: {
    includePartialMessages: true,
    allowedTools: ["Read", "Bash"],
  },
})) {
  if (message.type === "stream_event") {
    const event = message.event;

    if (event.type === "content_block_start") {
      // New tool call is starting
      if (event.content_block.type === "tool_use") {
        currentTool = event.content_block.name;
        toolInput = "";
        console.log(`Starting tool: ${currentTool}`);
      }
    } else if (event.type === "content_block_delta") {
      if (event.delta.type === "input_json_delta") {
        // Accumulate JSON input as it streams in
        const chunk = event.delta.partial_json;
        toolInput += chunk;
        console.log(`  Input chunk: ${chunk}`);
      }
    } else if (event.type === "content_block_stop") {
      // Tool call complete - show final input
      if (currentTool) {
        console.log(`Tool ${currentTool} called with: ${toolInput}`);
        currentTool = null;
      }
    }
  }
}
```

---

### Define type-safe schema with Zod (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/structured-outputs

Creates a Zod schema for a feature implementation plan with nested objects and arrays, converts it to JSON Schema, and uses it with the Claude Agent SDK query function. The schema includes validation for feature name, summary, implementation steps with complexity levels, and potential risks.

```typescript
import { z } from "zod";
import { query } from "@anthropic-ai/claude-agent-sdk";

// Define schema with Zod
const FeaturePlan = z.object({
  feature_name: z.string(),
  summary: z.string(),
  steps: z.array(
    z.object({
      step_number: z.number(),
      description: z.string(),
      estimated_complexity: z.enum(["low", "medium", "high"]),
    }),
  ),
  risks: z.array(z.string()),
});

type FeaturePlan = z.infer<typeof FeaturePlan>;

// Convert to JSON Schema
const schema = z.toJSONSchema(FeaturePlan);

// Use in query
for await (const message of query({
  prompt:
    "Plan how to add dark mode support to a React app. Break it into implementation steps.",
  options: {
    outputFormat: {
      type: "json_schema",
      schema: schema,
    },
  },
})) {
  if (message.type === "result" && message.structured_output) {
    // Validate and get fully typed result
    const parsed = FeaturePlan.safeParse(message.structured_output);
    if (parsed.success) {
      const plan: FeaturePlan = parsed.data;
      console.log(`Feature: ${plan.feature_name}`);
      console.log(`Summary: ${plan.summary}`);
      plan.steps.forEach((step) => {
        console.log(
          `${step.step_number}. [${step.estimated_complexity}] ${step.description}`,
        );
      });
    }
  }
}
```

---

### Define Type-Safe Tools with Schema Validation

Source: https://platform.claude.com/docs/en/agent-sdk/custom-tools

This example illustrates how to define type-safe tools using schema validation. In TypeScript, it leverages Zod schemas for both runtime validation and static type checking. In Python, it demonstrates simple type mapping for arguments using dictionary annotations, providing IDE support for argument access.

```typescript
import { z } from "zod";

tool(
  "process_data",
  "Process structured data with type safety",
  {
    // Zod schema defines both runtime validation and TypeScript types
    data: z.object({
      name: z.string(),
      age: z.number().min(0).max(150),
      email: z.string().email(),
      preferences: z.array(z.string()).optional(),
    }),
    format: z.enum(["json", "csv", "xml"]).default("json"),
  },
  async (args) => {
    // args is fully typed based on the schema
    // TypeScript knows: args.data.name is string, args.data.age is number, etc.
    console.log(`Processing ${args.data.name}'s data as ${args.format}`);

    // Your processing logic here
    return {
      content: [
        {
          type: "text",
          text: `Processed data for ${args.data.name}`,
        },
      ],
    };
  },
);
```

```python
from typing import Any


# Simple type mapping - recommended for most cases
@tool(
    "process_data",
    "Process structured data with type safety",
    {
        "name": str,
        "age": int,
        "email": str,
        "preferences": list,  # Optional parameters can be handled in the function
    },
)
async def process_data(args: dict[str, Any]) -> dict[str, Any]:
    # Access arguments with type hints for IDE support
    name = args["name"]
    age = args["age"]
    email = args["email"]
    preferences = args.get("preferences", [])

    print(f"Processing {name}'s data (age: {age})")

    return {"content": [{"type": "text", "text": f"Processed data for {name}"}]}
```

---

### Clear Conversation History using /clear command in Claude Agent SDK (TypeScript/Python)

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

This snippet shows how to use the `/clear` slash command to reset the conversation history and start a new session. It waits for a system initialization message (`init` subtype) to confirm the conversation has been cleared and logs the new session ID.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Clear conversation and start fresh
for await (const message of query({
  prompt: "/clear",
  options: { maxTurns: 1 },
})) {
  if (message.type === "system" && message.subtype === "init") {
    console.log("Conversation cleared, new session started");
    console.log("Session ID:", message.session_id);
  }
}
```

```python
import asyncio
from claude_agent_sdk import query


async def main():
    # Clear conversation and start fresh
    async for message in query(prompt="/clear", options={"max_turns": 1}):
        if message.type == "system" and message.subtype == "init":
            print("Conversation cleared, new session started")
            print("Session ID:", message.session_id)


asyncio.run(main())
```

---

### WebFetch Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the input and output structures for the `WebFetch` tool. This tool fetches content from a given URL and processes it with an AI model based on a provided prompt. Inputs include the URL and the prompt, while outputs contain the AI model's response, the fetched URL, and HTTP status information.

```python
{
    "url": str,  # The URL to fetch content from
    "prompt": str  # The prompt to run on the fetched content
}
```

```python
{
    "response": str,  # AI model's response to the prompt
    "url": str,  # URL that was fetched
    "final_url": str | None,  # Final URL after redirects
    "status_code": int | None  # HTTP status code
}
```

---

### Define ListMcpResources Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

This snippet defines the input and output schema for the `ListMcpResources` tool. It allows listing resources, optionally filtered by a `server` name. The tool returns a list of `resources`, each with a URI, name, description, MIME type, and server, along with the total count.

```python
# Input
{
    "server": str | None  # Optional server name to filter resources by
}

# Output
{
    "resources": [
        {
            "uri": str,
            "name": str,
            "description": str | None,
            "mimeType": str | None,
            "server": str
        }
    ],
    "total": int
}
```

---

### ListMcpResources Tool - Enumerate MCP Server Resources

Source: https://docs.claude.com/en/api/agent-sdk/python

Lists all available resources from MCP servers with optional filtering by server name. Returns an array of resource objects containing URI, name, description, MIME type, and server information, along with a total count. Useful for discovering available resources.

```json
{
  "server": "str | None"
}
```

---

### Create MCP server instance - createSdkMcpServer

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Creates an MCP server instance that runs in the same process as your application. Accepts server configuration including name, optional version, and array of tool definitions.

```typescript
function createSdkMcpServer(options: {
  name: string;
  version?: string;
  tools?: Array<SdkMcpToolDefinition<any>>;
}): McpSdkServerConfigWithInstance;
```

---

### Configure MCP Server via .mcp.json File

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

This JSON snippet illustrates how to define an MCP server, specifically a local filesystem server, within a `.mcp.json` configuration file. The SDK automatically loads this file from the project root, allowing for external configuration of MCP servers. It specifies the command and arguments needed to run the filesystem server.

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/me/projects"
      ]
    }
  }
}
```

---

### Implement TODO Tracking Agent with Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/structured-outputs

This code defines a JSON schema for extracting TODO comments, including their text, file, line, and optional author/date. It then uses the Claude Agent SDK's `query` function to prompt an AI agent to find all TODOs in a codebase and identify their authors. The agent processes the structured JSON output, logging the found TODOs and their blame information.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Define structure for TODO extraction
const todoSchema = {
  type: "object",
  properties: {
    todos: {
      type: "array",
      items: {
        type: "object",
        properties: {
          text: { type: "string" },
          file: { type: "string" },
          line: { type: "number" },
          author: { type: "string" },
          date: { type: "string" },
        },
        required: ["text", "file", "line"],
      },
    },
    total_count: { type: "number" },
  },
  required: ["todos", "total_count"],
};

// Agent uses Grep to find TODOs, Bash to get git blame info
for await (const message of query({
  prompt: "Find all TODO comments in this codebase and identify who added them",
  options: {
    outputFormat: {
      type: "json_schema",
      schema: todoSchema,
    },
  },
})) {
  if (message.type === "result" && message.structured_output) {
    const data = message.structured_output;
    console.log(`Found ${data.total_count} TODOs`);
    data.todos.forEach((todo) => {
      console.log(`${todo.file}:${todo.line} - ${todo.text}`);
      if (todo.author) {
        console.log(`  Added by ${todo.author} on ${todo.date}`);
      }
    });
  }
}
```

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

# Define structure for TODO extraction
todo_schema = {
    "type": "object",
    "properties": {
        "todos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "file": {"type": "string"},
                    "line": {"type": "number"},
                    "author": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["text", "file", "line"],
            },
        },
        "total_count": {"type": "number"},
    },
    "required": ["todos", "total_count"],
}


async def main():
    # Agent uses Grep to find TODOs, Bash to get git blame info
    async for message in query(
        prompt="Find all TODO comments in this codebase and identify who added them",
        options=ClaudeAgentOptions(
            output_format={"type": "json_schema", "schema": todo_schema}
        ),
    ):
        if isinstance(message, ResultMessage) and message.structured_output:
            data = message.structured_output
            print(f"Found {data['total_count']} TODOs")
            for todo in data["todos"]:
                print(f"{todo['file']}:{todo['line']} - {todo['text']}")
                if "author" in todo:
                    print(f"  Added by {todo['author']} on {todo['date']}")


asyncio.run(main())
```

---

### Modify Tool Input in Agent SDK PreToolUse Hook

Source: https://platform.claude.com/docs/en/agent-sdk/hooks

This example illustrates how to intercept and modify tool inputs within a `PreToolUse` hook. It specifically rewrites the `file_path` argument for 'Write' tool calls to prepend '/sandbox', effectively redirecting file writes. The hook returns `updatedInput` with the modified path and `permissionDecision: 'allow'` to auto-approve the rewritten operation.

```python
async def redirect_to_sandbox(input_data, tool_use_id, context):
    if input_data["hook_event_name"] != "PreToolUse":
        return {}

    if input_data["tool_name"] == "Write":
        original_path = input_data["tool_input"].get("file_path", "")
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "allow",
                "updatedInput": {
                    **input_data["tool_input"],
                    "file_path": f"/sandbox{original_path}",
                },
            }
        }
    return {}
```

```typescript
const redirectToSandbox: HookCallback = async (
  input,
  toolUseID,
  { signal },
) => {
  if (input.hook_event_name !== "PreToolUse") return {};

  const preInput = input as PreToolUseHookInput;
  const toolInput = preInput.tool_input as Record<string, unknown>;
  if (preInput.tool_name === "Write") {
    const originalPath = toolInput.file_path as string;
    return {
      hookSpecificOutput: {
        hookEventName: preInput.hook_event_name,
        permissionDecision: "allow",
        updatedInput: {
          ...toolInput,
          file_path: `/sandbox${originalPath}`,
        },
      },
    };
  }
  return {};
};
```

---

### Configure Docker Daemon to Use gVisor Runtime

Source: https://platform.claude.com/docs/en/agent-sdk/secure-deployment

This JSON snippet configures the Docker daemon to recognize and use the `runsc` runtime, which is gVisor's component. By adding this configuration to `/etc/docker/daemon.json`, Docker can then launch containers with gVisor for enhanced security by intercepting system calls.

```json
{
  "runtimes": {
    "runsc": {
      "path": "/usr/local/bin/runsc"
    }
  }
}
```

---

### AskUserQuestion Tool Input/Output Schema

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the input and output structure for the AskUserQuestion tool, which prompts users for clarification during agent execution. Input specifies questions with options and multi-select capability. Output returns the questions asked and user-provided answers.

```json
{
  "input": {
    "questions": [
      {
        "question": "str",
        "header": "str",
        "options": [
          {
            "label": "str",
            "description": "str"
          }
        ],
        "multiSelect": "bool"
      }
    ],
    "answers": "dict | None"
  },
  "output": {
    "questions": [
      {
        "question": "str",
        "header": "str",
        "options": [
          {
            "label": "str",
            "description": "str"
          }
        ],
        "multiSelect": "bool"
      }
    ],
    "answers": "dict[str, str]"
  }
}
```

---

### Load Settings from Filesystem Sources - TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/migration-guide

Shows how to explicitly load settings from filesystem sources in TypeScript after the v0.1.0 migration. The old behavior loaded all settings automatically; now you must specify which sources to load (user, project, local). Useful for maintaining backward compatibility.

```typescript
// BEFORE (v0.0.x) - Loaded all settings automatically
const result = query({ prompt: "Hello" });
// Would read from:
// - ~/.claude/settings.json (user)
// - .claude/settings.json (project)
// - .claude/settings.local.json (local)
// - CLAUDE.md files
// - Custom slash commands

// AFTER (v0.1.0) - No settings loaded by default
// To get the old behavior:
const result = query({
  prompt: "Hello",
  options: {
    settingSources: ["user", "project", "local"],
  },
});

// Or load only specific sources:
const result = query({
  prompt: "Hello",
  options: {
    settingSources: ["project"], // Only project settings
  },
});
```

---

### Configuring Claude Agent SDK to Load CLAUDE.md

Source: https://platform.claude.com/docs/en/agent-sdk/modifying-system-prompts

Demonstrates how to configure the Claude Agent SDK to load project-level CLAUDE.md files. It shows how to use the `claude_code` preset for the system prompt and explicitly enable `settingSources: ['project']` (TypeScript) or `setting_sources=['project']` (Python) to ensure CLAUDE.md content is processed.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// IMPORTANT: You must specify settingSources to load CLAUDE.md
// The claude_code preset alone does NOT load CLAUDE.md files
const messages = [];

for await (const message of query({
  prompt: "Add a new React component for user profiles",
  options: {
    systemPrompt: {
      type: "preset",
      preset: "claude_code", // Use Claude Code's system prompt
    },
    settingSources: ["project"], // Required to load CLAUDE.md from project
  },
})) {
  messages.push(message);
}

// Now Claude has access to your project guidelines from CLAUDE.md
```

```python
from claude_agent_sdk import query, ClaudeAgentOptions

# IMPORTANT: You must specify setting_sources to load CLAUDE.md
# The claude_code preset alone does NOT load CLAUDE.md files
messages = []

async for message in query(
    prompt="Add a new React component for user profiles",
    options=ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",  # Use Claude Code's system prompt
        },
        setting_sources=["project"],  # Required to load CLAUDE.md from project
    ),
):
    messages.append(message)

# Now Claude has access to your project guidelines from CLAUDE.md
```

---

### Run Docker Container with Security Hardening Options

Source: https://platform.claude.com/docs/en/agent-sdk/secure-deployment

This `docker run` command demonstrates a security-hardened configuration for an agent container. It drops all capabilities, prevents privilege escalation, restricts syscalls, makes the filesystem read-only, and limits resources like memory and PIDs. Communication is restricted to a mounted Unix socket, enhancing isolation.

```bash
docker run \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --security-opt seccomp=/path/to/seccomp-profile.json \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=100m \
  --tmpfs /home/agent:rw,noexec,nosuid,size=500m \
  --network none \
  --memory 2g \
  --cpus 2 \
  --pids-limit 100 \
  --user 1000:1000 \
  -v /path/to/code:/workspace:ro \
  -v /var/run/proxy.sock:/var/run/proxy.sock:ro \
  agent-image
```

---

### Configure stdio MCP Server

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

Set up local MCP servers that communicate via stdin/stdout. Supports TypeScript, Python, and .mcp.json configuration formats. Includes environment variable passing for authentication tokens.

```typescript
const _ = {
  options: {
    mcpServers: {
      github: {
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-github"],
        env: {
          GITHUB_TOKEN: process.env.GITHUB_TOKEN,
        },
      },
    },
    allowedTools: ["mcp__github__list_issues", "mcp__github__search_issues"],
  },
};
```

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_TOKEN": os.environ["GITHUB_TOKEN"]},
        }
    },
    allowed_tools=["mcp__github__list_issues", "mcp__github__search_issues"],
)
```

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

---

### Resume Session with Empty Prompt and Rewind Files (Python/TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/file-checkpointing

This code snippet illustrates how to resume a Claude SDK session, send an initial empty prompt to continue the conversation, and then rewind the agent's file system to a specified `checkpoint_id`. This is useful for resetting the agent's file state after a response or for debugging purposes.

```Python
async with ClaudeSDKClient(
    ClaudeAgentOptions(enable_file_checkpointing=True, resume=session_id)
) as client:
    await client.query("")
    async for message in client.receive_response():
        await client.rewind_files(checkpoint_id)
        break
```

```TypeScript
// Resume session with empty prompt, then rewind
const rewindQuery = query({
  prompt: "",
  options: { ...opts, resume: sessionId }
});

for await (const msg of rewindQuery) {
  await rewindQuery.rewindFiles(checkpointId);
  break;
}
```

---

### Configuration Options Reference

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Reference documentation for key configuration options used when initializing Claude Agent SDK queries, including settings sources, system prompts, thinking configuration, and tool management.

```APIDOC
## Configuration Options

### Description
Key configuration options for initializing and controlling Claude Agent SDK queries.

### settingSources
- **Type**: `SettingSource[]`
- **Default**: `[]` (no settings)
- **Description**: Control which filesystem settings to load. When omitted, no settings are loaded
- **Note**: Must include `'project'` to load CLAUDE.md files

### spawnClaudeCodeProcess
- **Type**: `(options: SpawnOptions) => SpawnedProcess`
- **Default**: `undefined`
- **Description**: Custom function to spawn the Claude Code process. Use to run Claude Code in VMs, containers, or remote environments

### stderr
- **Type**: `(data: string) => void`
- **Default**: `undefined`
- **Description**: Callback function for stderr output from the Claude Code process

### strictMcpConfig
- **Type**: `boolean`
- **Default**: `false`
- **Description**: Enforce strict MCP validation when loading MCP server configurations

### systemPrompt
- **Type**: `string | { type: 'preset'; preset: 'claude_code'; append?: string }`
- **Default**: `undefined` (minimal prompt)
- **Description**: System prompt configuration
- **Options**:
  - Pass a string for a custom system prompt
  - Pass `{ type: 'preset', preset: 'claude_code' }` to use Claude Code's default system prompt
  - When using the preset object form, add `append` property to extend the system prompt with additional instructions

### thinking
- **Type**: `ThinkingConfig`
- **Default**: `{ type: 'adaptive' }` for supported models
- **Description**: Controls Claude's thinking/reasoning behavior. See ThinkingConfig for available options

### tools
- **Type**: `string[] | { type: 'preset'; preset: 'claude_code' }`
- **Default**: `undefined`
- **Description**: Tool configuration
- **Options**:
  - Pass an array of tool names to specify individual tools
  - Use the preset `{ type: 'preset', preset: 'claude_code' }` to get Claude Code's default tools
```

---

### Configure Claude Agent Options with AskUserQuestion Tool

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This snippet demonstrates how to pass a `canUseTool` callback and explicitly include `AskUserQuestion` in the `tools` array within `ClaudeAgentOptions`. This ensures Claude can ask clarifying questions, especially when restricting other tool capabilities.

```python
async for message in query(
    prompt="Analyze this codebase",
    options=ClaudeAgentOptions(
        # Include AskUserQuestion in your tools list
        tools=["Read", "Glob", "Grep", "AskUserQuestion"],
        can_use_tool=can_use_tool,
    ),
):
    print(message)
```

```typescript
for await (const message of query({
  prompt: "Analyze this codebase",
  options: {
    // Include AskUserQuestion in your tools list
    tools: ["Read", "Glob", "Grep", "AskUserQuestion"],
    canUseTool: async (toolName, input) => {
      // Handle clarifying questions here
    },
  },
})) {
  console.log(message);
}
```

---

### Handle AskUserQuestion Tool - Display and Collect Answers - Python

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

Async handler that displays Claude's questions with numbered options to the user and collects their responses. Supports both single and multi-select questions, parsing numeric selections or free text input. Returns a PermissionResultAllow with the original questions and collected answers.

```python
async def handle_ask_user_question(input_data: dict) -> PermissionResultAllow:
    """Display Claude's questions and collect user answers."""
    answers = {}

    for q in input_data.get("questions", []):
        print(f"\n{q['header']}: {q['question']}")

        options = q["options"]
        for i, opt in enumerate(options):
            print(f"  {i + 1}. {opt['label']} - {opt['description']}")
        if q.get("multiSelect"):
            print("  (Enter numbers separated by commas, or type your own answer)")
        else:
            print("  (Enter a number, or type your own answer)")

        response = input("Your choice: ").strip()
        answers[q["question"]] = parse_response(response, options)

    return PermissionResultAllow(
        updated_input={
            "questions": input_data.get("questions", []),
            "answers": answers,
        }
    )
```

---

### Function: query with Sandbox Configuration

Source: https://platform.claude.com/docs/en/agent-sdk/python

Demonstrates how to use the `query` function from `claude_agent_sdk` with custom sandbox settings, including network configurations, to control the execution environment of the agent.

````APIDOC
## Function: query with Sandbox Configuration

### Description
Demonstrates how to use the `query` function from `claude_agent_sdk` with custom sandbox settings, including network configurations, to control the execution environment of the agent.

### Method
Function Call

### Endpoint
`claude_agent_sdk.query`

### Parameters
#### Function Parameters
- **prompt** (str) - Required - The natural language prompt or instruction for the agent.
- **options** (ClaudeAgentOptions) - Optional - Configuration options for the agent's execution.

#### ClaudeAgentOptions Fields
- **sandbox** (SandboxSettings) - Optional - Configuration for the agent's sandbox environment.

#### SandboxSettings Fields
- **enabled** (bool) - Optional - Default: `True` - Whether the sandbox is enabled for the agent.
- **autoAllowBashIfSandboxed** (bool) - Optional - Default: `False` - Automatically allow Bash commands if the agent is sandboxed.
- **network** (SandboxNetworkConfig) - Optional - Network-specific configuration for the sandbox.

#### SandboxNetworkConfig Fields
- **allowLocalBinding** (bool) - Optional - Default: `False` - Allow processes to bind to local ports within the sandbox.

### Request Example
```python
from claude_agent_sdk import query, ClaudeAgentOptions, SandboxSettings

sandbox_settings: SandboxSettings = {
    "enabled": True,
    "autoAllowBashIfSandboxed": True,
    "network": {"allowLocalBinding": True},
}

async for message in query(
    prompt="Build and test my project",
    options=ClaudeAgentOptions(sandbox=sandbox_settings),
):
    print(message)
````

### Response

#### Success Response (Stream of messages)

- **message** (str) - A streamed message from the agent, which can be an observation, thought, or tool output.

#### Response Example

```json
{
  "type": "message",
  "content": "Thinking..."
}
```

(Note: Actual response is a stream of various message types.)

````

--------------------------------

### Code Review Command Configuration

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

Markdown configuration file for a code review command that analyzes changed files and diffs using git tools. Defines allowed tools (Read, Grep, Glob, Bash), executes git commands to retrieve file changes, and provides a structured review checklist for quality, security, performance, tests, and documentation.

```markdown
---
allowed-tools: Read, Grep, Glob, Bash(git diff:*)
description: Comprehensive code review
---

## Changed Files
!`git diff --name-only HEAD~1`

## Detailed Changes
!`git diff HEAD~1`

## Review Checklist

Review the above changes for:
1. Code quality and readability
2. Security vulnerabilities
3. Performance implications
4. Test coverage
5. Documentation completeness

Provide specific, actionable feedback organized by priority.
````

---

### AskUserQuestion Tool

Source: https://platform.claude.com/docs/en/agent-sdk/python

Prompts the user with clarifying questions during agent execution. Supports multiple choice and multi-select options with customizable headers and descriptions for each question.

````APIDOC
## AskUserQuestion Tool

### Description
Asks the user clarifying questions during execution with support for multiple choice and multi-select options.

### Tool Name
`AskUserQuestion`

### Input Parameters
- **questions** (list) - Required - Questions to ask the user (1-4 questions)
  - **question** (str) - Required - The complete question to ask the user
  - **header** (str) - Required - Very short label displayed as a chip/tag (max 12 chars)
  - **options** (list) - Required - The available choices (2-4 options)
    - **label** (str) - Required - Display text for this option (1-5 words)
    - **description** (str) - Required - Explanation of what this option means
  - **multiSelect** (bool) - Required - Set to true to allow multiple selections
- **answers** (dict | None) - Optional - User answers populated by the permission system

### Request Example
```python
{
    "questions": [
        {
            "question": "Which deployment environment should we use?",
            "header": "Environment",
            "options": [
                {
                    "label": "Production",
                    "description": "Live environment for end users"
                },
                {
                    "label": "Staging",
                    "description": "Pre-production testing environment"
                }
            ],
            "multiSelect": false
        }
    ],
    "answers": null
}
````

### Response

#### Success Response (200)

- **questions** (list) - The questions that were asked
  - **question** (str) - The question text
  - **header** (str) - The question header/label
  - **options** (list) - Available options
    - **label** (str) - Option display text
    - **description** (str) - Option description
  - **multiSelect** (bool) - Whether multiple selections are allowed
- **answers** (dict[str, str]) - Maps question text to answer string (comma-separated for multi-select)

#### Response Example

```python
{
    "questions": [
        {
            "question": "Which deployment environment should we use?",
            "header": "Environment",
            "options": [
                {
                    "label": "Production",
                    "description": "Live environment for end users"
                },
                {
                    "label": "Staging",
                    "description": "Pre-production testing environment"
                }
            ],
            "multiSelect": false
        }
    ],
    "answers": {
        "Which deployment environment should we use?": "Production"
    }
}
```

````

--------------------------------

### Define SystemPromptPreset TypedDict for Claude Agent SDK

Source: https://docs.claude.com/en/api/agent-sdk/python

This Python `TypedDict` defines the structure for configuring a preset system prompt within the Claude Agent SDK. It specifies that the `type` must be 'preset' and the `preset` must be 'claude_code' to use Claude Code's system prompt. An optional `append` field allows adding custom instructions.

```python
class SystemPromptPreset(TypedDict):
    type: Literal["preset"]
    preset: Literal["claude_code"]
    append: NotRequired[str]
````

---

### Implement Claude Agent SDK Checkpointing and Session Rewind

Source: https://platform.claude.com/docs/en/agent-sdk/file-checkpointing

This code snippet illustrates how to enable file checkpointing, capture checkpoint metadata (user message UUIDs and timestamps) during an agent interaction, and subsequently rewind to a specific checkpoint. It requires the Claude Agent SDK and demonstrates how to resume a session with a specific session ID and then use the `rewindFiles` method. The `Checkpoint` dataclass/interface helps organize the metadata for tracking.

```python
from dataclasses import dataclass
from datetime import datetime
import asyncio

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.messages import UserMessage, ResultMessage

# Store checkpoint metadata for better tracking
@dataclass
class Checkpoint:
    id: str
    description: str
    timestamp: datetime


async def main():
    options = ClaudeAgentOptions(
        enable_file_checkpointing=True,
        permission_mode="acceptEdits",
        extra_args={
            "replay-user-messages": None
        },
    )

    checkpoints = []
    session_id = None

    async with ClaudeSDKClient(options) as client:
        await client.query("Refactor the authentication module")

        async for message in client.receive_response():
            if isinstance(message, UserMessage) and message.uuid:
                checkpoints.append(
                    Checkpoint(
                        id=message.uuid,
                        description=f"After turn {len(checkpoints) + 1}",
                        timestamp=datetime.now(),
                    )
                )
            if isinstance(message, ResultMessage) and not session_id:
                session_id = message.session_id

    # Later: rewind to any checkpoint by resuming the session
    if checkpoints and session_id:
        target = checkpoints[0]  # Pick any checkpoint
        async with ClaudeSDKClient(
            ClaudeAgentOptions(enable_file_checkpointing=True, resume=session_id)
        ) as client:
            await client.query("")  # Empty prompt to open the connection
            async for message in client.receive_response():
                await client.rewind_files(target.id)
                break
        print(f"Rewound to: {target.description}")


asyncio.run(main())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Store checkpoint metadata for better tracking
interface Checkpoint {
  id: string;
  description: string;
  timestamp: Date;
}

async function main() {
  const opts = {
    enableFileCheckpointing: true,
    permissionMode: "acceptEdits" as const,
    extraArgs: { "replay-user-messages": null },
  };

  const response = query({
    prompt: "Refactor the authentication module",
    options: opts,
  });

  const checkpoints: Checkpoint[] = [];
  let sessionId: string | undefined;

  for await (const message of response) {
    if (message.type === "user" && message.uuid) {
      checkpoints.push({
        id: message.uuid,
        description: `After turn ${checkpoints.length + 1}`,
        timestamp: new Date(),
      });
    }
    if ("session_id" in message && !sessionId) {
      sessionId = message.session_id;
    }
  }

  // Later: rewind to any checkpoint by resuming the session
  if (checkpoints.length > 0 && sessionId) {
    const target = checkpoints[0]; // Pick any checkpoint
    const rewindQuery = query({
      prompt: "", // Empty prompt to open the connection
      options: { ...opts, resume: sessionId },
    });

    for await (const msg of rewindQuery) {
      await rewindQuery.rewindFiles(target.id);
      break;
    }
    console.log(`Rewound to: ${target.description}`);
  }
}

main();
```

---

### Configure Default Tools with ToolsPreset

Source: https://docs.claude.com/en/api/agent-sdk/python

TypedDict for specifying preset tools configuration to use Claude Code's default tool set. Type must be 'preset' and preset must be 'claude_code'.

```python
class ToolsPreset(TypedDict):
    type: Literal["preset"]
    preset: Literal["claude_code"]
```

---

### WebFetch Tool

Source: https://platform.claude.com/docs/en/agent-sdk/python

Fetches content from a URL and processes it with an AI prompt. Returns the AI model's response along with HTTP status information and final URL after redirects.

````APIDOC
## WebFetch Tool

### Description
Fetches content from a specified URL and processes it using an AI model with a provided prompt.

### Tool Name
`WebFetch`

### Input Parameters
- **url** (string) - Required - The URL to fetch content from
- **prompt** (string) - Required - The prompt to run on the fetched content

### Request Example
```python
{
    "url": "https://example.com/article",
    "prompt": "Summarize the main points of this article"
}
````

### Response

- **response** (string) - AI model's response to the prompt
- **url** (string) - URL that was fetched
- **final_url** (string | null) - Final URL after redirects
- **status_code** (integer | null) - HTTP status code

### Response Example

```python
{
    "response": "The article discusses...",
    "url": "https://example.com/article",
    "final_url": "https://example.com/article?ref=search",
    "status_code": 200
}
```

````

--------------------------------

### Implement Pre and Post Tool Hooks in Python

Source: https://docs.claude.com/en/api/agent-sdk/python

Create hook functions to log tool usage before and after execution, with the ability to block dangerous commands. Pre-tool hooks can deny execution based on tool name and input validation, while post-tool hooks log completion. Requires ClaudeSDKClient, HookMatcher, and HookContext from claude_agent_sdk.

```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    HookContext,
)
import asyncio
from typing import Any


async def pre_tool_logger(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Log all tool usage before execution."""
    tool_name = input_data.get("tool_name", "unknown")
    print(f"[PRE-TOOL] About to use: {tool_name}")

    # You can modify or block the tool execution here
    if tool_name == "Bash" and "rm -rf" in str(input_data.get("tool_input", {})):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Dangerous command blocked",
            }
        }
    return {}


async def post_tool_logger(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Log results after tool execution."""
    tool_name = input_data.get("tool_name", "unknown")
    print(f"[POST-TOOL] Completed: {tool_name}")
    return {}


async def main():
    options = ClaudeAgentOptions(
        hooks={
            "PreToolUse": [
                HookMatcher(hooks=[pre_tool_logger]),
                HookMatcher(matcher="Bash", hooks=[pre_tool_logger]),
            ],
            "PostToolUse": [HookMatcher(hooks=[post_tool_logger])],
        },
        allowed_tools=["Read", "Write", "Bash"],
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("List files in current directory")

        async for message in client.receive_response():
            # Hooks will automatically log tool usage
            pass


asyncio.run(main())
````

---

### Read Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the input and output structures for the `Read` tool. This tool allows reading content from files, supporting both text and image formats. Inputs specify the file path and optional line-based limits, while outputs provide file content (with line numbers for text) or base64 encoded image data.

```python
{
    "file_path": str,  # The absolute path to the file to read
    "offset": int | None,  # The line number to start reading from
    "limit": int | None  # The number of lines to read
}
```

```python
{
    "content": str,  # File contents with line numbers
    "total_lines": int,  # Total number of lines in file
    "lines_returned": int  # Lines actually returned
}
```

```python
{
    "image": str,  # Base64 encoded image data
    "mime_type": str,  # Image MIME type
    "file_size": int  # File size in bytes
}
```

---

### Write Tool - File Creation and Content Writing

Source: https://docs.claude.com/en/api/agent-sdk/python

Writes content to a file at the specified path, creating the file if it doesn't exist or overwriting if it does. Returns confirmation with byte count written and file path for verification.

```json
{
  "file_path": "str",
  "content": "str"
}
```

```json
{
  "message": "str",
  "bytes_written": "int",
  "file_path": "str"
}
```

---

### Query with Session Capture and Resume - TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/overview

Demonstrates how to capture a session ID from an initial query and resume with full context in a subsequent query using the Claude Agent SDK. The first query reads an authentication module and captures the session ID from the init message. The second query resumes with the same session to find all places that call the authentication module.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

let sessionId: string | undefined;

// First query: capture the session ID
for await (const message of query({
  prompt: "Read the authentication module",
  options: { allowedTools: ["Read", "Glob"] },
})) {
  if (message.type === "system" && message.subtype === "init") {
    sessionId = message.session_id;
  }
}

// Resume with full context from the first query
for await (const message of query({
  prompt: "Now find all places that call it",
  options: { resume: sessionId },
})) {
  if ("result" in message) console.log(message.result);
}
```

---

### Load plugins from local directories using Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/plugins

Load one or multiple plugins from local file system paths by specifying their paths in the options configuration. Supports both relative paths (resolved from current working directory) and absolute paths. The SDK will make all plugin commands, agents, skills, and hooks available in the agent session.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Hello",
  options: {
    plugins: [
      { type: "local", path: "./my-plugin" },
      { type: "local", path: "/absolute/path/to/another-plugin" },
    ],
  },
})) {
  // Plugin commands, agents, and other features are now available
}
```

```python
import asyncio
from claude_agent_sdk import query


async def main():
    async for message in query(
        prompt="Hello",
        options={
            "plugins": [
                {"type": "local", "path": "./my-plugin"},
                {"type": "local", "path": "/absolute/path/to/another-plugin"},
            ]
        },
    ):
        # Plugin commands, agents, and other features are now available
        pass


asyncio.run(main())
```

---

### Method: Transport.is_ready()

Source: https://docs.claude.com/en/api/agent-sdk/python

Checks the current state of the transport to determine if it is ready to send and receive data.

````APIDOC
## METHOD Transport.is_ready()

### Description
Checks the current state of the transport to determine if it is ready to send and receive data.

### Method
`abstract`

### Endpoint
`Transport.is_ready`

### Parameters
#### Method Parameters
- No parameters.

### Request Example
```python
# Assuming 'my_transport_instance' is an instance of a class implementing Transport
is_ready_status = my_transport_instance.is_ready()
````

### Response

#### Success Response (200)

- Returns `bool` - `True` if the transport is ready for communication, `False` otherwise.

#### Response Example

```json
true
```

````

--------------------------------

### ToolsPreset

Source: https://docs.claude.com/en/api/agent-sdk/python

Configuration for using a predefined set of tools, such as Claude Code's default tool set.

```APIDOC
## ToolsPreset

### Description
Preset tools configuration for using Claude Code's default tool set.

### Definition
```python
class ToolsPreset(TypedDict):
    type: Literal["preset"]
    preset: Literal["claude_code"]
````

### Fields

- **type** (Literal["preset"]) - Required - Must be "preset" to indicate a preset configuration
- **preset** (Literal["claude_code"]) - Required - Specifies the name of the preset to use, e.g., "claude_code"

````

--------------------------------

### Glob Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the input and output structures for the `Glob` tool. This tool performs pattern matching to find files within a specified directory. Inputs include a glob pattern and an optional search path, while outputs provide a list of matching file paths and the total count.

```python
{
    "pattern": str,  # The glob pattern to match files against
    "path": str | None  # The directory to search in (defaults to cwd)
}
````

```python
{
    "matches": list[str],  # Array of matching file paths
    "count": int,  # Number of matches found
    "search_path": str  # Search directory used
}
```

---

### Write Tool

Source: https://platform.claude.com/docs/en/agent-sdk/python

Writes content to a file at the specified path. Creates the file if it doesn't exist or overwrites existing content. Returns confirmation with bytes written and file path.

````APIDOC
## Write Tool

### Description
Writes content to a file at the specified absolute path. Creates new files or overwrites existing ones.

### Tool Name
`Write`

### Input Parameters
- **file_path** (string) - Required - The absolute path to the file to write
- **content** (string) - Required - The content to write to the file

### Request Example
```python
{
    "file_path": "/path/to/output.txt",
    "content": "Hello, World!"
}
````

### Response

- **message** (string) - Success message
- **bytes_written** (integer) - Number of bytes written
- **file_path** (string) - File path that was written

### Response Example

```python
{
    "message": "File written successfully",
    "bytes_written": 13,
    "file_path": "/path/to/output.txt"
}
```

````

--------------------------------

### Test Runner Command Configuration

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

Markdown configuration file for a test runner command that executes tests matching an optional pattern. Supports multiple test frameworks (Jest, pytest, etc.), includes automatic framework detection, test execution with pattern matching, failure analysis, and verification re-runs.

```markdown
---
allowed-tools: Bash, Read, Edit
argument-hint: [test-pattern]
description: Run tests with optional pattern
---

Run tests matching pattern: $ARGUMENTS

1. Detect the test framework (Jest, pytest, etc.)
2. Run tests with the provided pattern
3. If tests fail, analyze and fix them
4. Re-run to verify fixes
````

---

### Configure Tool Search with Environment Variables

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

Set up tool search behavior using the ENABLE_TOOL_SEARCH environment variable to control when MCP tools are loaded into context. Supports auto mode with customizable thresholds, always-on, or disabled states. This configuration determines whether tools are deferred or loaded upfront based on context window consumption.

```TypeScript
const options = {
  mcpServers: {
    // your MCP servers
  },
  env: {
    ENABLE_TOOL_SEARCH: "auto:5" // Enable at 5% threshold
  }
};
```

```Python
options = ClaudeAgentOptions(
    mcp_servers={...},  # your MCP servers
    env={
        "ENABLE_TOOL_SEARCH": "auto:5"  # Enable at 5% threshold
    },
)
```

---

### TodoWrite Tool

Source: https://platform.claude.com/docs/en/agent-sdk/python

Writes and manages todo items with status tracking. Supports pending, in_progress, and completed statuses. Returns statistics on task distribution.

````APIDOC
## TodoWrite Tool

### Description
Writes and manages todo items with status tracking and statistics reporting.

### Tool Name
`TodoWrite`

### Input Parameters
- **todos** (array) - Required - Array of todo objects
  - **content** (string) - Required - The task description
  - **status** (string) - Required - Task status: "pending", "in_progress", or "completed"
  - **activeForm** (string) - Required - Active form of the description

### Request Example
```python
{
    "todos": [
        {
            "content": "Complete project documentation",
            "status": "in_progress",
            "activeForm": "Completing project documentation"
        },
        {
            "content": "Review pull requests",
            "status": "pending",
            "activeForm": "Reviewing pull requests"
        },
        {
            "content": "Deploy to production",
            "status": "completed",
            "activeForm": "Deployed to production"
        }
    ]
}
````

### Response

- **message** (string) - Success message
- **stats** (object) - Task statistics
  - **total** (integer) - Total number of tasks
  - **pending** (integer) - Number of pending tasks
  - **in_progress** (integer) - Number of in-progress tasks
  - **completed** (integer) - Number of completed tasks

### Response Example

```python
{
    "message": "Todos written successfully",
    "stats": {
        "total": 3,
        "pending": 1,
        "in_progress": 1,
        "completed": 1
    }
}
```

````

--------------------------------

### WebFetch Tool - Web Content Retrieval with AI Processing

Source: https://docs.claude.com/en/api/agent-sdk/python

Fetches content from a URL and processes it with an AI model using a provided prompt. Returns AI model response along with HTTP status code and final URL after redirects. Useful for extracting specific information from web pages.

```json
{
  "url": "str",
  "prompt": "str"
}
````

```json
{
  "response": "str",
  "url": "str",
  "final_url": "str | None",
  "status_code": "int | None"
}
```

---

### AskUserQuestion Tool Input/Output Schema

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the input and output schemas for the AskUserQuestion tool used to request clarifying information from users during agent execution. Supports multiple questions with configurable options and multi-select capabilities.

```python
# AskUserQuestion Tool Input
{
    "questions": [
        {
            "question": str,  # The complete question to ask the user
            "header": str,  # Very short label displayed as a chip/tag (max 12 chars)
            "options": [
                {
                    "label": str,  # Display text for this option (1-5 words)
                    "description": str,  # Explanation of what this option means
                }
            ],
            "multiSelect": bool,  # Set to true to allow multiple selections
        }
    ],
    "answers": dict | None,  # User answers populated by the permission system
}

# AskUserQuestion Tool Output
{
    "questions": [
        {
            "question": str,
            "header": str,
            "options": [{"label": str, "description": str}],
            "multiSelect": bool,
        }
    ],
    "answers": dict[str, str],  # Maps question text to answer string
}
```

---

### Define and Use Custom Tools with Claude Agent SDK Client (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This Python code illustrates how to define custom tools using the `@tool` decorator, such as `calculate` and `get_time`. It then demonstrates configuring these tools with `ClaudeAgentOptions` and `create_sdk_mcp_server` for use within an interactive `ClaudeSDKClient` session, allowing the agent to perform specific actions.

```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock,
)
import asyncio
from typing import Any


# Define custom tools with @tool decorator
@tool("calculate", "Perform mathematical calculations", {"expression": str})
async def calculate(args: dict[str, Any]) -> dict[str, Any]:
    try:
        result = eval(args["expression"], {"__builtins__": {}})
        return {"content": [{"type": "text", "text": f"Result: {result}"}]}
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True,
        }


@tool("get_time", "Get current time", {})
async def get_time(args: dict[str, Any]) -> dict[str, Any]:
    from datetime import datetime

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"content": [{"type": "text", "text": f"Current time: {current_time}"}]}


async def main():
    # Create SDK MCP server with custom tools
    my_server = create_sdk_mcp_server(
        name="utilities", version="1.0.0", tools=[calculate, get_time]
    )

    # Configure options with the server
    options = ClaudeAgentOptions(
        mcp_servers={"utils": my_server},
        allowed_tools=["mcp__utils__calculate", "mcp__utils__get_time"],
    )

    # Use ClaudeSDKClient for interactive tool usage
    async with ClaudeSDKClient(options=options) as client:
        await client.query("What's 123 * 456?")

        # Process calculation response
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Calculation: {block.text}")

        # Follow up with time query
        await client.query("What time is it now?")

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Time: {block.text}")


asyncio.run(main())
```

---

### Query Database with Claude Agent SDK using Postgres MCP Server

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

This snippet demonstrates how to use the Claude Agent SDK to query a PostgreSQL database using natural language. It configures a Postgres MCP server via `npx`, passes a connection string from an environment variable, and restricts operations to read-only queries. The agent automatically generates SQL and returns results.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Connection string from environment variable
const connectionString = process.env.DATABASE_URL;

for await (const message of query({
  // Natural language query - Claude writes the SQL
  prompt: "How many users signed up last week? Break it down by day.",
  options: {
    mcpServers: {
      postgres: {
        command: "npx",
        // Pass connection string as argument to the server
        args: ["-y", "@modelcontextprotocol/server-postgres", connectionString],
      },
    },
    // Allow only read queries, not writes
    allowedTools: ["mcp__postgres__query"],
  },
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}
```

```python
import asyncio
import os
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


async def main():
    # Connection string from environment variable
    connection_string = os.environ["DATABASE_URL"]

    options = ClaudeAgentOptions(
        mcp_servers={
            "postgres": {
                "command": "npx",
                # Pass connection string as argument to the server
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-postgres",
                    connection_string,
                ],
            }
        },
        # Allow only read queries, not writes
        allowed_tools=["mcp__postgres__query"],
    )

    # Natural language query - Claude writes the SQL
    async for message in query(
        prompt="How many users signed up last week? Break it down by day.",
        options=options,
    ):
        if isinstance(message, ResultMessage) and message.subtype == "success":
            print(message.result)


asyncio.run(main())
```

---

### Function: can_use_tool for Unsandboxed Commands

Source: https://platform.claude.com/docs/en/agent-sdk/python

Illustrates how to implement a `can_use_tool` handler to manage permissions for commands requested to run outside the sandbox, providing custom authorization logic.

````APIDOC
## Function: can_use_tool for Unsandboxed Commands

### Description
Illustrates how to implement a `can_use_tool` handler to manage permissions for commands requested to run outside the sandbox, providing custom authorization logic based on the tool and its input.

### Method
Callback Function

### Endpoint
`ToolPermissionContext` Callback

### Parameters
#### Function Parameters
- **tool** (str) - Required - The name of the tool being requested (e.g., "Bash").
- **input** (dict) - Required - The input arguments provided to the tool.
  - **dangerouslyDisableSandbox** (bool) - Optional - Indicates if the model is requesting to run this command outside the sandbox.
  - **command** (str) - Optional - (Specific to Bash tool) The command string to be executed.
- **context** (ToolPermissionContext) - Required - Contextual information related to the permission check.

### Request Example
```python
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)


async def can_use_tool(
    tool: str, input: dict, context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    # Check if the model is requesting to bypass the sandbox
    if tool == "Bash" and input.get("dangerouslyDisableSandbox"):
        # The model is requesting to run this command outside the sandbox
        print(f"Unsandboxed command requested: {input.get('command')}")

        # Placeholder for custom authorization logic
        def is_command_authorized(cmd: str) -> bool:
            # Example: Only allow 'ls' and 'pwd' unsandboxed
            return cmd in ["ls", "pwd"]

        if is_command_authorized(input.get("command")):
            return PermissionResultAllow()
        return PermissionResultDeny(
            message="Command not authorized for unsandboxed execution"
        )
    return PermissionResultAllow()

# This function would then be passed to the agent's options, e.g.:
# options=ClaudeAgentOptions(can_use_tool=can_use_tool)
````

### Response

#### Success Response (PermissionResultAllow)

- **PermissionResultAllow()** - Grants permission for the tool execution.

#### Error Response (PermissionResultDeny)

- **PermissionResultDeny()** - Denies permission for the tool execution.
  - **message** (str) - Optional - A message explaining the reason for denial.

#### Response Example

```python
# Example of allowing a command
PermissionResultAllow()

# Example of denying a command
PermissionResultDeny(message="Command 'rm -rf /' is not allowed unsandboxed")
```

````

--------------------------------

### Define ExitPlanMode Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

This snippet defines the input and output schema for the `ExitPlanMode` tool. It is used to present a `plan` to the user for approval. The tool returns a confirmation `message` and a boolean `approved` indicating whether the user accepted the plan.

```python
# Input
{
    "plan": str  # The plan to run by the user for approval
}

# Output
{
    "message": str,  # Confirmation message
    "approved": bool | None  # Whether user approved the plan
}
````

---

### TodoWrite Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the input and output structures for the `TodoWrite` tool. This tool allows managing a list of tasks (todos), including their content, status, and active form. Inputs consist of an array of todo items, and outputs provide a success message along with statistics on the total, pending, in-progress, and completed tasks.

```python
{
    "todos": [
        {
            "content": str,  # The task description
            "status": "pending" | "in_progress" | "completed",  # Task status
            "activeForm": str  # Active form of the description
        }
    ]
}
```

```python
{
    "message": str,  # Success message
    "stats": {"total": int, "pending": int, "in_progress": int, "completed": int}
}
```

---

### Search Codebase for TODO Comments with Built-in Tools

Source: https://platform.claude.com/docs/en/agent-sdk/overview

Creates an agent that searches a codebase for TODO comments using Read, Glob, and Grep tools. The agent processes the prompt asynchronously and returns a summary of findings. Requires the claude_agent_sdk package and async runtime support.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    async for message in query(
        prompt="Find all TODO comments and create a summary",
        options=ClaudeAgentOptions(allowed_tools=["Read", "Glob", "Grep"]),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Find all TODO comments and create a summary",
  options: { allowedTools: ["Read", "Glob", "Grep"] },
})) {
  if ("result" in message) console.log(message.result);
}
```

---

### Method ClaudeSDKClient.get_server_info

Source: https://platform.claude.com/docs/en/agent-sdk/python

Retrieves information about the connected server.

````APIDOC
## METHOD ClaudeSDKClient.get_server_info

### Description
Retrieves information about the connected server.

### Method
Async Class Method

### Endpoint
async def get_server_info(self) -> dict[str, Any] | None

### Parameters
#### Request Body
- No parameters.

### Request Example
```python
# Assuming 'client' is an initialized ClaudeSDKClient instance
info = await client.get_server_info()
print(info)
````

### Response

#### Success Response (200)

- **dict[str, Any] | None** - A dictionary containing server information, or `None` if not available.

#### Response Example

```json
{
  "name": "Claude Agent Server",
  "version": "1.
```

---

### Write Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the input and output structures for the `Write` tool. This tool enables writing specified content to a file at a given path. Inputs include the target file path and the content to be written, and outputs confirm the success of the write operation, including the number of bytes written.

```python
{
    "file_path": str,  # The absolute path to the file to write
    "content": str  # The content to write to the file
}
```

```python
{
    "message": str,  # Success message
    "bytes_written": int,  # Number of bytes written
    "file_path": str  # File path that was written
}
```

---

### Configure Sandbox Settings with Query Function

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Demonstrates how to enable and configure sandbox mode when using the query function from the Claude Agent SDK. Shows enabling sandbox, auto-allowing bash commands, and configuring network settings.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Build and test my project",
  options: {
    sandbox: {
      enabled: true,
      autoAllowBashIfSandboxed: true,
      network: {
        allowLocalBinding: true,
      },
    },
  },
})) {
  if ("result" in message) console.log(message.result);
}
```

---

### listSessions()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Discovers and lists past sessions with light metadata. Filter by project directory or list sessions across all projects.

````APIDOC
## Function listSessions()

### Description
Discovers and lists past sessions with light metadata. Filter by project directory or list sessions across all projects.

### Method
Function

### Endpoint
listSessions()

### Parameters
#### Path Parameters
(None)

#### Query Parameters
(None)

#### Request Body
- **options.dir** (string) - Optional - Directory to list sessions for. Returns sessions for this project (and its git worktrees). When omitted, returns sessions across all projects
- **options.limit** (number) - Optional - Maximum number of sessions to return

### Request Example
```typescript
import { listSessions } from "@anthropic-ai/claude-agent-sdk";

// List sessions for a specific project
const sessions = await listSessions({ dir: "/path/to/project" });

for (const session of sessions) {
  console.log(`${session.summary} (${new Date(session.lastModified).toLocaleDateString()})`);
}

// List all sessions across all projects, limited to 10
const recent = await listSessions({ limit: 10 });
````

### Response

#### Success Response (Returns Promise<SDKSessionInfo[]>)

- **SDKSessionInfo[]** (array) - An array of session information objects.
  - **sessionId** (string) - Unique session identifier (UUID)
  - **summary** (string) - Display title: custom title, auto-generated summary, or first prompt
  - **lastModified** (number) - Last modified time in milliseconds since epoch
  - **fileSize** (number) - Session file size in bytes
  - **customTitle** (string | undefined) - User-set session title (via `/rename`)
  - **firstPrompt** (string | undefined) - First meaningful user prompt in the session
  - **gitBranch** (string | undefined) - Git branch at the end of the session
  - **cwd** (string | undefined) - Working directory for the session

#### Response Example

```json
[
  {
    "sessionId": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "summary": "My first session",
    "lastModified": 1678886400000,
    "fileSize": 1024,
    "customTitle": "My first session",
    "firstPrompt": "Hello Claude, how are you?",
    "gitBranch": "main",
    "cwd": "/path/to/project"
  },
  {
    "sessionId": "b2c3d4e5-f6a7-8901-2345-67890abcdef0",
    "summary": "Another session",
    "lastModified": 1678972800000,
    "fileSize": 2048,
    "customTitle": null,
    "firstPrompt": "Write a Python script.",
    "gitBranch": "feature/new-agent",
    "cwd": "/path/to/project"
  }
]
```

````

--------------------------------

### Define ReadMcpResource Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

This snippet defines the input and output schema for the `ReadMcpResource` tool. It reads a specific resource from an MCP server using its `server` name and `uri`. The tool returns the `contents` of the resource, which can include its URI, MIME type, text content, or a blob, along with the `server` it was read from.

```python
# Input
{
    "server": str,  # The MCP server name
    "uri": str  # The resource URI to read
}

# Output
{
    "contents": [
        {"uri": str, "mimeType": str | None, "text": str | None, "blob": str | None}
    ],
    "server": str
}
````

---

### TodoWrite Tool - Task Management with Status Tracking

Source: https://docs.claude.com/en/api/agent-sdk/python

Writes and manages todo items with status tracking (pending, in_progress, completed). Returns success message with statistics including total tasks and count per status. Useful for maintaining task lists with active form descriptions.

```json
{
  "todos": [
    {
      "content": "str",
      "status": "pending | in_progress | completed",
      "activeForm": "str"
    }
  ]
}
```

```json
{
  "message": "str",
  "stats": {
    "total": "int",
    "pending": "int",
    "in_progress": "int",
    "completed": "int"
  }
}
```

---

### ExitPlanMode Tool - Submit Plan for User Approval

Source: https://docs.claude.com/en/api/agent-sdk/python

Submits a plan to the user for approval before execution. Accepts a plan string as input and returns a confirmation message with an approval boolean or None. Enables user control over agent actions.

```json
{
  "plan": "str"
}
```

---

### Basic Session with V1 TypeScript SDK

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Create a session and send a message using the V1 SDK with async generator pattern. Both input and output flow through a single async generator, requiring restructuring for multi-turn logic compared to the V2 approach.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

const q = query({
  prompt: "Hello!",
  options: { model: "claude-opus-4-6" },
});

for await (const msg of q) {
  if (msg.type === "assistant") {
    const text = msg.message.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("");
    console.log(text);
  }
}
```

---

### create_sdk_mcp_server()

Source: https://docs.claude.com/en/api/agent-sdk/python

The `create_sdk_mcp_server()` function allows you to create an in-process MCP server directly within your Python application, enabling custom tool integration.

```APIDOC
## create_sdk_mcp_server()

### Description
Create an in-process MCP server that runs within your Python application.

### Method
SDK Function

### Endpoint
N/A

### Parameters
#### Path Parameters
N/A

#### Query Parameters
N/A

#### Request Body
- **name** (`str`) - Required - Unique identifier for the server
- **version** (`str`) - Optional - Server version string (default: "1.0.0")
- **tools** (`list[SdkMcpTool[Any]] | None`) - Optional - List of tool functions created with `@tool` decorator (default: `None`)

### Request Example
N/A (parameters are direct arguments)

### Response
#### Success Response (Returns)
- `McpSdkServerConfig`

#### Response Example
N/A
```

---

### Glob Tool - File Pattern Matching and Discovery

Source: https://docs.claude.com/en/api/agent-sdk/python

Matches files against glob patterns within a specified directory. Returns array of matching file paths with match count and search directory information. Useful for discovering files by extension or naming convention.

```json
{
  "pattern": "str",
  "path": "str | None"
}
```

```json
{
  "matches": "list[str]",
  "count": "int",
  "search_path": "str"
}
```

---

### Define a Custom Command with Arguments and Placeholders in Markdown

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

This snippet demonstrates how to create a custom command that accepts dynamic arguments using placeholders (`$1`, `$2`) and an `argument-hint` in its frontmatter. The `/fix-issue` command is designed to process an issue number and priority, enabling flexible command execution.

```markdown
---
argument-hint: [issue-number] [priority]
description: Fix a GitHub issue
---

Fix issue #$1 with priority $2.
Check the issue description and implement the necessary changes.
```

---

### unstable_v2_prompt()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

One-shot convenience function for single-turn queries.

```APIDOC
## SDK Function unstable_v2_prompt()

### Description
One-shot convenience function for single-turn queries.

### Method
SDK Function

### Parameters
- **prompt** (string) - Required - The prompt message for the query.

#### Request Body
- **model** (string) - Required - The model to use for the prompt. Additional options are supported but not detailed here.

### Request Example
{
  "prompt": "Tell me a story about a brave knight.",
  "model": "claude-opus-4-6"
}

### Response
#### Success Response (Promise<SDKResultMessage>)
- **SDKResultMessage** (object) - The result message from the SDK. The specific structure of `SDKResultMessage` is not detailed in the provided text.

#### Response Example
{
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Once upon a time, in a land far away..."
    }
  ]
}
```

---

### Define `create_sdk_mcp_server()` signature in Python SDK

Source: https://docs.claude.com/en/api/agent-sdk/python

This is the function signature for `create_sdk_mcp_server()`, which creates an in-process MCP server within a Python application. It takes a server name, optional version, and a list of `SdkMcpTool` instances, returning an `McpSdkServerConfig`. This function is used to host custom tools and expose them to the Claude Agent.

```python
def create_sdk_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: list[SdkMcpTool[Any]] | None = None
) -> McpSdkServerConfig
```

---

### Implement Claude Agent SDK checkpointing for doc comment generation (Python/TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/file-checkpointing

This script uses the Claude Agent SDK to automatically add documentation comments to the `utils` file. It configures the SDK with file checkpointing enabled and sets `permission_mode` to `acceptEdits`. The script captures the `checkpoint_id` and `session_id` to allow the user to rewind the changes made by the agent, restoring the original file content.

```python
import asyncio
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    UserMessage,
    ResultMessage,
)


async def main():
    # Configure the SDK with checkpointing enabled
    # - enable_file_checkpointing: Track file changes for rewinding
    # - permission_mode: Auto-accept file edits without prompting
    # - extra_args: Required to receive user message UUIDs in the stream
    options = ClaudeAgentOptions(
        enable_file_checkpointing=True,
        permission_mode="acceptEdits",
        extra_args={"replay-user-messages": None},
    )

    checkpoint_id = None  # Store the user message UUID for rewinding
    session_id = None  # Store the session ID for resuming

    print("Running agent to add doc comments to utils.py...\n")

    # Run the agent and capture checkpoint data from the response stream
    async with ClaudeSDKClient(options) as client:
        await client.query("Add doc comments to utils.py")

        async for message in client.receive_response():
            # Capture the first user message UUID - this is our restore point
            if isinstance(message, UserMessage) and message.uuid and not checkpoint_id:
                checkpoint_id = message.uuid
            # Capture the session ID so we can resume later
            if isinstance(message, ResultMessage):
                session_id = message.session_id

    print("Done! Open utils.py to see the added doc comments.\n")

    # Ask the user if they want to rewind the changes
    if checkpoint_id and session_id:
        response = input("Rewind to remove the doc comments? (y/n): ")

        if response.lower() == "y":
            # Resume the session with an empty prompt, then rewind
            async with ClaudeSDKClient(
                ClaudeAgentOptions(enable_file_checkpointing=True, resume=session_id)
            ) as client:
                await client.query("")  # Empty prompt opens the connection
                async for message in client.receive_response():
                    await client.rewind_files(checkpoint_id)  # Restore files
                    break

            print(
                "\n✓ File restored! Open utils.py to verify the doc comments are gone."
            )
        else:
            print("\nKept the modified file.")


asyncio.run(main())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";
import * as readline from "readline";

async function main() {
  // Configure the SDK with checkpointing enabled
  // - enableFileCheckpointing: Track file changes for rewinding
  // - permissionMode: Auto-accept file edits without prompting
  // - extraArgs: Required to receive user message UUIDs in the stream
  const opts = {
    enableFileCheckpointing: true,
    permissionMode: "acceptEdits" as const,
    extraArgs: { "replay-user-messages": null }
  };

  let sessionId: string | undefined; // Store the session ID for resuming
  let checkpointId: string | undefined; // Store the user message UUID for rewinding

  console.log("Running agent to add doc comments to utils.ts...\n");

  // Run the agent and capture checkpoint data from the response stream
  const response = query({
    prompt: "Add doc comments to utils.ts",
    options: opts
  });

  for await (const message of response) {
    // Capture the first user message UUID - this is our restore point
    if (message.type === "user" && message.uuid && !checkpointId) {
      checkpointId = message.uuid;
    }
```

---

### Define SDK Plugin Configuration

Source: https://platform.claude.com/docs/en/agent-sdk/python

TypedDict class for loading local plugins in the SDK. Currently supports only local plugin type with a required path field pointing to the plugin directory. Accepts both absolute and relative paths.

```python
class SdkPluginConfig(TypedDict):
    type: Literal["local"]
    path: str
```

```python
plugins = [
    {"type": "local", "path": "./my-plugin"},
    {"type": "local", "path": "/absolute/path/to/plugin"},
]
```

---

### TOOL AskUserQuestion

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the input and output structure for the 'AskUserQuestion' tool, used to prompt the user for clarifying information or decisions during execution.

```APIDOC
## TOOL /tools/AskUserQuestion

### Description
Asks the user clarifying questions during execution. See Handle approvals and user input for usage details.

### Method
TOOL

### Endpoint
/tools/AskUserQuestion

### Parameters
#### Path Parameters
- No path parameters.

#### Query Parameters
- No query parameters.

#### Request Body
- **questions** (array) - Required - Questions to ask the user (1-4 questions)
  - **question** (string) - Required - The complete question to ask the user
  - **header** (string) - Required - Very short label displayed as a chip/tag (max 12 chars)
  - **options** (array) - Required - The available choices (2-4 options)
    - **label** (string) - Required - Display text for this option (1-5 words)
    - **description** (string) - Required - Explanation of what this option means
  - **multiSelect** (boolean) - Required - Set to true to allow multiple selections
- **answers** (object | null) - Optional - User answers populated by the permission system

### Request Example
{
  "questions": [
    {
      "question": "Which database do you want to use?",
      "header": "DB Choice",
      "options": [
        {
          "label": "PostgreSQL",
          "description": "Relational database"
        },
        {
          "label": "MongoDB",
          "description": "NoSQL document database"
        }
      ],
      "multiSelect": false
    }
  ],
  "answers": null
}

### Response
#### Success Response (200)
- **questions** (array) - The questions that were asked
  - **question** (string)
  - **header** (string)
  - **options** (array)
    - **label** (string)
    - **description** (string)
  - **multiSelect** (boolean)
- **answers** (object) - Maps question text to answer string. Multi-select answers are comma-separated.

#### Response Example
{
  "questions": [
    {
      "question": "Which database do you want to use?",
      "header": "DB Choice",
      "options": [
        {
          "label": "PostgreSQL",
          "description": "Relational database"
        },
        {
          "label": "MongoDB",
          "description": "NoSQL document database"
        }
      ],
      "multiSelect": false
    }
  ],
  "answers": {
    "Which database do you want to use?": "PostgreSQL"
  }
}
```

---

### WebSearch Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the input and output structures for the `WebSearch` tool. This tool performs web searches based on a query, with options to filter by allowed or blocked domains. Inputs include the search query and domain constraints, and outputs provide a list of search results with titles, URLs, and snippets.

```python
{
    "query": str,  # The search query to use
    "allowed_domains": list[str] | None,  # Only include results from these domains
    "blocked_domains": list[str] | None  # Never include results from these domains
}
```

```python
{
    "results": [{"title": str, "url": str, "snippet": str, "metadata": dict | None}],
    "total_results": int,
    "query": str
}
```

---

### Invoke Custom Commands and List Available Commands in Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

This snippet demonstrates how to programmatically invoke a custom command (e.g., `/refactor`) using the Claude Agent SDK. It also shows how to retrieve a list of all available commands, including both built-in and custom ones, from the system initialization message.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Use a custom command
for await (const message of query({
  prompt: "/refactor src/auth/login.ts",
  options: { maxTurns: 3 },
})) {
  if (message.type === "assistant") {
    console.log("Refactoring suggestions:", message.message);
  }
}

// Custom commands appear in the slash_commands list
for await (const message of query({
  prompt: "Hello",
  options: { maxTurns: 1 },
})) {
  if (message.type === "system" && message.subtype === "init") {
    // Will include both built-in and custom commands
    console.log("Available commands:", message.slash_commands);
    // Example: ["/compact", "/clear", "/help", "/refactor", "/security-check"]
  }
}
```

```python
import asyncio
from claude_agent_sdk import query


async def main():
    # Use a custom command
    async for message in query(
        prompt="/refactor src/auth/login.py", options={"max_turns": 3}
    ):
        if message.type == "assistant":
            print("Refactoring suggestions:", message.message)

    # Custom commands appear in the slash_commands list
    async for message in query(prompt="Hello", options={"max_turns": 1}):
        if message.type == "system" and message.subtype == "init":
            # Will include both built-in and custom commands
            print("Available commands:", message.slash_commands)
            # Example: ["/compact", "/clear", "/help", "/refactor", "/security-check"]


asyncio.run(main())
```

---

### OutputFormat Configuration

Source: https://platform.claude.com/docs/en/agent-sdk/python

Configuration schema for structured output validation using JSON Schema. Pass this configuration as a dictionary to the output_format field on ClaudeAgentOptions to enable output validation.

````APIDOC
## OutputFormat Configuration

### Description
Configuration for structured output validation using JSON Schema. This enables validation of agent output against a specified schema definition.

### Usage
Pass this configuration as a `dict` to the `output_format` field on `ClaudeAgentOptions`:

### Request Example
```python
{
    "type": "json_schema",
    "schema": {...}  # Your JSON Schema definition
}
````

### Parameters

#### type

- **Type**: `string`
- **Required**: Yes
- **Description**: Must be `"json_schema"` to enable JSON Schema validation for output.

#### schema

- **Type**: `object`
- **Required**: Yes
- **Description**: JSON Schema definition that specifies the structure and constraints for validating agent output.

### Response Example

```python
{
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "result": {"type": "string"},
            "status": {"type": "string"}
        },
        "required": ["result", "status"]
    }
}
```

````

--------------------------------

### Implement Permission Handler with Unsandboxed Command Support

Source: https://docs.claude.com/en/api/agent-sdk/python

Demonstrates implementing a custom permission handler that validates unsandboxed command requests from the model. The handler checks for dangerouslyDisableSandbox flag, logs requests, and applies custom authorization logic before allowing execution outside the sandbox. Includes required dummy hook to maintain stream state.

```python
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)


async def can_use_tool(
    tool: str, input: dict, context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    # Check if the model is requesting to bypass the sandbox
    if tool == "Bash" and input.get("dangerouslyDisableSandbox"):
        # The model is requesting to run this command outside the sandbox
        print(f"Unsandboxed command requested: {input.get('command')}")

        if is_command_authorized(input.get("command")):
            return PermissionResultAllow()
        return PermissionResultDeny(
            message="Command not authorized for unsandboxed execution"
        )
    return PermissionResultAllow()


# Required: dummy hook keeps the stream open for can_use_tool
async def dummy_hook(input_data, tool_use_id, context):
    return {"continue_": True}


async def prompt_stream():
    yield {
        "type": "user",
        "message": {"role": "user", "content": "Deploy my application"},
    }


async def main():
    async for message in query(
        prompt=prompt_stream(),
        options=ClaudeAgentOptions(
            sandbox={
                "enabled": True,
                "allowUnsandboxedCommands": True,  # Model can request unsandboxed execution
            },
            permission_mode="default",
            can_use_tool=can_use_tool,
            hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[dummy_hook])]},
        ),
    ):
        print(message)
````

---

### Configuring Session Hooks via Setting Sources (Python/TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/hooks

This snippet illustrates how to load `SessionStart` and `SessionEnd` shell command hooks in both Python and TypeScript SDKs. Since these hooks are not directly available as SDK callbacks in Python, they are loaded from `.claude/settings.json` by specifying 'project' in the `setting_sources` or `settingSources` option.

```python
options = ClaudeAgentOptions(
    setting_sources=["project"],  # Loads .claude/settings.json including hooks
)
```

```typescript
const options = {
  settingSources: ["project"], // Loads .claude/settings.json including hooks
};
```

---

### Organize Custom Commands with Namespacing in Filesystem

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

This snippet illustrates how to structure custom command files within subdirectories under `.claude/commands/` for better organization. This approach allows for logical grouping of commands (e.g., `frontend`, `backend`), though the subdirectory name does not affect the command's invocation name.

```bash
.claude/commands/
├── frontend/
│   ├── component.md      # Creates /component (project:frontend)
│   └── style-check.md     # Creates /style-check (project:frontend)
├── backend/
│   ├── api-test.md        # Creates /api-test (project:backend)
│   └── db-migrate.md      # Creates /db-migrate (project:backend)
└── review.md              # Creates /review (project)
```

---

### Configure system-wide HTTP proxy with HTTP_PROXY and HTTPS_PROXY

Source: https://platform.claude.com/docs/en/agent-sdk/secure-deployment

Set HTTP_PROXY and HTTPS_PROXY environment variables to route all HTTP/HTTPS traffic through a proxy system-wide. Claude Code and Agent SDK respect these standard variables. For HTTPS, the proxy creates an encrypted CONNECT tunnel and cannot inspect contents without TLS interception.

```bash
export HTTP_PROXY="http://localhost:8080"
export HTTPS_PROXY="http://localhost:8080"
```

---

### Define PreCompactHookInput TypedDict

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the input structure for PreCompact hook events, triggered before session compaction. Includes the trigger source (manual or automatic) and optional custom instructions for the compaction process.

```python
class PreCompactHookInput(BaseHookInput):
    hook_event_name: Literal["PreCompact"]
    trigger: Literal["manual", "auto"]
    custom_instructions: str | None
```

---

### Define a Basic Custom Command in Markdown

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

This snippet demonstrates how to create a simple custom command by defining its behavior in a Markdown file. The command, named `/refactor`, provides instructions to improve code readability and maintainability.

```markdown
Refactor the selected code to improve readability and maintainability.
Focus on clean code principles and best practices.
```

---

### Client Method: get_server_info()

Source: https://platform.claude.com/docs/en/agent-sdk/python

Retrieves server information, including the current session ID and available capabilities. This is useful for understanding the active session's context.

````APIDOC
## Client Method: get_server_info()

### Description
Get server information including session ID and capabilities. This provides details about the current connection and what features are supported.

### Method
get_server_info

### Parameters
#### Arguments
- **None**

### Request Example
```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient

async def main():
    async with ClaudeSDKClient() as client:
        await client.connect()
        info = await client.get_server_info()
        print(f"Server Info: {info}")

asyncio.run(main())
````

### Response

#### Return Value

- **object** - An object containing server-related information.

#### Response Example

```json
{
  "session_id": "sess_01H01J01K01L01M01N01P",
  "capabilities": ["streaming_input", "file_checkpointing", "tool_use"],
  "connected_at": "2024-01-01T12:00:00Z"
}
```

````

--------------------------------

### One-shot Prompt with V1 TypeScript SDK

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Send a single-turn query using the V1 SDK query() function with an async generator pattern. This demonstrates the difference between V1 and V2 approaches for simple queries.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

const q = query({
  prompt: "What is 2 + 2?",
  options: { model: "claude-opus-4-6" }
});

for await (const msg of q) {
  if (msg.type === "result") {
    console.log(msg.result);
  }
}
````

---

### Task Tool Input/Output Schema

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the input and output structure for the Task tool, which delegates work to specialized subagents. Input requires a task description, prompt, and subagent type. Output includes the result, token usage statistics, cost, and execution duration.

```json
{
  "input": {
    "description": "str",
    "prompt": "str",
    "subagent_type": "str"
  },
  "output": {
    "result": "str",
    "usage": "dict | None",
    "total_cost_usd": "float | None",
    "duration_ms": "int | None"
  }
}
```

---

### POST /tools/ExitPlanMode

Source: https://docs.claude.com/en/api/agent-sdk/python

Submits a plan for user approval and exits plan mode. This tool presents a plan to the user and waits for their approval decision before proceeding.

````APIDOC
## POST /tools/ExitPlanMode

### Description
Submits a plan for user approval and exits plan mode. Presents the plan to the user and waits for their approval decision.

### Method
POST

### Endpoint
/tools/ExitPlanMode

### Tool Name
ExitPlanMode

### Parameters
#### Request Body
- **plan** (string) - Required - The plan to run by the user for approval

### Request Example
```json
{
  "plan": "Create a new file, write content to it, and execute a test script"
}
````

### Response

#### Success Response (200)

- **message** (string) - Confirmation message
- **approved** (boolean | null) - Whether user approved the plan (null if no response)

#### Response Example

```json
{
  "message": "Plan submitted for user approval",
  "approved": true
}
```

````

--------------------------------

### List sessions - Discover past sessions with metadata

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Discovers and lists past sessions with light metadata. Can filter by project directory or list sessions across all projects. Returns session information including ID, summary, modification time, and git branch.

```typescript
function listSessions(options?: ListSessionsOptions): Promise<SDKSessionInfo[]>;
````

---

### Grep Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the input and output structures for the `Grep` tool. This tool searches for patterns within files, similar to the Unix `grep` command. Inputs include a regular expression pattern and various options for search scope, output format, and context lines. Outputs vary based on the output mode, providing either detailed matches, a list of files with matches, or a count.

```python
{
    "pattern": str,  # The regular expression pattern
    "path": str | None,  # File or directory to search in
    "glob": str | None,  # Glob pattern to filter files
    "type": str | None,  # File type to search
    "output_mode": str | None,  # "content", "files_with_matches", or "count"
    "-i": bool | None,  # Case insensitive search
    "-n": bool | None,  # Show line numbers
    "-B": int | None,  # Lines to show before each match
    "-A": int | None,  # Lines to show after each match
    "-C": int | None,  # Lines to show before and after
    "head_limit": int | None,  # Limit output to first N lines/entries
    "multiline": bool | None  # Enable multiline mode
}
```

```python
{
    "matches": [
        {
            "file": str,
            "line_number": int | None,
            "line": str,
            "before_context": list[str] | None,
            "after_context": list[str] | None
        }
    ],
    "total_matches": int
}
```

```python
{
    "files": list[str],  # Files containing matches
    "count": int  # Number of files with matches
}
```

---

### Discover Available Slash Commands in Claude Agent SDK (TypeScript/Python)

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

This snippet demonstrates how to retrieve the list of available slash commands from the Claude Agent SDK. It processes the system initialization message (`init` subtype) received after a query to extract and log the `slash_commands` array.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Hello Claude",
  options: { maxTurns: 1 },
})) {
  if (message.type === "system" && message.subtype === "init") {
    console.log("Available slash commands:", message.slash_commands);
    // Example output: ["/compact", "/clear", "/help"]
  }
}
```

```python
import asyncio
from claude_agent_sdk import query


async def main():
    async for message in query(prompt="Hello Claude", options={"max_turns": 1}):
        if message.type == "system" and message.subtype == "init":
            print("Available slash commands:", message.slash_commands)
            # Example output: ["/compact", "/clear", "/help"]


asyncio.run(main())
```

---

### Define Agent Configuration with AgentDefinition

Source: https://docs.claude.com/en/api/agent-sdk/python

Dataclass for configuring subagents programmatically with description, system prompt, optional tool restrictions, and model selection. Supports model inheritance from parent agent when not specified.

```python
@dataclass
class AgentDefinition:
    description: str
    prompt: str
    tools: list[str] | None = None
    model: Literal["sonnet", "opus", "haiku", "inherit"] | None = None
```

---

### Method: Transport.connect()

Source: https://docs.claude.com/en/api/agent-sdk/python

Connects the transport mechanism and prepares it for sending and receiving communication. This method should establish any necessary underlying connections.

````APIDOC
## METHOD Transport.connect()

### Description
Connects the transport mechanism and prepares it for sending and receiving communication. This method should establish any necessary underlying connections.

### Method
`async`

### Endpoint
`Transport.connect`

### Parameters
#### Method Parameters
- No parameters.

### Request Example
```python
# Assuming 'my_transport_instance' is an instance of a class implementing Transport
await my_transport_instance.connect()
````

### Response

#### Success Response (200)

- Returns `None` upon successful connection.

#### Response Example

```json
{}
```

````

--------------------------------

### Provide Tool Permission Context Information

Source: https://docs.claude.com/en/api/agent-sdk/python

Dataclass containing context information passed to tool permission callbacks, including optional abort signal support and permission update suggestions from the CLI.

```python
@dataclass
class ToolPermissionContext:
    signal: Any | None = None
    suggestions: list[PermissionUpdate] = field(default_factory=list)
````

---

### Define input schema options for Python SDK tool

Source: https://docs.claude.com/en/api/agent-sdk/python

These snippets illustrate two ways to define the input schema for a custom tool. The first uses a simple Python dictionary for basic type mapping, while the second demonstrates the use of JSON Schema for more complex validation rules, including properties, types, and required fields. Both methods allow specifying the expected arguments for tool functions.

```python
{"text": str, "count": int, "enabled": bool}
```

```json
{
  "type": "object",
  "properties": {
    "text": { "type": "string" },
    "count": { "type": "integer", "minimum": 0 }
  },
  "required": ["text"]
}
```

---

### TypeScript Claude Agent SDK: Handling `AskUserQuestion` Tool and User Input

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This comprehensive TypeScript snippet illustrates how to intercept and handle the `AskUserQuestion` tool using the `canUseTool` callback in the Claude Agent SDK. It includes helper functions for prompting the user via the terminal, parsing their responses (single or multi-select), and formatting the answers to be returned to the agent, enabling interactive user input for agent queries.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";
import * as readline from "readline/promises";

// Helper to prompt user for input in the terminal
async function prompt(question: string): Promise<string> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  const answer = await rl.question(question);
  rl.close();
  return answer;
}

// Parse user input as option number(s) or free text
function parseResponse(response: string, options: any[]): string {
  const indices = response.split(",").map((s) => parseInt(s.trim()) - 1);
  const labels = indices
    .filter((i) => !isNaN(i) && i >= 0 && i < options.length)
    .map((i) => options[i].label);
  return labels.length > 0 ? labels.join(", ") : response;
}

// Display Claude's questions and collect user answers
async function handleAskUserQuestion(input: any) {
  const answers: Record<string, string> = {};

  for (const q of input.questions) {
    console.log(`\n${q.header}: ${q.question}`);

    const options = q.options;
    options.forEach((opt: any, i: number) => {
      console.log(`  ${i + 1}. ${opt.label} - ${opt.description}`);
    });
    if (q.multiSelect) {
      console.log(
        "  (Enter numbers separated by commas, or type your own answer)",
      );
    } else {
      console.log("  (Enter a number, or type your own answer)");
    }

    const response = (await prompt("Your choice: ")).trim();
    answers[q.question] = parseResponse(response, options);
  }

  // Return the answers to Claude (must include original questions)
  return {
    behavior: "allow",
    updatedInput: { questions: input.questions, answers },
  };
}

async function main() {
  for await (const message of query({
    prompt: "Help me decide on the tech stack for a new mobile app",
    options: {
      canUseTool: async (toolName, input) => {
        // Route AskUserQuestion to our question handler
        if (toolName === "AskUserQuestion") {
          return handleAskUserQuestion(input);
        }
        // Auto-approve other tools for this example
        return { behavior: "allow", updatedInput: input };
      },
    },
  })) {
    if ("result" in message) console.log(message.result);
  }
}

main();
```

---

### Client Method: query(prompt, session_id)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Sends a new request to Claude in streaming mode. This is the primary method for sending user input and continuing a conversation within an established session.

````APIDOC
## Client Method: query(prompt, session_id)

### Description
Send a new request in streaming mode. This method is used to send user messages or input streams to Claude.

### Method
query

### Parameters
#### Arguments
- **prompt** (string | async generator) - Required - The user's message as a string or an asynchronous generator yielding message objects for streaming input.
- **session_id** (string) - Optional - A specific session ID to associate the query with. If not provided, the current session is used.

### Request Example
```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient

async def main():
    async with ClaudeSDKClient() as client:
        await client.query("What's the capital of France?")
        # Example with streaming input:
        # async def message_stream():
        #     yield {"type": "user", "message": {"role": "user", "content": "Analyze:"}}
        #     await asyncio.sleep(0.1)
        #     yield {"type": "user", "message": {"role": "user", "content": "Data point 1"}}
        # await client.query(message_stream())

asyncio.run(main())
````

### Response

#### Return Value

- **None** - This method initiates the query and does not return a direct value. Responses are received via `receive_messages()` or `receive_response()`.

#### Response Example

```json
null
```

````

--------------------------------

### Single Message Query with Session Management

Source: https://platform.claude.com/docs/en/agent-sdk/streaming-vs-single-mode

Implements stateless one-shot queries using the query() function with optional session continuation. Supports tool specification and response streaming without requiring message generators. Ideal for lambda functions and stateless environments.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Simple one-shot query
for await (const message of query({
  prompt: "Explain the authentication flow",
  options: {
    maxTurns: 1,
    allowedTools: ["Read", "Grep"]
  }
})) {
  if (message.type === "result") {
    console.log(message.result);
  }
}

// Continue conversation with session management
for await (const message of query({
  prompt: "Now explain the authorization process",
  options: {
    continue: true,
    maxTurns: 1
  }
})) {
  if (message.type === "result") {
    console.log(message.result);
  }
}
````

```python
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
import asyncio


async def single_message_example():
    # Simple one-shot query using query() function
    async for message in query(
        prompt="Explain the authentication flow",
        options=ClaudeAgentOptions(max_turns=1, allowed_tools=["Read", "Grep"]),
    ):
        if isinstance(message, ResultMessage):
            print(message.result)

    # Continue conversation with session management
    async for message in query(
        prompt="Now explain the authorization process",
        options=ClaudeAgentOptions(continue_conversation=True, max_turns=1),
    ):
        if isinstance(message, ResultMessage):
            print(message.result)


asyncio.run(single_message_example())
```

---

### Configure multiple local plugin sources in Agent SDK (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/plugins

This TypeScript configuration snippet shows how to define an array of plugin objects, each specifying a `local` type and its corresponding file system `path`. This allows the Agent SDK to load plugins from different directories, such as a project-specific local plugin and a shared custom plugin from a user's home directory.

```typescript
plugins: [
  { type: "local", path: "./local-plugin" },
  { type: "local", path: "~/.claude/custom-plugins/shared-plugin" },
];
```

---

### MCP Server Configuration

Source: https://docs.claude.com/en/api/agent-sdk/python

Configuration types for Model Context Protocol (MCP) servers. Supports multiple server types including stdio, SSE, HTTP, and SDK-based servers for integrating external tools and resources.

````APIDOC
## McpServerConfig

### Description
Union type for MCP server configurations. Supports multiple server types for different deployment scenarios.

### Type Definition
```python
McpServerConfig = (
    McpStdioServerConfig | McpSSEServerConfig | McpHttpServerConfig | McpSdkServerConfig
)
````

### McpStdioServerConfig

Configuration for stdio-based MCP servers.

```python
class McpStdioServerConfig(TypedDict):
    type: NotRequired[Literal["stdio"]]
    command: str
    args: NotRequired[list[str]]
    env: NotRequired[dict[str, str]]
```

### McpSSEServerConfig

Configuration for Server-Sent Events (SSE) based MCP servers.

```python
class McpSSEServerConfig(TypedDict):
    type: Literal["sse"]
    url: str
    headers: NotRequired[dict[str, str]]
```

### McpHttpServerConfig

Configuration for HTTP-based MCP servers.

```python
class McpHttpServerConfig(TypedDict):
    type: Literal["http"]
    url: str
    headers: NotRequired[dict[str, str]]
```

### McpSdkServerConfig

Configuration for SDK MCP servers created with `create_sdk_mcp_server()`.

```python
class McpSdkServerConfig(TypedDict):
    type: Literal["sdk"]
    name: str
    instance: Any
```

````

--------------------------------

### Store Multiple Checkpoints for Granular Rewinding with Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/file-checkpointing

This pattern illustrates how to store multiple checkpoint UUIDs, potentially with associated metadata, to enable more granular control over state restoration. Instead of just rewinding to the last state, this approach allows developers to select and revert to any specific previous point in the agent's history, useful for selectively undoing changes across multiple turns.

```python
import asyncio
from dataclasses import dataclass
from datetime import datetime
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    UserMessage,
    ResultMessage,
)
````

---

### ToolPermissionContext

Source: https://docs.claude.com/en/api/agent-sdk/python

Provides additional context information to tool permission callback functions, including future abort signal support and permission update suggestions.

````APIDOC
## ToolPermissionContext

### Description
Context information passed to tool permission callbacks.

### Definition
```python
@dataclass
class ToolPermissionContext:
    signal: Any | None = None  # Future: abort signal support
    suggestions: list[PermissionUpdate] = field(default_factory=list)
````

### Fields

- **signal** (Any | None) - Reserved for future abort signal support
- **suggestions** (list[PermissionUpdate]) - Permission update suggestions from the CLI

````

--------------------------------

### query()

Source: https://docs.claude.com/en/api/agent-sdk/python

The `query()` function creates a new, independent session for each interaction with Claude Code. It returns an async iterator yielding messages, suitable for one-off tasks without conversation history.

```APIDOC
## query()

### Description
Creates a new session for each interaction with Claude Code. Returns an async iterator that yields messages as they arrive. Each call to `query()` starts fresh with no memory of previous interactions.

### Method
SDK Function

### Endpoint
N/A

### Parameters
#### Path Parameters
N/A

#### Query Parameters
N/A

#### Request Body
- **prompt** (`str | AsyncIterable[dict[str, Any]]`) - Required - The input prompt as a string or async iterable for streaming mode
- **options** (`ClaudeAgentOptions | None`) - Optional - Optional configuration object (defaults to `ClaudeAgentOptions()` if None)
- **transport** (`Transport | None`) - Optional - Optional custom transport for communicating with the CLI process

### Request Example
N/A (parameters are direct arguments)

### Response
#### Success Response (Returns)
- `AsyncIterator[Message]` - An async iterator that yields messages from the conversation.

#### Response Example
```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are an expert Python developer",
        permission_mode="acceptEdits",
        cwd="/home/user/project",
    )

    async for message in query(prompt="Create a Python web server", options=options):
        print(message)


asyncio.run(main())
````

````

--------------------------------

### Resume Session and Rewind Files in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/file-checkpointing

Resumes an agent session with an empty prompt to restore the connection, then calls rewindFiles() to restore files to their checkpoint state. Iterates through the response stream and breaks after the first message to execute the rewind operation.

```typescript
const rewindQuery = query({
  prompt: "",
  options: { ...opts, resume: sessionId }
});

for await (const msg of rewindQuery) {
  await rewindQuery.rewindFiles(checkpointId);
  break;
}
````

---

### Define McpStdioServerConfig for Claude Agent SDK (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This `TypedDict` configures an MCP server that communicates via standard I/O. It specifies the command to execute, optional arguments, and environment variables for the server process. The `type` field is optional for backward compatibility.

```python
class McpStdioServerConfig(TypedDict):
    type: NotRequired[Literal["stdio"]]  # Optional for backwards compatibility
    command: str
    args: NotRequired[list[str]]
    env: NotRequired[dict[str, str]]
```

---

### Class: SdkMcpTool Definition

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the structure for creating a Multi-Component Platform (MCP) tool using the `@tool` decorator, specifying its name, description, input schema, handler, and optional annotations.

````APIDOC
## CLASS SdkMcpTool

### Description
Definition for an SDK MCP tool created with the `@tool` decorator. This dataclass specifies the structure and required components for integrating a tool within the SDK's Multi-Component Platform (MCP) framework.

### Method
`dataclass`

### Endpoint
`SdkMcpTool`

### Parameters
#### Class Properties
- **name** (`str`) - Required - Unique identifier for the tool.
- **description** (`str`) - Required - Human-readable description of the tool's functionality.
- **input_schema** (`type[T] | dict[str, Any]`) - Required - Schema used for validating the input to the tool's handler.
- **handler** (`Callable[[T], Awaitable[dict[str, Any]]]`) - Required - An asynchronous function responsible for executing the tool's logic.
- **annotations** (`ToolAnnotations | None`) - Optional - Optional MCP tool annotations, such as `readOnlyHint`, `destructiveHint`, or `openWorldHint`, sourced from `mcp.types`.

### Request Example
```python
# Example of an SdkMcpTool definition
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")

@dataclass
class MyToolInput:
    query: str

async def my_tool_handler(input: MyToolInput) -> dict[str, Any]:
    return {"result": f"Processed query: {input.query}"}

# Assuming SdkMcpTool and ToolAnnotations are imported or defined
# from claude_agent_sdk import SdkMcpTool, ToolAnnotations

# my_sdk_tool = SdkMcpTool(
#     name="my_example_tool",
#     description="A simple example tool.",
#     input_schema=MyToolInput,
#     handler=my_tool_handler,
#     annotations=None
# )
````

### Response

#### Definition Structure

- **name** (`str`) - Unique identifier.
- **description** (`str`) - Human-readable description.
- **input_schema** (`type[T] | dict[str, Any]`) - Input validation schema.
- **handler** (`Callable[[T], Awaitable[dict[str, Any]]]`) - Execution function.
- **annotations** (`ToolAnnotations | None`) - Optional annotations.

#### Response Example

```json
{
  "status": "SdkMcpTool class defined",
  "details": "This object represents the structure for creating a new tool within the MCP framework."
}
```

````

--------------------------------

### Extend Claude Agent SDK System Prompt with Append

Source: https://platform.claude.com/docs/en/agent-sdk/modifying-system-prompts

This snippet demonstrates how to customize the AI's system prompt by appending additional instructions to a pre-defined preset, such as 'claude_code'. By using the 'systemPrompt' option with an 'append' property, users can add specific directives (e.g., requiring docstrings and type hints) while retaining the core functionality and context provided by the base preset. This allows for fine-grained control over the AI's behavior for specific tasks.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

const messages = [];

for await (const message of query({
  prompt: "Help me write a Python function to calculate fibonacci numbers",
  options: {
    systemPrompt: {
      type: "preset",
      preset: "claude_code",
      append: "Always include detailed docstrings and type hints in Python code."
    }
  }
})) {
  messages.push(message);
  if (message.type === "assistant") {
    console.log(message.message.content);
  }
}
````

```python
from claude_agent_sdk import query, ClaudeAgentOptions

messages = []

async for message in query(
    prompt="Help me write a Python function to calculate fibonacci numbers",
    options=ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": "Always include detailed docstrings and type hints in Python code.",
        }
    ),
):
    messages.append(message)
    if message.type == "assistant":
        print(message.message.content)
```

---

### Create Custom Output Styles for Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/modifying-system-prompts

This functionality allows users to programmatically define and save custom output styles for the Claude Agent SDK. It involves creating a function that takes a name, description, and prompt, then writes this information into a Markdown file within a designated '.claude/output-styles' directory. These styles can later be activated via CLI commands or SDK settings.

```typescript
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";
import { homedir } from "os";

async function createOutputStyle(
  name: string,
  description: string,
  prompt: string,
) {
  // User-level: ~/.claude/output-styles
  // Project-level: .claude/output-styles
  const outputStylesDir = join(homedir(), ".claude", "output-styles");

  await mkdir(outputStylesDir, { recursive: true });

  const content = `---
name: ${name}
description: ${description}
---

${prompt}`;

  const filePath = join(
    outputStylesDir,
    `${name.toLowerCase().replace(/\s+/g, "-")}.md`,
  );
  await writeFile(filePath, content, "utf-8");
}

// Example: Create a code review specialist
await createOutputStyle(
  "Code Reviewer",
  "Thorough code review assistant",
  `You are an expert code reviewer.

For every code submission:
1. Check for bugs and security issues
2. Evaluate performance
3. Suggest improvements
4. Rate code quality (1-10)`,
);
```

```python
from pathlib import Path


async def create_output_style(name: str, description: str, prompt: str):
    # User-level: ~/.claude/output-styles
    # Project-level: .claude/output-styles
    output_styles_dir = Path.home() / ".claude" / "output-styles"

    output_styles_dir.mkdir(parents=True, exist_ok=True)

    content = f"""---
name: {name}
description: {description}
---

{prompt}"""

    file_name = name.lower().replace(" ", "-") + ".md"
    file_path = output_styles_dir / file_name
    file_path.write_text(content, encoding="utf-8")


# Example: Create a code review specialist
await create_output_style(
    "Code Reviewer",
    "Thorough code review assistant",
    """You are an expert code reviewer.

For every code submission:
1. Check for bugs and security issues
2. Evaluate performance
3. Suggest improvements
4. Rate code quality (1-10)""",
)
```

---

### Grep Tool

Source: https://platform.claude.com/docs/en/agent-sdk/python

Searches for patterns using regular expressions within files or directories. Supports multiple output modes (content, files_with_matches, count) and context display options for flexible text searching.

````APIDOC
## Grep Tool

### Description
Searches for regular expression patterns in files with support for context display, case-insensitive matching, and multiple output modes.

### Tool Name
`Grep`

### Input Parameters
- **pattern** (string) - Required - The regular expression pattern
- **path** (string | null) - Optional - File or directory to search in
- **glob** (string | null) - Optional - Glob pattern to filter files
- **type** (string | null) - Optional - File type to search
- **output_mode** (string | null) - Optional - "content", "files_with_matches", or "count"
- **-i** (boolean | null) - Optional - Case insensitive search
- **-n** (boolean | null) - Optional - Show line numbers
- **-B** (integer | null) - Optional - Lines to show before each match
- **-A** (integer | null) - Optional - Lines to show after each match
- **-C** (integer | null) - Optional - Lines to show before and after
- **head_limit** (integer | null) - Optional - Limit output to first N lines/entries
- **multiline** (boolean | null) - Optional - Enable multiline mode

### Request Example
```python
{
    "pattern": "error",
    "path": "/var/log",
    "output_mode": "content",
    "-i": true,
    "-n": true,
    "-A": 2
}
````

### Response (Content Mode)

- **matches** (array) - Array of match objects
  - **file** (string) - File path containing the match
  - **line_number** (integer | null) - Line number of the match
  - **line** (string) - The matching line
  - **before_context** (array[string] | null) - Lines before the match
  - **after_context** (array[string] | null) - Lines after the match
- **total_matches** (integer) - Total number of matches found

### Response (Files with Matches Mode)

- **files** (array[string]) - Files containing matches
- **count** (integer) - Number of files with matches

### Response Example (Content Mode)

```python
{
    "matches": [
        {
            "file": "/var/log/app.log",
            "line_number": 42,
            "line": "ERROR: Connection failed",
            "before_context": ["INFO: Starting connection"],
            "after_context": ["INFO: Retrying connection"]
        }
    ],
    "total_matches": 1
}
```

````

--------------------------------

### Execute Queries with File Operations in Python

Source: https://docs.claude.com/en/api/agent-sdk/python

Use the query function to execute agent tasks with file operation tools (Read, Write, Bash). Accepts ClaudeAgentOptions to configure allowed tools, permission mode, and working directory. Returns an async iterator of messages that can be inspected for tool usage and results.

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ToolUseBlock
import asyncio


async def create_project():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits",
        cwd="/home/user/project",
    )

    async for message in query(
        prompt="Create a Python project structure with setup.py", options=options
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"Using tool: {block.name}")


asyncio.run(create_project())
````

---

### Define McpSdkServerConfig for Claude Agent SDK (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This `TypedDict` defines the configuration for SDK MCP (Multi-Channel Protocol) servers. It is used when creating servers via `create_sdk_mcp_server()`. The configuration includes the server type, a unique name, and the server instance.

```python
class McpSdkServerConfig(TypedDict):
    type: Literal["sdk"]
    name: str
    instance: Any  # MCP Server instance
```

---

### PreCompactHookInput - Pre-Compaction Hook

Source: https://platform.claude.com/docs/en/agent-sdk/python

Provides input data for PreCompact hook events, which are triggered before transcript compaction. Includes trigger type and optional custom instructions.

````APIDOC
## PreCompactHookInput

### Description
Input data for PreCompact hook events. Triggered before transcript compaction, allowing customization of the compaction process.

### Structure
```python
class PreCompactHookInput(BaseHookInput):
    hook_event_name: Literal["PreCompact"]
    trigger: Literal["manual", "auto"]
    custom_instructions: str | None
````

### Fields

- **hook_event_name** (Literal["PreCompact"]) - Required - Always "PreCompact"
- **trigger** (Literal["manual", "auto"]) - Required - What triggered the compaction (manual or automatic)
- **custom_instructions** (str | None) - Required - Custom instructions for compaction, or None if not provided

### Inherits From

- BaseHookInput (session_id, transcript_path, cwd, permission_mode)

````

--------------------------------

### WebSearch Tool - Search Engine Integration with Domain Filtering

Source: https://docs.claude.com/en/api/agent-sdk/python

Performs web searches with optional domain whitelisting and blacklisting. Returns array of search results with title, URL, snippet, and optional metadata. Supports filtering results to specific domains or excluding particular domains.

```json
{
  "query": "str",
  "allowed_domains": "list[str] | None",
  "blocked_domains": "list[str] | None"
}
````

```json
{
  "results": [
    {
      "title": "str",
      "url": "str",
      "snippet": "str",
      "metadata": "dict | None"
    }
  ],
  "total_results": "int",
  "query": "str"
}
```

---

### SDKControlInitializeResponse Type

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Return type of the initializationResult() method. Contains comprehensive session initialization data including available commands, agents, models, and account information.

````APIDOC
## SDKControlInitializeResponse

### Description
Return type of `initializationResult()`. Contains session initialization data with information about available commands, agents, models, output styles, and account details.

### Type Definition
```typescript
type SDKControlInitializeResponse = {
  commands: SlashCommand[];
  agents: AgentInfo[];
  output_style: string;
  available_output_styles: string[];
  models: ModelInfo[];
  account: AccountInfo;
};
````

### Properties

#### commands

- **Type**: `SlashCommand[]`
- **Description**: Array of available slash commands that can be used in the session

#### agents

- **Type**: `AgentInfo[]`
- **Description**: Array of available subagents that can be invoked

#### output_style

- **Type**: `string`
- **Description**: Current output style configuration for the session

#### available_output_styles

- **Type**: `string[]`
- **Description**: Array of all available output style options

#### models

- **Type**: `ModelInfo[]`
- **Description**: Array of available models with their display information and capabilities

#### account

- **Type**: `AccountInfo`
- **Description**: Account information including user details and subscription status

````

--------------------------------

### Stream Dynamic Input Messages to Claude SDK

Source: https://docs.claude.com/en/api/agent-sdk/python

Demonstrates streaming user messages asynchronously to Claude using an async generator function. Allows progressive message delivery with delays between inputs, useful for processing large datasets or real-time data feeds. The session context is maintained across the streamed input and follow-up queries.

```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient


async def message_stream():
    """Generate messages dynamically."""
    yield {
        "type": "user",
        "message": {"role": "user", "content": "Analyze the following data:"},
    }
    await asyncio.sleep(0.5)
    yield {
        "type": "user",
        "message": {"role": "user", "content": "Temperature: 25°C, Humidity: 60%"},
    }
    await asyncio.sleep(0.5)
    yield {
        "type": "user",
        "message": {"role": "user", "content": "What patterns do you see?"},
    }


async def main():
    async with ClaudeSDKClient() as client:
        # Stream input to Claude
        await client.query(message_stream())

        # Process response
        async for message in client.receive_response():
            print(message)

        # Follow-up in same session
        await client.query("Should we be concerned about these readings?")

        async for message in client.receive_response():
            print(message)


asyncio.run(main())
````

---

### Customize Claude Agent SDK System Prompt with Session-Specific Instructions

Source: https://platform.claude.com/docs/en/agent-sdk/modifying-system-prompts

This code snippet illustrates how to dynamically append additional instructions to an active system prompt preset within the Claude Agent SDK. By using the `systemPrompt.append` option, you can provide session-specific focus areas, such as prioritizing OAuth 2.0 compliance or token storage security for a code review, without altering the base preset. This allows for flexible and context-aware agent behavior.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Assuming "Code Reviewer" output style is active (via /output-style)
// Add session-specific focus areas
const messages = [];

for await (const message of query({
  prompt: "Review this authentication module",
  options: {
    systemPrompt: {
      type: "preset",
      preset: "claude_code",
      append: `
        For this review, prioritize:
        - OAuth 2.0 compliance
        - Token storage security
        - Session management
      `,
    },
  },
})) {
  messages.push(message);
}
```

```python
from claude_agent_sdk import query, ClaudeAgentOptions

# Assuming "Code Reviewer" output style is active (via /output-style)
# Add session-specific focus areas
messages = []

async for message in query(
    prompt="Review this authentication module",
    options=ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": """
            For this review, prioritize:
            - OAuth 2.0 compliance
            - Token storage security
            - Session management
            """,
        }
    ),
):
    messages.append(message)
```

---

### Define Configuration for Matching Hooks (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the `HookMatcher` dataclass for configuring how hooks are matched to specific events or tools. It allows specifying a `matcher` string (e.g., a tool name or regex pattern), a list of `hooks` (callbacks) to execute, and an optional `timeout` for the collective execution of those hooks.

```python
@dataclass
class HookMatcher:
    matcher: str | None = (
        None  # Tool name or pattern to match (e.g., "Bash", "Write|Edit")
    )
    hooks: list[HookCallback] = field(
        default_factory=list
    )  # List of callbacks to execute
    timeout: float | None = (
        None  # Timeout in seconds for all hooks in this matcher (default: 60)
    )
```

---

### Mounting Read-Only Code Directory for Agent Analysis (Docker)

Source: https://platform.claude.com/docs/en/agent-sdk/secure-deployment

This snippet demonstrates how to mount a directory containing code into a Docker container in read-only mode. This prevents the agent from modifying the source code while still allowing it to analyze the files. It's crucial to be aware of sensitive files (like credentials) that might be exposed even with read-only access.

```bash
docker run -v /path/to/code:/workspace:ro agent-image
```

---

### Configure Claude Agent SDK for file checkpointing

Source: https://platform.claude.com/docs/en/agent-sdk/file-checkpointing

This snippet illustrates how to configure the Claude Agent SDK to enable file checkpointing and ensure that checkpoint UUIDs are received in the response stream. It shows the necessary options for both Python and TypeScript to track file changes and capture user message UUIDs.

```python
options = ClaudeAgentOptions(
    enable_file_checkpointing=True,
    permission_mode="acceptEdits",
    extra_args={"replay-user-messages": None},
)

async with ClaudeSDKClient(options) as client:
    await client.query("Refactor the authentication module")
```

```typescript
const response = query({
  prompt: "Refactor the authentication module",
  options: {
    enableFileCheckpointing: true,
    permissionMode: "acceptEdits" as const,
    extraArgs: { "replay-user-messages": null },
  },
});
```

---

### SdkBeta Type Definition

Source: https://docs.claude.com/en/api/agent-sdk/python

Literal type for SDK beta features. Use with the `betas` field in `ClaudeAgentOptions` to enable experimental features and access new capabilities.

````APIDOC
## SdkBeta

### Description
Literal type for SDK beta features. Use with the `betas` field in `ClaudeAgentOptions` to enable beta features.

### Type Definition
```python
SdkBeta = Literal["context-1m-2025-08-07"]
````

### Usage

Pass beta feature identifiers to the `betas` field in `ClaudeAgentOptions` to enable experimental features.

````

--------------------------------

### Execute Namespaced Plugin Commands with Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/plugins

This snippet demonstrates how to invoke a custom command from a locally loaded plugin using its namespaced format (plugin-name:command-name) within the Claude Agent SDK. It shows how to pass plugin configuration to the query function and process the assistant's response.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Load a plugin with a custom /greet command
for await (const message of query({
  prompt: "/my-plugin:greet", // Use plugin command with namespace
  options: {
    plugins: [{ type: "local", path: "./my-plugin" }]
  }
})) {
  // Claude executes the custom greeting command from the plugin
  if (message.type === "assistant") {
    console.log(message.content);
  }
}
````

```python
import asyncio
from claude_agent_sdk import query, AssistantMessage, TextBlock


async def main():
    # Load a plugin with a custom /greet command
    async for message in query(
        prompt="/demo-plugin:greet",  # Use plugin command with namespace
        options={"plugins": [{"type": "local", "path": "./plugins/demo-plugin"}]},
    ):
        # Claude executes the custom greeting command from the plugin
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")


asyncio.run(main())
```

---

### ClaudeAgentOptions - Core Configuration Parameters

Source: https://platform.claude.com/docs/en/agent-sdk/python

Configuration parameters for ClaudeAgentOptions including tool permissions, hooks, user identification, and message streaming settings. These parameters control the fundamental behavior of the Claude Agent SDK.

```APIDOC
## ClaudeAgentOptions Configuration Parameters

### Description
Core configuration options for initializing and controlling Claude Agent SDK behavior, including tool permissions, event hooks, user context, and message streaming preferences.

### Parameters

#### can_use_tool
- **Type**: `CanUseTool | None`
- **Default**: `None`
- **Required**: No
- **Description**: Tool permission callback function that controls which tools can be used. See Permission types documentation for implementation details.

#### hooks
- **Type**: `dict[HookEvent, list[HookMatcher]] | None`
- **Default**: `None`
- **Required**: No
- **Description**: Hook configurations for intercepting and handling specific events during agent execution.

#### user
- **Type**: `str | None`
- **Default**: `None`
- **Required**: No
- **Description**: User identifier to associate with the current session or request.

#### include_partial_messages
- **Type**: `bool`
- **Default**: `False`
- **Required**: No
- **Description**: When enabled, includes partial message streaming events. StreamEvent messages are yielded during streaming operations.

#### fork_session
- **Type**: `bool`
- **Default**: `False`
- **Required**: No
- **Description**: When resuming with `resume`, fork to a new session ID instead of continuing the original session.

#### agents
- **Type**: `dict[str, AgentDefinition] | None`
- **Default**: `None`
- **Required**: No
- **Description**: Programmatically defined subagents that can be invoked during execution.

#### plugins
- **Type**: `list[SdkPluginConfig]`
- **Default**: `[]`
- **Required**: No
- **Description**: Load custom plugins from local paths. Refer to Plugins documentation for configuration details.

#### sandbox
- **Type**: `SandboxSettings | None`
- **Default**: `None`
- **Required**: No
- **Description**: Configure sandbox behavior programmatically. See Sandbox settings documentation for available options.

#### setting_sources
- **Type**: `list[SettingSource] | None`
- **Default**: `None` (no settings loaded)
- **Required**: No
- **Description**: Control which filesystem settings to load. Must include `"project"` to load CLAUDE.md files.

#### max_thinking_tokens
- **Type**: `int | None`
- **Default**: `None`
- **Required**: No
- **Description**: Deprecated - Maximum tokens for thinking blocks. Use `thinking` parameter instead.

#### thinking
- **Type**: `ThinkingConfig | None`
- **Default**: `None`
- **Required**: No
- **Description**: Controls extended thinking behavior. Takes precedence over `max_thinking_tokens`.

#### effort
- **Type**: `Literal["low", "medium", "high", "max"] | None`
- **Default**: `None`
- **Required**: No
- **Description**: Effort level that controls the depth and intensity of thinking operations.
```

---

### Bash Tool

Source: https://platform.claude.com/docs/en/agent-sdk/python

Executes bash commands with optional timeout and background execution support. Returns command output, exit code, and execution status information.

````APIDOC
## Bash Tool

### Description
Executes bash commands with support for timeouts and background execution.

### Tool Name
`Bash`

### Input Parameters
- **command** (str) - Required - The command to execute
- **timeout** (int | None) - Optional - Timeout in milliseconds (max 600000)
- **description** (str | None) - Optional - Clear, concise description (5-10 words)
- **run_in_background** (bool | None) - Optional - Set to true to run in background

### Request Example
```python
{
    "command": "ls -la /home/user",
    "timeout": 5000,
    "description": "List directory contents",
    "run_in_background": false
}
````

### Response

#### Success Response (200)

- **output** (str) - Combined stdout and stderr output
- **exitCode** (int) - Exit code of the command
- **killed** (bool | None) - Whether command was killed due to timeout
- **shellId** (str | None) - Shell ID for background processes

#### Response Example

```python
{
    "output": "total 48\ndrwxr-xr-x 5 user group 4096 Jan 15 10:30 .\ndrwxr-xr-x 3 root root 4096 Jan 10 08:20 ..",
    "exitCode": 0,
    "killed": false,
    "shellId": null
}
```

````

--------------------------------

### Implement API Gateway Tool for Authenticated Requests

Source: https://platform.claude.com/docs/en/agent-sdk/custom-tools

This tool allows an SDK server to make authenticated HTTP requests to predefined external services such as Stripe, GitHub, OpenAI, and Slack. It takes parameters like the target service, API endpoint, HTTP method, and optional request body or query parameters, then constructs and sends the request, returning the JSON response. Environment variables are used for API keys.

```typescript
const apiGatewayServer = createSdkMcpServer({
  name: "api-gateway",
  version: "1.0.0",
  tools: [
    tool(
      "api_request",
      "Make authenticated API requests to external services",
      {
        service: z.enum(["stripe", "github", "openai", "slack"]).describe("Service to call"),
        endpoint: z.string().describe("API endpoint path"),
        method: z.enum(["GET", "POST", "PUT", "DELETE"]).describe("HTTP method"),
        body: z.record(z.any()).optional().describe("Request body"),
        query: z.record(z.string()).optional().describe("Query parameters")
      },
      async (args) => {
        const config = {
          stripe: { baseUrl: "https://api.stripe.com/v1", key: process.env.STRIPE_KEY },
          github: { baseUrl: "https://api.github.com", key: process.env.GITHUB_TOKEN },
          openai: { baseUrl: "https://api.openai.com/v1", key: process.env.OPENAI_KEY },
          slack: { baseUrl: "https://slack.com/api", key: process.env.SLACK_TOKEN }
        };

        const { baseUrl, key } = config[args.service];
        const url = new URL(`${baseUrl}${args.endpoint}`);

        if (args.query) {
          Object.entries(args.query).forEach(([k, v]) => url.searchParams.set(k, v));
        }

        const response = await fetch(url, {
          method: args.method,
          headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
          body: args.body ? JSON.stringify(args.body) : undefined
        });

        const data = await response.json();
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(data, null, 2)
            }
          ]
        };
      }
    )
  ]
});
````

```python
import os
import json
import aiohttp
from typing import Any


# For complex schemas with enums, use JSON Schema format
@tool(
    "api_request",
    "Make authenticated API requests to external services",
    {
        "type": "object",
        "properties": {
            "service": {
                "type": "string",
                "enum": ["stripe", "github", "openai", "slack"]
            },
            "endpoint": {"type": "string"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
            "body": {"type": "object"},
            "query": {"type": "object"}
        },
        "required": ["service", "endpoint", "method"]
    },
)
async def api_request(args: dict[str, Any]) -> dict[str, Any]:
    config = {
        "stripe": {
            "base_url": "https://api.stripe.com/v1",
            "key": os.environ["STRIPE_KEY"]
        },
        "github": {
            "base_url": "https://api.github.com",
            "key": os.environ["GITHUB_TOKEN"]
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "key": os.environ["OPENAI_KEY"]
        },
        "slack": {
            "base_url": "https://slack.com/api",
            "key": os.environ["SLACK_TOKEN"]
        }
    }

    service_config = config[args["service"]]
    url = f"{service_config['base_url']}{args['endpoint']}"

    if args.get("query"):
        params = "&".join([f"{k}={v}" for k, v in args["query"].items()])
        url += f"?{params}"

    headers = {
        "Authorization": f"Bearer {service_config['key']}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.request(
            args["method"], url, headers=headers, json=args.get("body")
        ) as response:
            data = await response.json()
            return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}]}


api_gateway_server = create_sdk_mcp_server(
    name="api-gateway",
    version="1.0.0",
    tools=[api_request]
)
```

---

### Define McpHttpServerConfig for Claude Agent SDK (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This `TypedDict` configures an MCP server that communicates over HTTP. It specifies the URL for the HTTP endpoint and allows for optional custom HTTP headers. This provides a standard web-based communication method for the MCP server.

```python
class McpHttpServerConfig(TypedDict):
    type: Literal["http"]
    url: str
    headers: NotRequired[dict[str, str]]
```

---

### WebSearch Tool

Source: https://platform.claude.com/docs/en/agent-sdk/python

Performs web searches with optional domain filtering. Returns search results with titles, URLs, snippets, and metadata. Supports domain whitelisting and blacklisting.

````APIDOC
## WebSearch Tool

### Description
Performs web searches and returns results with optional domain filtering for targeted searches.

### Tool Name
`WebSearch`

### Input Parameters
- **query** (string) - Required - The search query to use
- **allowed_domains** (array[string] | null) - Optional - Only include results from these domains
- **blocked_domains** (array[string] | null) - Optional - Never include results from these domains

### Request Example
```python
{
    "query": "machine learning tutorials",
    "allowed_domains": ["github.com", "medium.com"],
    "blocked_domains": ["spam-site.com"]
}
````

### Response

- **results** (array) - Array of search result objects
  - **title** (string) - Result title
  - **url** (string) - Result URL
  - **snippet** (string) - Result snippet/description
  - **metadata** (object | null) - Additional metadata
- **total_results** (integer) - Total number of results found
- **query** (string) - The search query used

### Response Example

```python
{
    "results": [
        {
            "title": "Machine Learning Tutorial",
            "url": "https://github.com/example/ml-tutorial",
            "snippet": "A comprehensive guide to machine learning...",
            "metadata": {"author": "John Doe"}
        }
    ],
    "total_results": 1000,
    "query": "machine learning tutorials"
}
```

````

--------------------------------

### Define SdkPluginConfig for Claude Agent SDK (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This `TypedDict` specifies the configuration for loading plugins within the SDK. Currently, it only supports local plugins, requiring a `type` of 'local' and an absolute or relative `path` to the plugin directory. This allows extending agent functionality with custom plugins.

```python
class SdkPluginConfig(TypedDict):
    type: Literal["local"]
    path: str
````

---

### Client Method: rewind_files(user_message_id)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Restores files to their state at the specified user message. This feature requires `enable_file_checkpointing=True` to be enabled during client initialization.

````APIDOC
## Client Method: rewind_files(user_message_id)

### Description
Restore files to their state at the specified user message. Requires `enable_file_checkpointing=True` during client initialization. This allows reverting file modifications within a session.

### Method
rewind_files

### Parameters
#### Arguments
- **user_message_id** (string) - Required - The ID of the user message to which the file state should be rewound.

### Request Example
```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient

async def main():
    # Client must be initialized with file checkpointing enabled
    async with ClaudeSDKClient(enable_file_checkpointing=True) as client:
        await client.connect()
        # Assume some file operations happened after 'msg_abc123'
        # ...
        await client.rewind_files("msg_abc123")
        print("Files rewound to state at message ID 'msg_abc123'.")

asyncio.run(main())
````

### Response

#### Return Value

- **None** - This method does not return a value.

#### Response Example

```json
null
```

````

--------------------------------

### Manage a Single Checkpoint for Risky Operations with Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/file-checkpointing

This pattern demonstrates how to maintain only the most recent checkpoint UUID, updating it before each agent turn. This allows for an immediate rewind to the last safe state if an error or undesirable outcome occurs, effectively breaking out of the current processing loop and restoring files to a known good condition.

```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, UserMessage


async def main():
    options = ClaudeAgentOptions(
        enable_file_checkpointing=True,
        permission_mode="acceptEdits",
        extra_args={"replay-user-messages": None},
    )

    safe_checkpoint = None

    async with ClaudeSDKClient(options) as client:
        await client.query("Refactor the authentication module")

        async for message in client.receive_response():
            # Update checkpoint before each agent turn starts
            # This overwrites the previous checkpoint. Only keep the latest
            if isinstance(message, UserMessage) and message.uuid:
                safe_checkpoint = message.uuid

            # Decide when to revert based on your own logic
            # For example: error detection, validation failure, or user input
            if your_revert_condition and safe_checkpoint:
                await client.rewind_files(safe_checkpoint)
                # Exit the loop after rewinding, files are restored
                break


asyncio.run(main())
````

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

async function main() {
  const response = query({
    prompt: "Refactor the authentication module",
    options: {
      enableFileCheckpointing: true,
      permissionMode: "acceptEdits" as const,
      extraArgs: { "replay-user-messages": null },
    },
  });

  let safeCheckpoint: string | undefined;

  for await (const message of response) {
    // Update checkpoint before each agent turn starts
    // This overwrites the previous checkpoint. Only keep the latest
    if (message.type === "user" && message.uuid) {
      safeCheckpoint = message.uuid;
    }

    // Decide when to revert based on your own logic
    // For example: error detection, validation failure, or user input
    if (yourRevertCondition && safeCheckpoint) {
      await response.rewindFiles(safeCheckpoint);
      // Exit the loop after rewinding, files are restored
      break;
    }
  }
}

main();
```

---

### Create Database Query Tool for Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/custom-tools

This snippet demonstrates how to define a database query tool within an Agent SDK server, supporting both TypeScript and Python. The tool accepts a SQL query string and optional parameters, executes the query using a `db.query` function, and returns the results. It also illustrates how to register this tool with an SDK server instance.

```typescript
const databaseServer = createSdkMcpServer({
  name: "database-tools",
  version: "1.0.0",
  tools: [
    tool(
      "query_database",
      "Execute a database query",
      {
        query: z.string().describe("SQL query to execute"),
        params: z.array(z.any()).optional().describe("Query parameters"),
      },
      async (args) => {
        const results = await db.query(args.query, args.params || []);
        return {
          content: [
            {
              type: "text",
              text: `Found ${results.length} rows:\n${JSON.stringify(results, null, 2)}`,
            },
          ],
        };
      },
    ),
  ],
});
```

```python
from typing import Any
import json


@tool(
    "query_database",
    "Execute a database query",
    {"query": str, "params": list},  # Simple schema with list type
)
async def query_database(args: dict[str, Any]) -> dict[str, Any]:
    results = await db.query(args["query"], args.get("params", []))
    return {
        "content": [
            {
                "type": "text",
                "text": f"Found {len(results)} rows:\n{json.dumps(results, indent=2)}",
            }
        ]
    }


database_server = create_sdk_mcp_server(
    name="database-tools",
    version="1.0.0",
    tools=[query_database],  # Pass the decorated function
)
```

---

### Method ClaudeSDKClient.query

Source: https://platform.claude.com/docs/en/agent-sdk/python

Sends a query to the Claude agent within the current session, optionally specifying a session ID.

````APIDOC
## METHOD ClaudeSDKClient.query

### Description
Sends a query to the Claude agent within the current session, optionally specifying a session ID.

### Method
Async Class Method

### Endpoint
async def query(self, prompt: str | AsyncIterable[dict], session_id: str = "default") -> None

### Parameters
#### Request Body
- **prompt** (str | AsyncIterable[dict]) - Required - The prompt or messages to send.
- **session_id** (str) - Optional - Default: "default" - Identifier for the conversation session.

### Request Example
```python
# Assuming 'client' is an initialized ClaudeSDKClient instance
await client.query("What is the capital of France?")
````

### Response

#### Success Response (200)

- **None** - The method returns nothing after sending the query.

#### Response Example

```python
# No explicit return value
```

````

--------------------------------

### Basic Session with V2 TypeScript SDK

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Create a session and send a message with explicit send()/stream() separation for multi-turn conversations. Uses await using (TypeScript 5.2+) for automatic resource cleanup. The stream() method yields message objects that can be filtered by type to extract assistant responses.

```typescript
import { unstable_v2_createSession } from "@anthropic-ai/claude-agent-sdk";

await using session = unstable_v2_createSession({
  model: "claude-opus-4-6"
});

await session.send("Hello!");
for await (const msg of session.stream()) {
  // Filter for assistant messages to get human-readable output
  if (msg.type === "assistant") {
    const text = msg.message.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("");
    console.log(text);
  }
}
````

---

### TOOL Bash

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the input and output structure for the 'Bash' tool, enabling the execution of shell commands within the agent's environment.

```APIDOC
## TOOL /tools/Bash

### Description
Executes a bash command within the agent's environment.

### Method
TOOL

### Endpoint
/tools/Bash

### Parameters
#### Path Parameters
- No path parameters.

#### Query Parameters
- No query parameters.

#### Request Body
- **command** (string) - Required - The command to execute
- **timeout** (integer | null) - Optional - Optional timeout in milliseconds (max 600000)
- **description** (string | null) - Optional - Clear, concise description (5-10 words)
- **run_in_background** (boolean | null) - Optional - Set to true to run in background

### Request Example
{
  "command": "ls -l /var/log",
  "timeout": 30000,
  "description": "List log files"
}

### Response
#### Success Response (200)
- **output** (string) - Combined stdout and stderr output
- **exitCode** (integer) - Exit code of the command
- **killed** (boolean | null) - Whether command was killed due to timeout
- **shellId** (string | null) - Shell ID for background processes

#### Response Example
{
  "output": "total 4\n-rw-r--r-- 1 root root 0 Jan 1 00:00 auth.log\n-rw-r--r-- 1 root root 0 Jan 1 00:00 syslog",
  "exitCode": 0,
  "killed": false,
  "shellId": null
}
```

---

### Configure `canUseTool` callback for Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This snippet demonstrates how to configure the `canUseTool` callback in the Claude Agent SDK options. This callback is invoked when Claude requires user input, either for tool approval or to answer clarifying questions, pausing execution until a response is returned. It receives the tool name and input data, allowing the application to prompt the user and return their decision.

```python
async def handle_tool_request(tool_name, input_data, context):
    # Prompt user and return allow or deny
    ...


options = ClaudeAgentOptions(can_use_tool=handle_tool_request)
```

```typescript
async function handleToolRequest(toolName, input) {
  // Prompt user and return allow or deny
}

const options = { canUseTool: handleToolRequest };
```

---

### Grep Tool - Advanced Text Search with Context

Source: https://docs.claude.com/en/api/agent-sdk/python

Searches files using regex patterns with extensive filtering options including case-insensitive search, line numbers, context lines, and multiline mode. Supports multiple output modes (content, files_with_matches, count) and file type filtering. Returns matches with optional before/after context.

```json
{
  "pattern": "str",
  "path": "str | None",
  "glob": "str | None",
  "type": "str | None",
  "output_mode": "str | None",
  "-i": "bool | None",
  "-n": "bool | None",
  "-B": "int | None",
  "-A": "int | None",
  "-C": "int | None",
  "head_limit": "int | None",
  "multiline": "bool | None"
}
```

```json
{
  "matches": [
    {
      "file": "str",
      "line_number": "int | None",
      "line": "str",
      "before_context": "list[str] | None",
      "after_context": "list[str] | None"
    }
  ],
  "total_matches": "int"
}
```

```json
{
  "files": "list[str]",
  "count": "int"
}
```

---

### Client Method: set_model(model)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Changes the model used for the current session. Pass `None` to reset to the default model configured for the client.

````APIDOC
## Client Method: set_model(model)

### Description
Change the model for the current session. Pass `None` to reset to default. This allows switching between different Claude models during a conversation.

### Method
set_model

### Parameters
#### Arguments
- **model** (string | None) - Required - The identifier of the model to use (e.g., "claude-3-opus-20240229", "claude-3-sonnet-20240229"), or `None` to revert to the client's default model.

### Request Example
```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient

async def main():
    async with ClaudeSDKClient() as client:
        await client.connect()
        await client.set_model("claude-3-sonnet-20240229")
        print("Model set to Claude 3 Sonnet.")
        await client.query("Hello, Sonnet!")
        # ... receive response ...
        await client.set_model(None) # Reset to default
        print("Model reset to default.")

asyncio.run(main())
````

### Response

#### Return Value

- **None** - This method does not return a value.

#### Response Example

```json
null
```

````

--------------------------------

### Read Tool

Source: https://platform.claude.com/docs/en/agent-sdk/python

Reads file contents with optional line offset and limit parameters. Supports both text files (returns content with line numbers) and image files (returns base64 encoded data). Useful for retrieving specific portions of large files.

```APIDOC
## Read Tool

### Description
Reads file contents from the specified path. Supports text files with line-based pagination and image files with base64 encoding.

### Tool Name
`Read`

### Input Parameters
- **file_path** (string) - Required - The absolute path to the file to read
- **offset** (integer | null) - Optional - The line number to start reading from
- **limit** (integer | null) - Optional - The number of lines to read

### Request Example
```python
{
    "file_path": "/path/to/file.txt",
    "offset": 10,
    "limit": 50
}
````

### Response (Text Files)

- **content** (string) - File contents with line numbers
- **total_lines** (integer) - Total number of lines in file
- **lines_returned** (integer) - Lines actually returned

### Response (Image Files)

- **image** (string) - Base64 encoded image data
- **mime_type** (string) - Image MIME type
- **file_size** (integer) - File size in bytes

### Response Example (Text)

```python
{
    "content": "1: line one\n2: line two\n3: line three",
    "total_lines": 100,
    "lines_returned": 3
}
```

### Response Example (Image)

```python
{
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",
    "mime_type": "image/png",
    "file_size": 1024
}
```

````

--------------------------------

### Define a Custom Command with Bash Execution in Markdown

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

This snippet demonstrates how to create a custom command that executes bash commands and includes their output directly within the command's context using the `!` syntax. The `/git-commit` command gathers `git status` and `git diff HEAD` output to inform the commit message generation.

```markdown
---
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)
description: Create a git commit
---

## Context

- Current status: !`git status`
- Current diff: !`git diff HEAD`

## Task

Create a git commit with appropriate message based on the changes.
````

---

### Bash Tool Input/Output Schema

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the input and output structure for the Bash tool, which executes shell commands. Input includes the command, optional timeout, description, and background execution flag. Output provides combined stdout/stderr, exit code, timeout status, and shell ID for background processes.

```json
{
  "input": {
    "command": "str",
    "timeout": "int | None",
    "description": "str | None",
    "run_in_background": "bool | None"
  },
  "output": {
    "output": "str",
    "exitCode": "int",
    "killed": "bool | None",
    "shellId": "str | None"
  }
}
```

---

### Query Function Options

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

This section details the `Options` configuration object used to customize the behavior of the `query()` function in the Claude Agent SDK.

```APIDOC
## Configuration Object: `Options`

### Description
Configuration object for the `query()` function in the Claude Agent SDK. This object allows you to customize various aspects of the agent's behavior, permissions, environment, and execution.

### Object Name
`Options`

### Properties
- **`abortController`** (`AbortController`) - Optional - Default: `new AbortController()` - Controller for cancelling operations.
- **`additionalDirectories`** (`string[]`) - Optional - Default: `[]` - Additional directories Claude can access.
- **`agent`** (`string`) - Optional - Default: `undefined` - Agent name for the main thread. The agent must be defined in the `agents` option or in settings.
- **`agents`** (`Record<string, AgentDefinition>`) - Optional - Default: `undefined` - Programmatically define subagents.
- **`allowDangerouslySkipPermissions`** (`boolean`) - Optional - Default: `false` - Enable bypassing permissions. Required when using `permissionMode: 'bypassPermissions'`.
- **`allowedTools`** (`string[]`) - Optional - Default: `[]` - Tools to auto-approve without prompting. This does not restrict Claude to only these tools; unlisted tools fall through to `permissionMode` and `canUseTool`. Use `disallowedTools` to block tools. See [Permissions](/docs/en/agent-sdk/permissions#allow-and-deny-rules).
- **`betas`** (`SdkBeta[]`) - Optional - Default: `[]` - Enable beta features (e.g., `['context-1m-2025-08-07']`).
- **`canUseTool`** (`CanUseTool`) - Optional - Default: `undefined` - Custom permission function for tool usage.
- **`continue`** (`boolean`) - Optional - Default: `false` - Continue the most recent conversation.
- **`cwd`** (`string`) - Optional - Default: `process.cwd()` - Current working directory.
- **`debug`** (`boolean`) - Optional - Default: `false` - Enable debug mode for the Claude Code process.
- **`debugFile`** (`string`) - Optional - Default: `undefined` - Write debug logs to a specific file path. Implicitly enables debug mode.
- **`disallowedTools`** (`string[]`) - Optional - Default: `[]` - Tools to always deny. Deny rules are checked first and override `allowedTools` and `permissionMode` (including `bypassPermissions`).
- **`effort`** (`'low' | 'medium' | 'high' | 'max'`) - Optional - Default: `'high'` - Controls how much effort Claude puts into its response. Works with adaptive thinking to guide thinking depth.
- **`enableFileCheckpointing`** (`boolean`) - Optional - Default: `false` - Enable file change tracking for rewinding. See [File checkpointing](/docs/en/agent-sdk/file-checkpointing).
- **`env`** (`Record<string, string | undefined>`) - Optional - Default: `process.env` - Environment variables. Set `CLAUDE_AGENT_SDK_CLIENT_APP` to identify your app in the User-Agent header.
- **`executable`** (`'bun' | 'deno' | 'node'`) - Optional - Default: `Auto-detected` - JavaScript runtime to use.
- **`executableArgs`** (`string[]`) - Optional - Default: `[]` - Arguments to pass to the executable.
- **`extraArgs`** (`Record<string, string | null>`) - Optional - Default: `{}` - Additional arguments.
- **`fallbackModel`** (`string`) - Optional - Default: `undefined` - Model to use if primary fails.
- **`forkSession`** (`boolean`) - Optional - Default: `false` - When resuming with `resume`, fork to a new session ID instead of continuing the original session.
- **`hooks`** (`Partial<Record<HookEvent, HookCallbackMatcher[]>>`) - Optional - Default: `{}` - Hook callbacks for events.
- **`includePartialMessages`** (`boolean`) - Optional - Default: `false` - Include partial message events.
- **`maxBudgetUsd`** (`number`) - Optional - Default: `undefined` - Maximum budget in USD for the query.
- **`maxThinkingTokens`** (`number`) - Optional - Default: `undefined` - _Deprecated:_ Use `thinking` instead. Maximum tokens for thinking process.
- **`maxTurns`** (`number`) - Optional - Default: `undefined` - Maximum conversation turns.
- **`mcpServers`** (`Record<string, McpServerConfig>`) - Optional - Default: `{}` - MCP server configurations.
- **`model`** (`string`) - Optional - Default: `Default from CLI` - Claude model to use.
- **`outputFormat`** (`{ type: 'json_schema', schema: JSONSchema }`) - Optional - Default: `undefined` - Define output format for agent results. See [Structured outputs](/docs/en/agent-sdk/structured-outputs) for details.
- **`pathToClaudeCodeExecutable`** (`string`) - Optional - Default: `Uses built-in executable` - Path to Claude Code executable.
- **`permissionMode`** (`PermissionMode`) - Optional - Default: `'default'` - Permission mode for the session.
- **`permissionPromptToolName`** (`string`) - Optional - Default: `undefined` - MCP tool name for permission prompts.
- **`persistSession`** (`boolean`) - Optional - Default: `true` - When `false`, disables session persistence to disk. Sessions cannot be resumed later.
- **`plugins`** (`SdkPluginConfig[]`) - Optional - Default: `[]` - Load custom plugins from local paths. See [Plugins](/docs/en/agent-sdk/plugins) for details.
- **`promptSuggestions`** (`boolean`) - Optional - Default: `false` - Enable prompt suggestions. Emits a `prompt_suggestion` message after each turn with a predicted next user prompt.
- **`resume`** (`string`) - Optional - Default: `undefined` - Session ID to resume.
- **`resumeSessionAt`** (`string`) - Optional - Default: `undefined` - Resume session at a specific message UUID.
- **`sandbox`** (`SandboxSettings`) - Optional - Default: `undefined` - Configure sandbox behavior programmatically. See [Sandbox settings](#sandboxsettings) for details.
- **`sessionId`** (`string`) - Optional - Default: `Auto-generated` - Use a specific UUID for the session instead of auto-generating one.
```

---

### Route Tool Calls with canUseTool Callback - Python

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

Permission callback that routes tool calls based on tool name. Checks if the tool is 'AskUserQuestion' and delegates to the question handler, otherwise auto-approves other tools. This controls which tools Claude can use and how they are processed.

```python
async def can_use_tool(
    tool_name: str, input_data: dict, context
) -> PermissionResultAllow:
    # Route AskUserQuestion to our question handler
    if tool_name == "AskUserQuestion":
        return await handle_ask_user_question(input_data)
    # Auto-approve other tools for this example
    return PermissionResultAllow(updated_input=input_data)
```

---

### Grant Access to MCP Tools with allowedTools (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

This TypeScript-like code snippet shows how to configure the `allowedTools` option to control which Model Context Protocol (MCP) tools an agent can use. It demonstrates granting access to all tools from a server using a wildcard (`mcp__github__*`), as well as specifying individual tools from different servers (`mcp__db__query`, `mcp__slack__send_message`). This is crucial for security and managing agent capabilities.

```typescript
const _ = {
  options: {
    mcpServers: {
      // your servers
    },
    allowedTools: [
      "mcp__github__*", // All tools from the github server
      "mcp__db__query", // Only the query tool from db server
      "mcp__slack__send_message", // Only send_message from slack server
    ],
  },
};
```

---

### Handle system prompt default change

Source: https://platform.claude.com/docs/en/agent-sdk/migration-guide

The Claude Agent SDK no longer uses Claude Code's system prompt by default. Explicitly configure the system prompt using a preset or a custom string in both TypeScript/JavaScript and Python projects to maintain previous behavior or define new behavior.

```typescript
// BEFORE (v0.0.x) - Used Claude Code's system prompt by default
const result = query({ prompt: "Hello" });

// AFTER (v0.1.0) - Uses minimal system prompt by default
// To get the old behavior, explicitly request Claude Code's preset:
const result = query({
  prompt: "Hello",
  options: {
    systemPrompt: { type: "preset", preset: "claude_code" },
  },
});

// Or use a custom system prompt:
const result = query({
  prompt: "Hello",
  options: {
    systemPrompt: "You are a helpful coding assistant",
  },
});
```

```python
# BEFORE (v0.0.x) - Used Claude Code's system prompt by default
async for message in query(prompt="Hello"):
    print(message)

# AFTER (v0.1.0) - Uses minimal system prompt by default
# To get the old behavior, explicitly request Claude Code's preset:
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Hello",
    options=ClaudeAgentOptions(
        system_prompt={"type": "preset", "preset": "claude_code"}  # Use the preset
    ),
):
    print(message)
```

---

### Streaming Message Generator with Image Attachments

Source: https://platform.claude.com/docs/en/agent-sdk/streaming-vs-single-mode

Implements an async generator pattern for multi-turn conversations with support for text and image content. Demonstrates yielding multiple user messages with delays and processing streaming responses from the Claude Agent SDK. Requires file system access for image encoding.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";
import { readFile } from "fs/promises";

async function* generateMessages() {
  // First message
  yield {
    type: "user" as const,
    message: {
      role: "user" as const,
      content: "Analyze this codebase for security issues",
    },
  };

  // Wait for conditions or user input
  await new Promise((resolve) => setTimeout(resolve, 2000));

  // Follow-up with image
  yield {
    type: "user" as const,
    message: {
      role: "user" as const,
      content: [
        {
          type: "text",
          text: "Review this architecture diagram",
        },
        {
          type: "image",
          source: {
            type: "base64",
            media_type: "image/png",
            data: await readFile("diagram.png", "base64"),
          },
        },
      ],
    },
  };
}

// Process streaming responses
for await (const message of query({
  prompt: generateMessages(),
  options: {
    maxTurns: 10,
    allowedTools: ["Read", "Grep"],
  },
})) {
  if (message.type === "result") {
    console.log(message.result);
  }
}
```

```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)
import asyncio
import base64


async def streaming_analysis():
    async def message_generator():
        # First message
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": "Analyze this codebase for security issues",
            },
        }

        # Wait for conditions
        await asyncio.sleep(2)

        # Follow-up with image
        with open("diagram.png", "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Review this architecture diagram"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data,
                        },
                    },
                ],
            },
        }

    # Use ClaudeSDKClient for streaming input
    options = ClaudeAgentOptions(max_turns=10, allowed_tools=["Read", "Grep"])

    async with ClaudeSDKClient(options) as client:
        # Send streaming input
        await client.query(message_generator())

        # Process responses
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text)


asyncio.run(streaming_analysis())
```

---

### Define ClaudeSDKClient Class Methods (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This snippet outlines the method signatures for the `ClaudeSDKClient` class, which is designed to maintain a conversation session across multiple exchanges, similar to the TypeScript SDK's internal `query()` function. It provides methods for initializing the client, connecting to Claude, sending queries, receiving messages, managing session state (interrupt, permissions, model), and disconnecting. Key features include session continuity, interrupt support, and an explicit lifecycle.

```python
class ClaudeSDKClient:
    def __init__(self, options: ClaudeAgentOptions | None = None, transport: Transport | None = None)
    async def connect(self, prompt: str | AsyncIterable[dict] | None = None) -> None
    async def query(self, prompt: str | AsyncIterable[dict], session_id: str = "default") -> None
    async def receive_messages(self) -> AsyncIterator[Message]
    async def receive_response(self) -> AsyncIterator[Message]
    async def interrupt(self) -> None
    async def set_permission_mode(self, mode: str) -> None
    async def set_model(self, model: str | None = None) -> None
    async def rewind_files(self, user_message_id: str) -> None
    async def get_mcp_status(self) -> dict[str, Any]
    async def get_server_info(self) -> dict[str, Any] | None
    async def disconnect(self) -> None
```

---

### Define and Use Subagents with Claude Agent SDK (Python/TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/overview

This snippet demonstrates how to define and use subagents within the Claude Agent SDK. It shows how to configure a 'code-reviewer' agent with specific tools and prompts, and then query it to review a codebase, printing the results.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    async for message in query(
        prompt="Use the code-reviewer agent to review this codebase",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep", "Task"],
            agents={
                "code-reviewer": {
                    "description": "Expert code reviewer for quality and security reviews.",
                    "prompt": "Analyze code quality and suggest improvements.",
                    "tools": ["Read", "Glob", "Grep"]
                }
            }
        )
    ):
        if hasattr(message, "result"):
            print(message.result)

asyncio.run(main())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Use the code-reviewer agent to review this codebase",
  options: {
    allowedTools: ["Read", "Glob", "Grep", "Task"],
    agents: {
      "code-reviewer": {
        description: "Expert code reviewer for quality and security reviews.",
        prompt: "Analyze code quality and suggest improvements.",
        tools: ["Read", "Glob", "Grep"],
      },
    },
  },
})) {
  if ("result" in message) console.log(message.result);
}
```

---

### Handle Multi-turn Conversations with Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Demonstrates how to maintain conversational context across multiple exchanges using the Claude Agent SDK. It illustrates both the V2 approach, where `send()` is called repeatedly on the same session, and the V1 method, which uses an async iterable to feed messages to the `query` function.

```typescript
import { unstable_v2_createSession } from "@anthropic-ai/claude-agent-sdk";

await using session = unstable_v2_createSession({
  model: "claude-opus-4-6",
});

// Turn 1
await session.send("What is 5 + 3?");
for await (const msg of session.stream()) {
  // Filter for assistant messages to get human-readable output
  if (msg.type === "assistant") {
    const text = msg.message.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("");
    console.log(text);
  }
}

// Turn 2
await session.send("Multiply that by 2");
for await (const msg of session.stream()) {
  if (msg.type === "assistant") {
    const text = msg.message.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("");
    console.log(text);
  }
}
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Must create an async iterable to feed messages
async function* createInputStream() {
  yield {
    type: "user",
    session_id: "",
    message: {
      role: "user",
      content: [{ type: "text", text: "What is 5 + 3?" }],
    },
    parent_tool_use_id: null,
  };
  // Must coordinate when to yield next message
  yield {
    type: "user",
    session_id: "",
    message: {
      role: "user",
      content: [{ type: "text", text: "Multiply by 2" }],
    },
    parent_tool_use_id: null,
  };
}

const q = query({
  prompt: createInputStream(),
  options: { model: "claude-opus-4-6" },
});

for await (const msg of q) {
  if (msg.type === "assistant") {
    const text = msg.message.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("");
    console.log(text);
  }
}
```

---

### Implement a Bug-Fixing AI Agent with Claude Agent SDK (Python/TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/overview

This snippet demonstrates how to create an AI agent that can autonomously find and fix bugs in a specified file. It utilizes the SDK's `query` function with `Read`, `Edit`, and `Bash` tools to allow Claude to interact with the codebase.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    async for message in query(
        prompt="Find and fix the bug in auth.py",
        options=ClaudeAgentOptions(allowed_tools=["Read", "Edit", "Bash"]),
    ):
        print(message)  # Claude reads the file, finds the bug, edits it


asyncio.run(main())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Find and fix the bug in auth.py",
  options: { allowedTools: ["Read", "Edit", "Bash"] },
})) {
  console.log(message); // Claude reads the file, finds the bug, edits it
}
```

---

### Define Calculator Tool Server with SDK (TypeScript & Python)

Source: https://platform.claude.com/docs/en/agent-sdk/custom-tools

This snippet demonstrates how to define a calculator tool server using the SDK in both TypeScript and Python. It includes two tools: 'calculate' for evaluating mathematical expressions and 'compound_interest' for financial calculations. The server is configured with a name and version, and the tools are registered with their respective schemas and asynchronous execution logic.

```typescript
const calculatorServer = createSdkMcpServer({
  name: "calculator",
  version: "1.0.0",
  tools: [
    tool(
      "calculate",
      "Perform mathematical calculations",
      {
        expression: z.string().describe("Mathematical expression to evaluate"),
        precision: z
          .number()
          .optional()
          .default(2)
          .describe("Decimal precision"),
      },
      async (args) => {
        try {
          // Use a safe math evaluation library in production
          const result = eval(args.expression); // Example only!
          const formatted = Number(result).toFixed(args.precision);

          return {
            content: [
              {
                type: "text",
                text: `${args.expression} = ${formatted}`,
              },
            ],
          };
        } catch (error) {
          return {
            content: [
              {
                type: "text",
                text: `Error: Invalid expression - ${error.message}`,
              },
            ],
          };
        }
      },
    ),
    tool(
      "compound_interest",
      "Calculate compound interest for an investment",
      {
        principal: z.number().positive().describe("Initial investment amount"),
        rate: z
          .number()
          .describe("Annual interest rate (as decimal, e.g., 0.05 for 5%)"),
        time: z.number().positive().describe("Investment period in years"),
        n: z
          .number()
          .positive()
          .default(12)
          .describe("Compounding frequency per year"),
      },
      async (args) => {
        const amount =
          args.principal * Math.pow(1 + args.rate / args.n, args.n * args.time);
        const interest = amount - args.principal;

        return {
          content: [
            {
              type: "text",
              text:
                "Investment Analysis:\n" +
                `Principal: $${args.principal.toFixed(2)}\n` +
                `Rate: ${(args.rate * 100).toFixed(2)}%\n` +
                `Time: ${args.time} years\n` +
                `Compounding: ${args.n} times per year\n\n` +
                `Final Amount: $${amount.toFixed(2)}\n` +
                `Interest Earned: $${interest.toFixed(2)}\n` +
                `Return: ${((interest / args.principal) * 100).toFixed(2)}%`,
            },
          ],
        };
      },
    ),
  ],
});
```

```python
import math
from typing import Any


@tool(
    "calculate",
    "Perform mathematical calculations",
    {"expression": str, "precision": int},  # Simple schema
)
async def calculate(args: dict[str, Any]) -> dict[str, Any]:
    try:
        # Use a safe math evaluation library in production
        result = eval(args["expression"], {"__builtins__": {}})
        precision = args.get("precision", 2)
        formatted = round(result, precision)

        return {
            "content": [{"type": "text", "text": f"{args['expression']} = {formatted}"}]
        }
    except Exception as e:
        return {
            "content": [
                {"type": "text", "text": f"Error: Invalid expression - {str(e)}"}
            ]
        }


@tool(
    "compound_interest",
    "Calculate compound interest for an investment",
    {"principal": float, "rate": float, "time": float, "n": int},
)
async def compound_interest(args: dict[str, Any]) -> dict[str, Any]:
    principal = args["principal"]
    rate = args["rate"]
    time = args["time"]
    n = args.get("n", 12)

    amount = principal * (1 + rate / n) ** (n * time)
    interest = amount - principal

    return {
        "content": [
            {
                "type": "text",
                "text": f"""Investment Analysis:\nPrincipal: ${principal:.2f}\nRate: {rate * 100:.2f}%\nTime: {time} years\nCompounding: {n} times per year\n\nFinal Amount: ${amount:.2f}\nInterest Earned: ${interest:.2f}\nReturn: {(interest / principal) * 100:.2f}%""",
            }
        ]
    }


calculator_server = create_sdk_mcp_server(
    name="calculator",
    version="1.0.0",
    tools=[calculate, compound_interest],  # Pass decorated functions
)
```

---

### Define SDKSystemMessage TypeScript Type

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Represents the system initialization message containing session metadata, configuration, and environment details. Includes agent information, API key source, tools, MCP servers, and permission mode settings.

```typescript
type SDKSystemMessage = {
  type: "system";
  subtype: "init";
  uuid: UUID;
  session_id: string;
  agents?: string[];
  apiKeySource: ApiKeySource;
  betas?: string[];
  claude_code_version: string;
  cwd: string;
  tools: string[];
  mcp_servers: {
    name: string;
    status: string;
  }[];
  model: string;
  permissionMode: PermissionMode;
  slash_commands: string[];
  output_style: string;
  skills: string[];
  plugins: { name: string; path: string }[];
};
```

---

### Read Tool - File Content Retrieval with Line Offset

Source: https://docs.claude.com/en/api/agent-sdk/python

Reads file contents with optional line offset and limit parameters. Supports both text files (returns content with line numbers) and image files (returns Base64 encoded data). Useful for retrieving specific sections of large files without loading entire contents.

```json
{
  "file_path": "str",
  "offset": "int | None",
  "limit": "int | None"
}
```

```json
{
  "content": "str",
  "total_lines": "int",
  "lines_returned": "int"
}
```

```json
{
  "image": "str",
  "mime_type": "str",
  "file_size": "int"
}
```

---

### Real-time Todo Progress Tracker with Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/todo-tracking

Implements a TodoTracker class that streams queries through the Claude Agent SDK and displays real-time progress updates. The tracker processes assistant messages, extracts todo data from tool use blocks, and renders progress with status icons. Supports up to 20 conversation turns and handles multiple task states (completed, in_progress, pending).

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

class TodoTracker {
  private todos: any[] = [];

  displayProgress() {
    if (this.todos.length === 0) return;

    const completed = this.todos.filter((t) => t.status === "completed").length;
    const inProgress = this.todos.filter(
      (t) => t.status === "in_progress",
    ).length;
    const total = this.todos.length;

    console.log(`\nProgress: ${completed}/${total} completed`);
    console.log(`Currently working on: ${inProgress} task(s)\n`);

    this.todos.forEach((todo, index) => {
      const icon =
        todo.status === "completed"
          ? "✅"
          : todo.status === "in_progress"
            ? "🔧"
            : "❌";
      const text =
        todo.status === "in_progress" ? todo.activeForm : todo.content;
      console.log(`${index + 1}. ${icon} ${text}`);
    });
  }

  async trackQuery(prompt: string) {
    for await (const message of query({
      prompt,
      options: { maxTurns: 20 },
    })) {
      if (message.type === "assistant") {
        for (const block of message.message.content) {
          if (block.type === "tool_use" && block.name === "TodoWrite") {
            this.todos = block.input.todos;
            this.displayProgress();
          }
        }
      }
    }
  }
}

const tracker = new TodoTracker();
await tracker.trackQuery("Build a complete authentication system with todos");
```

```python
from claude_agent_sdk import query, AssistantMessage, ToolUseBlock
from typing import List, Dict


class TodoTracker:
    def __init__(self):
        self.todos: List[Dict] = []

    def display_progress(self):
        if not self.todos:
            return

        completed = len([t for t in self.todos if t["status"] == "completed"])
        in_progress = len([t for t in self.todos if t["status"] == "in_progress"])
        total = len(self.todos)

        print(f"\nProgress: {completed}/{total} completed")
        print(f"Currently working on: {in_progress} task(s)\n")

        for i, todo in enumerate(self.todos):
            icon = (
                "✅"
                if todo["status"] == "completed"
                else "🔧"
                if todo["status"] == "in_progress"
                else "❌"
            )
            text = (
                todo["activeForm"]
                if todo["status"] == "in_progress"
                else todo["content"]
            )
            print(f"{i + 1}. {icon} {text}")

    async def track_query(self, prompt: str):
        async for message in query(prompt=prompt, options={"max_turns": 20}):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock) and block.name == "TodoWrite":
                        self.todos = block.input["todos"]
                        self.display_progress()


tracker = TodoTracker()
await tracker.track_query("Build a complete authentication system with todos")
```

---

### Method ClaudeSDKClient.receive_response

Source: https://platform.claude.com/docs/en/agent-sdk/python

Asynchronously yields responses received from the Claude agent, allowing for response-driven flow.

````APIDOC
## METHOD ClaudeSDKClient.receive_response

### Description
Asynchronously yields responses received from the Claude agent, allowing for response-driven flow.

### Method
Async Class Method

### Endpoint
async def receive_response(self) -> AsyncIterator[Message]

### Parameters
#### Request Body
- No parameters.

### Request Example
```python
# Assuming 'client' is an initialized ClaudeSDKClient instance
async for response in client.receive_response():
    print(response)
````

### Response

#### Success Response (200)

- **AsyncIterator[Message]** - An asynchronous iterator yielding `Message` objects.

#### Response Example

```json
{
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Here is some information."
    }
  ]
}
```

````

--------------------------------

### NotebookEdit Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the input and output structures for the `NotebookEdit` tool. This tool allows programmatic editing of Jupyter notebooks, including replacing, inserting, or deleting cells. Inputs specify the notebook path, cell ID, new source, cell type, and edit mode, while outputs confirm the edit type and provide updated cell information.

```python
{
    "notebook_path": str,  # Absolute path to the Jupyter notebook
    "cell_id": str | None,  # The ID of the cell to edit
    "new_source": str,  # The new source for the cell
    "cell_type": "code" | "markdown" | None,  # The type of the cell
    "edit_mode": "replace" | "insert" | "delete" | None  # Edit operation type
}
````

```python
{
    "message": str,  # Success message
    "edit_type": "replaced" | "inserted" | "deleted",  # Type of edit performed
    "cell_id": str | None,  # Cell ID that was affected
    "total_cells": int  # Total cells in notebook after edit
}
```

---

### Approving Tool Execution with Input Modifications in Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This snippet illustrates how to modify a tool's input before execution, such as sanitizing parameters or scoping commands, while still allowing the tool to run. Claude is not informed of these changes, making it useful for enforcing constraints.

```python
async def can_use_tool(tool_name, input_data, context):
    if tool_name == "Bash":
        # User approved, but scope all commands to sandbox
        sandboxed_input = {**input_data}
        sandboxed_input["command"] = input_data["command"].replace(
            "/tmp", "/tmp/sandbox"
        )
        return PermissionResultAllow(updated_input=sandboxed_input)
    return PermissionResultAllow(updated_input=input_data)
```

```typescript
canUseTool: async (toolName, input) => {
  if (toolName === "Bash") {
    // User approved, but scope all commands to sandbox
    const sandboxedInput = {
      ...input,
      command: input.command.replace("/tmp", "/tmp/sandbox"),
    };
    return { behavior: "allow", updatedInput: sandboxedInput };
  }
  return { behavior: "allow", updatedInput: input };
};
```

---

### Verify Skill Filesystem Location via Bash

Source: https://platform.claude.com/docs/en/agent-sdk/skills

This snippet provides bash commands to verify the physical location of Skill definition files (`SKILL.md`) on the filesystem. It shows how to check for project-specific Skills within `.claude/skills/` and personal Skills in the user's home directory.

```bash
# Check project Skills
ls .claude/skills/*/SKILL.md

# Check personal Skills
ls ~/.claude/skills/*/SKILL.md
```

---

### Configure Sandbox Settings for Command Execution (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This Python `TypedDict` defines the `SandboxSettings` structure for configuring command execution sandboxing in the Claude Agent SDK. It allows control over enabling the sandbox, auto-approving bash commands, excluding specific commands, and managing network restrictions. Note that filesystem and network access restrictions are handled by separate permission rules, not these sandbox settings.

```python
class SandboxSettings(TypedDict, total=False):
    enabled: bool
    autoAllowBashIfSandboxed: bool
    excludedCommands: list[str]
    allowUnsandboxedCommands: bool
    network: SandboxNetworkConfig
    ignoreViolations: SandboxIgnoreViolations
    enableWeakerNestedSandbox: bool
```

---

### Set Anthropic API Key Environment Variable (Bash)

Source: https://platform.claude.com/docs/en/agent-sdk/overview

This command demonstrates how to set your Anthropic API key as an environment variable, which is required for authenticating with the Claude Agent SDK. The SDK also supports authentication via Amazon Bedrock, Google Vertex AI, and Microsoft Azure by setting specific environment variables.

```bash
export ANTHROPIC_API_KEY=your-api-key
```

---

### Data Structure: SandboxNetworkConfig

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines network-specific configuration options for the sandbox mode, controlling network access and proxy settings for sandboxed processes.

````APIDOC
## Data Structure: SandboxNetworkConfig

### Description
Defines network-specific configuration options for the sandbox mode, controlling network access and proxy settings for sandboxed processes.

### Method
TypedDict Definition

### Endpoint
N/A

### Parameters
#### Request Body
- **allowLocalBinding** (bool) - Optional - Default: `False` - Allow processes to bind to local ports (e.g., for dev servers).
- **allowUnixSockets** (list[str]) - Optional - Default: `[]` - A list of specific Unix socket paths that processes can access (e.g., `/var/run/docker.sock`).
- **allowAllUnixSockets** (bool) - Optional - Default: `False` - If `True`, allows access to all Unix sockets, bypassing individual path restrictions.
- **httpProxyPort** (int) - Optional - Default: `None` - The HTTP proxy port for network requests originating from the sandbox.
- **socksProxyPort** (int) - Optional - Default: `None` - The SOCKS proxy port for network requests originating from the sandbox.

### Request Example
```json
{
  "allowLocalBinding": true,
  "allowUnixSockets": [
    "/tmp/my_app.sock"
  ],
  "allowAllUnixSockets": false,
  "httpProxyPort": 8080
}
````

### Response

N/A (This is a configuration object, not an API response.)

### Response Example

N/A

````

--------------------------------

### Edit Tool Input/Output Schema

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the input and output schemas for the Edit tool used to modify file contents. Supports targeted string replacement with optional replace-all functionality, returning confirmation details and replacement count.

```python
# Edit Tool Input
{
    "file_path": str,  # The absolute path to the file to modify
    "old_string": str,  # The text to replace
    "new_string": str,  # The text to replace it with
    "replace_all": bool | None,  # Replace all occurrences (default False)
}

# Edit Tool Output
{
    "message": str,  # Confirmation message
    "replacements": int,  # Number of replacements made
    "file_path": str,  # File path that was edited
}
````

---

### Define PostToolUseHookInput TypedDict

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the input structure for PostToolUse hook events, triggered after successful tool execution. Includes the tool name, input parameters, response, and unique identifier.

```python
class PostToolUseHookInput(BaseHookInput):
    hook_event_name: Literal["PostToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_response: Any
    tool_use_id: str
```

---

### Deny tool execution in Python `can_use_tool`

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This Python snippet demonstrates how to explicitly deny a tool from executing within the `can_use_tool` callback. It shows returning a `PermissionResultDeny` object, which requires a `message` explaining the denial to Claude, allowing the agent to adjust its strategy accordingly.

```python
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

# Deny the tool from executing
return PermissionResultDeny(message="User denied this action")
```

---

### Single-Turn Query with unstable_v2_prompt()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Convenience function for one-shot single-turn queries without session management. Accepts a prompt string and configuration options, returning a promise that resolves to an SDKResultMessage containing the response.

```typescript
function unstable_v2_prompt(
  prompt: string,
  options: {
    model: string;
    // Additional options supported
  },
): Promise<SDKResultMessage>;
```

---

### Glob Tool

Source: https://platform.claude.com/docs/en/agent-sdk/python

Searches for files matching a glob pattern within a specified directory. Returns an array of matching file paths and the count of matches found.

````APIDOC
## Glob Tool

### Description
Searches for files matching a glob pattern in the specified directory. Useful for finding files by name patterns.

### Tool Name
`Glob`

### Input Parameters
- **pattern** (string) - Required - The glob pattern to match files against
- **path** (string | null) - Optional - The directory to search in (defaults to current working directory)

### Request Example
```python
{
    "pattern": "*.txt",
    "path": "/home/user/documents"
}
````

### Response

- **matches** (array[string]) - Array of matching file paths
- **count** (integer) - Number of matches found
- **search_path** (string) - Search directory used

### Response Example

```python
{
    "matches": ["/home/user/documents/file1.txt", "/home/user/documents/file2.txt"],
    "count": 2,
    "search_path": "/home/user/documents"
}
```

````

--------------------------------

### Define SdkBeta Type

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

TypeScript string literal type for available beta features in the SDK. Currently supports the context-1m-2025-08-07 beta for enabling 1 million token context windows on compatible Claude models.

```typescript
type SdkBeta = "context-1m-2025-08-07";
````

---

### Define Setting Source Type in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

This TypeScript type enumerates the possible filesystem-based configuration sources from which the Agent SDK can load settings. It includes 'user' for global user settings, 'project' for shared project settings, and 'local' for local project-specific settings, each corresponding to a specific `settings.json` file location.

```typescript
type SettingSource = "user" | "project" | "local";
```

---

### Chain multiple hooks in execution order

Source: https://platform.claude.com/docs/en/agent-sdk/hooks

Demonstrates configuring multiple hooks in a specific execution sequence for the PreToolUse event. Hooks execute in array order, with each hook focused on a single responsibility: rate limiting, authorization verification, input sanitization, and audit logging. This pattern enables complex permission and security logic through composition.

```python
options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(hooks=[rate_limiter]),  # First: check rate limits
            HookMatcher(hooks=[authorization_check]),  # Second: verify permissions
            HookMatcher(hooks=[input_sanitizer]),  # Third: sanitize inputs
            HookMatcher(hooks=[audit_logger]),  # Last: log the action
        ]
    }
)
```

```typescript
const options = {
  hooks: {
    PreToolUse: [
      { hooks: [rateLimiter] }, // First: check rate limits
      { hooks: [authorizationCheck] }, // Second: verify permissions
      { hooks: [inputSanitizer] }, // Third: sanitize inputs
      { hooks: [auditLogger] }, // Last: log the action
    ],
  },
};
```

---

### unstable_v2_createSession()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Creates a new session for multi-turn conversations.

```APIDOC
## SDK Function unstable_v2_createSession()

### Description
Creates a new session for multi-turn conversations.

### Method
SDK Function

### Parameters
#### Request Body
- **model** (string) - Required - The model to use for the session. Additional options are supported but not detailed here.

### Request Example
{
  "model": "claude-opus-4-6"
}

### Response
#### Success Response (SDKSession object)
- **sessionId** (string) - The unique identifier for the created session.
- **send** (function) - A method to send messages to the session.
- **stream** (function) - A method to stream messages from the session.
- **close** (function) - A method to close the session.

#### Response Example
{
  "sessionId": "sess_abc123def456",
  "send": "[function]",
  "stream": "[function]",
  "close": "[function]"
}
```

---

### Define PreToolUseHookInput TypedDict

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the input structure for PreToolUse hook events, triggered before a tool is executed. Contains the tool name, input parameters, and unique tool use identifier along with inherited base fields.

```python
class PreToolUseHookInput(BaseHookInput):
    hook_event_name: Literal["PreToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_use_id: str
```

---

### Interactive Rewind Prompt with Readline in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/file-checkpointing

Creates an interactive command-line prompt asking users whether to rewind file changes after agent execution. Uses Node.js readline interface to capture user input and closes the interface after receiving the response.

```typescript
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

const answer = await new Promise<string>((resolve) => {
  rl.question("Rewind to remove the doc comments? (y/n): ", resolve);
});
rl.close();
```

---

### SDKSession.send()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Sends a message to the session.

```APIDOC
## SDKSession.send()

### Description
Sends a message to the session.

### Method
SDK Function

### Parameters
- **message** (string | SDKUserMessage) - Required - The message to send. Can be a simple string or a structured `SDKUserMessage` object.

### Request Example
{
  "type": "user_message",
  "text": "Hello, Claude!"
}

### Response
#### Success Response (Promise<void>)
- No explicit return value. The promise resolves when the message is sent.

#### Response Example
(No response body)
```

---

### Configure Permission Modes for Tool Execution

Source: https://docs.claude.com/en/api/agent-sdk/python

Type alias defining four permission modes for controlling tool execution behavior: default standard behavior, acceptEdits for auto-accepting file modifications, plan for planning-only mode without execution, and bypassPermissions for unrestricted access.

```python
PermissionMode = Literal[
    "default",
    "acceptEdits",
    "plan",
    "bypassPermissions",
]
```

---

### Configure HTTP Headers for Remote MCP Servers

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

Set up authentication headers for HTTP and SSE remote servers by passing headers directly in the server configuration. This method allows Bearer token authentication and other header-based security mechanisms for remote MCP server connections.

```TypeScript
const _ = {
  options: {
    mcpServers: {
      "secure-api": {
        type: "http",
        url: "https://api.example.com/mcp",
        headers: {
          Authorization: `Bearer ${process.env.API_TOKEN}`
        }
      }
    },
    allowedTools: ["mcp__secure-api__*"]
  }
};
```

```Python
options = ClaudeAgentOptions(
    mcp_servers={
        "secure-api": {
            "type": "http",
            "url": "https://api.example.com/mcp",
            "headers": {"Authorization": f"Bearer {os.environ['API_TOKEN']}"},
        }
    },
    allowed_tools=["mcp__secure-api__*"],
)
```

```JSON
{
  "mcpServers": {
    "secure-api": {
      "type": "http",
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${API_TOKEN}"
      }
    }
  }
}
```

---

### Register PreToolUse Hook with ClaudeSDKClient - Python

Source: https://platform.claude.com/docs/en/agent-sdk/hooks

Initializes a ClaudeSDKClient with hook options that register the protect_env_files callback for PreToolUse events. Uses HookMatcher to filter only Write and Edit tool calls. Executes a query and processes assistant and result messages from the response stream.

```python
async def main():
    options = ClaudeAgentOptions(
        hooks={
            # Register the hook for PreToolUse events
            # The matcher filters to only Write and Edit tool calls
            "PreToolUse": [HookMatcher(matcher="Write|Edit", hooks=[protect_env_files])]
        }
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Update the database configuration")
        async for message in client.receive_response():
            # Filter for assistant and result messages
            if isinstance(message, (AssistantMessage, ResultMessage)):
                print(message)


asyncio.run(main())
```

---

### UserPromptSubmitHookInput - User Prompt Hook

Source: https://platform.claude.com/docs/en/agent-sdk/python

Provides input data for UserPromptSubmit hook events, which are triggered when a user submits a prompt. Contains the submitted prompt text.

````APIDOC
## UserPromptSubmitHookInput

### Description
Input data for UserPromptSubmit hook events. Triggered when a user submits a prompt to the agent.

### Structure
```python
class UserPromptSubmitHookInput(BaseHookInput):
    hook_event_name: Literal["UserPromptSubmit"]
    prompt: str
````

### Fields

- **hook_event_name** (Literal["UserPromptSubmit"]) - Required - Always "UserPromptSubmit"
- **prompt** (str) - Required - The user's submitted prompt

### Inherits From

- BaseHookInput (session_id, transcript_path, cwd, permission_mode)

````

--------------------------------

### Configure HTTP/SSE MCP Server

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

Set up cloud-hosted or remote MCP servers using HTTP or SSE transport protocols. Supports custom headers for authentication and works across TypeScript, Python, and .mcp.json configurations.

```typescript
const _ = {
  options: {
    mcpServers: {
      "remote-api": {
        type: "sse",
        url: "https://api.example.com/mcp/sse",
        headers: {
          Authorization: `Bearer ${process.env.API_TOKEN}`
        }
      }
    },
    allowedTools: ["mcp__remote-api__*"]
  }
};
````

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "remote-api": {
            "type": "sse",
            "url": "https://api.example.com/mcp/sse",
            "headers": {"Authorization": f"Bearer {os.environ['API_TOKEN']}"},
        }
    },
    allowed_tools=["mcp__remote-api__*"],
)
```

```json
{
  "mcpServers": {
    "remote-api": {
      "type": "sse",
      "url": "https://api.example.com/mcp/sse",
      "headers": {
        "Authorization": "Bearer ${API_TOKEN}"
      }
    }
  }
}
```

---

### Client Method: get_mcp_status()

Source: https://platform.claude.com/docs/en/agent-sdk/python

Retrieves the status of all configured MCP (Multi-Cloud Platform) servers. This provides insight into the health and connectivity of backend services.

````APIDOC
## Client Method: get_mcp_status()

### Description
Get the status of all configured MCP servers. This can be used for monitoring and debugging connectivity.

### Method
get_mcp_status

### Parameters
#### Arguments
- **None**

### Request Example
```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient

async def main():
    async with ClaudeSDKClient() as client:
        await client.connect()
        status = await client.get_mcp_status()
        print(f"MCP Server Status: {status}")

asyncio.run(main())
````

### Response

#### Return Value

- **object** - An object containing the status of each configured MCP server.

#### Response Example

```json
{
  "server_us_east": {
    "status": "online",
    "latency_ms": 50
  },
  "server_eu_west": {
    "status": "offline",
    "error": "Connection refused"
  }
}
```

````

--------------------------------

### Continue Conversation with Context Retention in Claude SDK

Source: https://docs.claude.com/en/api/agent-sdk/python

Demonstrates maintaining conversation state across multiple queries using ClaudeSDKClient. The SDK automatically retains context from previous messages, allowing follow-up questions to reference earlier responses. Uses async/await pattern with message streaming to process AssistantMessage responses containing TextBlock content.

```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient, AssistantMessage, TextBlock, ResultMessage


async def main():
    async with ClaudeSDKClient() as client:
        # First question
        await client.query("What's the capital of France?")

        # Process response
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")

        # Follow-up question - the session retains the previous context
        await client.query("What's the population of that city?")

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")

        # Another follow-up - still in the same conversation
        await client.query("What are some famous landmarks there?")

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")


asyncio.run(main())
````

---

### Bash Tool Input/Output Schema

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the input and output schemas for the Bash tool in Claude Agent SDK. Executes shell commands with optional timeout, background execution, and description parameters, returning output, exit code, and shell information.

```python
# Bash Tool Input
{
    "command": str,  # The command to execute
    "timeout": int | None,  # Optional timeout in milliseconds (max 600000)
    "description": str | None,  # Clear, concise description (5-10 words)
    "run_in_background": bool | None,  # Set to true to run in background
}

# Bash Tool Output
{
    "output": str,  # Combined stdout and stderr output
    "exitCode": int,  # Exit code of the command
    "killed": bool | None,  # Whether command was killed due to timeout
    "shellId": str | None,  # Shell ID for background processes
}
```

---

### Detect Failed MCP Server Connections from System Init Message

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

This snippet shows how to specifically identify and log MCP servers that failed to connect by inspecting the `status` field within the `system` message of subtype `init`. This allows for early diagnosis of connection issues before the agent attempts to use the server.

```typescript
if (message.type === "system" && message.subtype === "init") {
  for (const server of message.mcp_servers) {
    if (server.status === "failed") {
      console.error(`Server ${server.name} failed to connect`);
    }
  }
}
```

---

### SdkPluginConfig Type Definition

Source: https://docs.claude.com/en/api/agent-sdk/python

Configuration for loading plugins in the SDK. Currently supports local plugins with absolute or relative paths. Use this to extend SDK functionality with custom plugins.

````APIDOC
## SdkPluginConfig

### Description
Configuration for loading plugins in the SDK. Currently supports local plugins with absolute or relative paths.

### Type Definition
```python
class SdkPluginConfig(TypedDict):
    type: Literal["local"]
    path: str
````

### Fields

| Field  | Type               | Description                                                |
| ------ | ------------------ | ---------------------------------------------------------- |
| `type` | `Literal["local"]` | Must be `"local"` (only local plugins currently supported) |
| `path` | `str`              | Absolute or relative path to the plugin directory          |

### Example

```python
plugins = [
    {"type": "local", "path": "./my-plugin"},
    {"type": "local", "path": "/absolute/path/to/plugin"}
]
```

````

--------------------------------

### Define SandboxIgnoreViolations TypedDict

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the configuration structure for ignoring specific sandbox violations by file path patterns and network patterns. This allows selective exemption of resources from sandbox enforcement while maintaining security for other resources.

```python
class SandboxIgnoreViolations(TypedDict, total=False):
    file: list[str]
    network: list[str]
````

---

### unstable_v2_resumeSession()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Resumes an existing session by ID.

```APIDOC
## SDK Function unstable_v2_resumeSession()

### Description
Resumes an existing session by ID.

### Method
SDK Function

### Parameters
- **sessionId** (string) - Required - The ID of the session to resume.

#### Request Body
- **model** (string) - Required - The model to use for the session. Additional options are supported but not detailed here.

### Request Example
{
  "sessionId": "your-existing-session-id",
  "model": "claude-opus-4-6"
}

### Response
#### Success Response (SDKSession object)
- **sessionId** (string) - The unique identifier for the resumed session.
- **send** (function) - A method to send messages to the session.
- **stream** (function) - A method to stream messages from the session.
- **close** (function) - A method to close the session.

#### Response Example
{
  "sessionId": "your-existing-session-id",
  "send": "[function]",
  "stream": "[function]",
  "close": "[function]"
}
```

---

### Define a Custom Tool for Claude Agent SDK in Python

Source: https://docs.claude.com/en/api/agent-sdk/python

The `SdkMcpTool` dataclass provides a structured way to define custom tools for the Claude Agent SDK. It requires a unique name, a human-readable description, an input schema for validation, and an asynchronous handler function for execution. Optional annotations can be added for specific tool behaviors.

```python
@dataclass
class SdkMcpTool(Generic[T]):
    name: str
    description: str
    input_schema: type[T] | dict[str, Any]
    handler: Callable[[T], Awaitable[dict[str, Any]]]
    annotations: ToolAnnotations | None = None
```

---

### CALL ExitPlanMode

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Exits planning mode. Optionally specifies prompt-based permissions needed to implement the plan.

```APIDOC
## CALL ExitPlanMode

### Description
Exits planning mode. Optionally specifies prompt-based permissions needed to implement the plan.

### Method
CALL

### Endpoint
ExitPlanMode

### Parameters
#### Path Parameters
N/A

#### Query Parameters
N/A

#### Request Body
- **allowedPrompts** (Array of objects) - Optional - An array of prompts, each specifying a tool and a prompt string.
  - **tool** (string, literal "Bash") - Required -
```

---

### Task Tool

Source: https://platform.claude.com/docs/en/agent-sdk/python

The Task tool allows agents to delegate work to specialized subagents. It accepts a task description and prompt, and returns the result along with usage statistics and execution metrics.

````APIDOC
## Task Tool

### Description
Delegates a task to a specialized subagent and returns the result with performance metrics.

### Tool Name
`Task`

### Input Parameters
- **description** (str) - Required - A short (3-5 word) description of the task
- **prompt** (str) - Required - The task for the agent to perform
- **subagent_type** (str) - Required - The type of specialized agent to use

### Request Example
```python
{
    "description": "Analyze code quality",
    "prompt": "Review the provided codebase for performance issues",
    "subagent_type": "code_analyzer"
}
````

### Response

#### Success Response (200)

- **result** (str) - Final result from the subagent
- **usage** (dict | None) - Token usage statistics
- **total_cost_usd** (float | None) - Total cost in USD
- **duration_ms** (int | None) - Execution duration in milliseconds

#### Response Example

```python
{
    "result": "Analysis complete: Found 3 performance bottlenecks",
    "usage": {"input_tokens": 1500, "output_tokens": 800},
    "total_cost_usd": 0.045,
    "duration_ms": 2340
}
```

````

--------------------------------

### Allow Tool Execution with PermissionResultAllow

Source: https://docs.claude.com/en/api/agent-sdk/python

Dataclass indicating a tool call should be allowed, with optional modified input parameters and permission updates to apply. Default behavior is 'allow'.

```python
@dataclass
class PermissionResultAllow:
    behavior: Literal["allow"] = "allow"
    updated_input: dict[str, Any] | None = None
    updated_permissions: list[PermissionUpdate] | None = None
````

---

### Detect AskUserQuestion in canUseTool Callback

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This code illustrates how to identify when Claude calls the `AskUserQuestion` tool within your `canUseTool` callback. It shows conditional logic to delegate handling of clarifying questions to a specific function while processing other tools normally.

```python
async def can_use_tool(tool_name: str, input_data: dict, context):
    if tool_name == "AskUserQuestion":
        # Your implementation to collect answers from the user
        return await handle_clarifying_questions(input_data)
    # Handle other tools normally
    return await prompt_for_approval(tool_name, input_data)
```

```typescript
canUseTool: async (toolName, input) => {
  if (toolName === "AskUserQuestion") {
    // Your implementation to collect answers from the user
    return handleClarifyingQuestions(input);
  }
  // Handle other tools normally
  return promptForApproval(toolName, input);
};
```

---

### Define McpSSEServerConfig for Claude Agent SDK (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This `TypedDict` defines the configuration for an MCP server using Server-Sent Events (SSE). It requires a URL for the SSE endpoint and allows for optional custom HTTP headers. This enables real-time communication with the MCP server.

```python
class McpSSEServerConfig(TypedDict):
    type: Literal["sse"]
    url: str
    headers: NotRequired[dict[str, str]]
```

---

### Method ClaudeSDKClient.set_model

Source: https://platform.claude.com/docs/en/agent-sdk/python

Sets the AI model to be used for the current session.

````APIDOC
## METHOD ClaudeSDKClient.set_model

### Description
Sets the AI model to be used for the current session.

### Method
Async Class Method

### Endpoint
async def set_model(self, model: str | None = None) -> None

### Parameters
#### Request Body
- **model** (str | None) - Optional - The name of the model to use. If `None`, resets to default.

### Request Example
```python
# Assuming 'client' is an initialized ClaudeSDKClient instance
await client.set_model("claude-3-opus-20240229")
````

### Response

#### Success Response (200)

- **None** - The method returns nothing upon successful model setting.

#### Response Example

```python
# No explicit return value
```

````

--------------------------------

### ReadMcpResource Tool - Fetch MCP Resource Content

Source: https://docs.claude.com/en/api/agent-sdk/python

Reads content from a specific MCP resource identified by server name and URI. Returns resource contents with URI, MIME type, text, and optional blob data. Supports reading various resource types from configured MCP servers.

```json
{
  "server": "str",
  "uri": "str"
}
````

---

### Method ClaudeSDKClient.set_permission_mode

Source: https://platform.claude.com/docs/en/agent-sdk/python

Sets the permission mode for the current session.

````APIDOC
## METHOD ClaudeSDKClient.set_permission_mode

### Description
Sets the permission mode for the current session.

### Method
Async Class Method

### Endpoint
async def set_permission_mode(self, mode: str) -> None

### Parameters
#### Request Body
- **mode** (str) - Required - The permission mode to set (e.g., "strict", "permissive").

### Request Example
```python
# Assuming 'client' is an initialized ClaudeSDKClient instance
await client.set_permission_mode("strict")
````

### Response

#### Success Response (200)

- **None** - The method returns nothing upon successful mode setting.

#### Response Example

```python
# No explicit return value
```

````

--------------------------------

### ClaudeSDKClient - Continuous Conversation Interface

Source: https://docs.claude.com/en/api/agent-sdk/python

Advanced feature for building continuous conversation sessions with Claude. Maintains conversation context across multiple turns, supports task interruption, and session management.

```APIDOC
## ClaudeSDKClient - Continuous Conversation Interface

### Description
Advanced feature for building continuous conversation sessions with Claude. Maintains conversation context across multiple turns, supports task interruption, and session management.

### Class: ConversationSession

### Methods

#### __init__(options: ClaudeAgentOptions | None = None)
Initializes a new conversation session with optional configuration.

**Parameters:**
- **options** (ClaudeAgentOptions | None) - Optional - Configuration options for the Claude agent

#### async start()
Starts the interactive conversation loop.

**Features:**
- Maintains context across multiple turns
- Supports user commands: 'exit', 'interrupt', 'new'
- Streams responses from Claude
- Tracks conversation turn count

#### async client.connect()
Establishes connection to Claude agent.

#### async client.query(message: str)
Sends a message to Claude. Previous messages are retained in session context.

**Parameters:**
- **message** (string) - Required - User message to send

#### async client.receive_response()
Asynchronously receives and streams Claude's response.

**Yields:**
- **AssistantMessage** - Response message object containing content blocks

#### async client.interrupt()
Interrupts the current task execution.

#### async client.disconnect()
Closes the connection and ends the session.

### Configuration Example
```python
options = ClaudeAgentOptions(
  allowed_tools=["Read", "Write", "Bash"],
  permission_mode="acceptEdits"
)
````

### Usage Example

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
import asyncio

async def main():
  options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Bash"],
    permission_mode="acceptEdits"
  )
  session = ConversationSession(options)
  await session.start()

asyncio.run(main())
```

### Conversation Flow

1. User sends message: "Create a file called hello.py"
2. Claude processes and responds with action
3. User sends follow-up: "What's in that file?"
4. Claude remembers context and references the previously created file
5. User can continue with modifications: "Add a main function to it"
6. Claude maintains full conversation history and context

### Response Types

- **AssistantMessage** - Contains response content blocks
- **TextBlock** - Text content from Claude's response

### Commands

- **exit** - Quit the conversation
- **interrupt** - Stop current task
- **new** - Start fresh conversation session (clears context)

````

--------------------------------

### Edit Tool Input/Output Schema

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the input and output structure for the Edit tool, which modifies file contents. Input specifies the file path, text to replace, replacement text, and optional flag to replace all occurrences. Output confirms the operation with message, replacement count, and edited file path.

```json
{
  "input": {
    "file_path": "str",
    "old_string": "str",
    "new_string": "str",
    "replace_all": "bool | None"
  },
  "output": {
    "message": "str",
    "replacements": "int",
    "file_path": "str"
  }
}
````

---

### Data Structure: SandboxIgnoreViolations

Source: https://platform.claude.com/docs/en/agent-sdk/python

Specifies patterns for ignoring certain sandbox violations, allowing more granular control over sandbox enforcement for file and network operations.

````APIDOC
## Data Structure: SandboxIgnoreViolations

### Description
Specifies patterns for ignoring certain sandbox violations, allowing more granular control over sandbox enforcement for file and network operations.

### Method
TypedDict Definition

### Endpoint
N/A

### Parameters
#### Request Body
- **file** (list[str]) - Optional - Default: `[]` - A list of file path patterns for which sandbox violations should be ignored.
- **network** (list[str]) - Optional - Default: `[]` - A list of network patterns for which sandbox violations should be ignored.

### Request Example
```json
{
  "file": [
    "/tmp/ignore_me/*"
  ],
  "network": [
    "192.168.1.100:8080"
  ]
}
````

### Response

N/A (This is a configuration object, not an API response.)

### Response Example

N/A

````

--------------------------------

### Define `McpSdkServerConfigWithInstance` Type in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the `McpSdkServerConfigWithInstance` type for configuring an SDK-based MCP server with an existing instance. It specifies a `name` for the server and requires an `instance` of `McpServer`, with the `type` field set to 'sdk'.

```typescript
type McpSdkServerConfigWithInstance = {
  type: "sdk";
  name: string;
  instance: McpServer;
};
````

---

### Allow tool execution in Python `can_use_tool`

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This Python snippet demonstrates how to explicitly allow a tool to execute within the `can_use_tool` callback. It shows returning a `PermissionResultAllow` object, which can optionally include an `updated_input` if the tool's parameters need to be modified before execution.

```python
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

# Allow the tool to execute
return PermissionResultAllow(updated_input=input_data)
```

---

### Define AskUserQuestion Tool Output Type (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the `AskUserQuestionOutput` type. This type returns an array of `questions` posed to the user, each with a question string, header, options, and a multi-select flag. It also includes a `answers` record mapping question identifiers to user responses.

```typescript
type AskUserQuestionOutput = {
  questions: Array<{
    question: string;
    header: string;
    options: Array<{ label: string; description: string }>;
    multiSelect: boolean;
  }>;
  answers: Record<string, string>;
};
```

---

### tool()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Creates a type-safe MCP tool definition for use with SDK MCP servers.

````APIDOC
## Function tool()

### Description
Creates a type-safe MCP tool definition for use with SDK MCP servers.

### Method
Function

### Endpoint
tool()

### Parameters
#### Path Parameters
(None)

#### Query Parameters
(None)

#### Request Body
- **name** (string) - Required - The name of the tool
- **description** (string) - Required - A description of what the tool does
- **inputSchema** (Schema extends AnyZodRawShape) - Required - Zod schema defining the tool's input parameters (supports both Zod 3 and Zod 4)
- **handler** ((args, extra) => Promise<CallToolResult>) - Required - Async function that executes the tool logic
- **extras** ({ annotations?: ToolAnnotations }) - Optional - Optional extra configuration including MCP tool annotations (e.g., `readOnly`, `destructive`, `openWorld`)

### Request Example
```typescript
import { tool, z } from "@anthropic-ai/claude-agent-sdk";

const myTool = tool(
  "getCurrentWeather",
  "Gets the current weather for a location",
  z.object({
    location: z.string().describe("The city and state, e.g. San Francisco, CA")
  }),
  async (args) => {
    // Tool logic here
    return { type: "success", result: { temperature: 72, unit: "fahrenheit" } };
  }
);
````

### Response

#### Success Response (Returns SdkMcpToolDefinition<Schema>)

- **SdkMcpToolDefinition<Schema>** (object) - A type-safe MCP tool definition.

#### Response Example

```json
{
  "name": "getCurrentWeather",
  "description": "Gets the current weather for a location",
  "input_schema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "The city and state, e.g. San Francisco, CA"
      }
    },
    "required": ["location"]
  }
}
```

````

--------------------------------

### Define Sandbox Filesystem Configuration Type (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

This TypeScript type specifies the configuration for filesystem access within a sandboxed environment. It allows defining patterns to explicitly permit or deny read and write operations on specific file paths.

```typescript
type SandboxFilesystemConfig = {
  allowWrite?: string[];
  denyWrite?: string[];
  denyRead?: string[];
};
````

---

### Manual Session Cleanup for Older TypeScript Versions

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Provides manual session cleanup pattern for TypeScript versions prior to 5.2 or when await using is not available. Requires explicit session.close() call to release resources after use.

```typescript
import { unstable_v2_createSession } from "@anthropic-ai/claude-agent-sdk";

const session = unstable_v2_createSession({
  model: "claude-opus-4-6",
});
// ... use the session ...
session.close();
```

---

### Define OutputFormat Dictionary for Claude Agent SDK

Source: https://docs.claude.com/en/api/agent-sdk/python

This snippet illustrates the expected dictionary structure for configuring structured output validation using `OutputFormat`. It specifies that the output type must be `json_schema` and requires a JSON Schema definition for validation. This configuration is passed to the `output_format` field of `ClaudeAgentOptions`.

```python
# Expected dict shape for output_format
{
    "type": "json_schema",
    "schema": {...},  # Your JSON Schema definition
}
```

---

### POST /tools/ReadMcpResource

Source: https://docs.claude.com/en/api/agent-sdk/python

Reads the contents of a specific MCP resource identified by server name and resource URI. Returns the resource content with optional MIME type and encoding information.

````APIDOC
## POST /tools/ReadMcpResource

### Description
Reads the contents of a specific MCP resource identified by server name and resource URI. Returns the resource content with optional MIME type and encoding information.

### Method
POST

### Endpoint
/tools/ReadMcpResource

### Tool Name
ReadMcpResource

### Parameters
#### Request Body
- **server** (string) - Required - The MCP server name
- **uri** (string) - Required - The resource URI to read

### Request Example
```json
{
  "server": "my-mcp-server",
  "uri": "resource://file1"
}
````

### Response

#### Success Response (200)

- **contents** (array) - Array of content objects
  - **uri** (string) - Resource URI
  - **mimeType** (string | null) - MIME type of the content
  - **text** (string | null) - Text content (if applicable)
  - **blob** (string | null) - Binary content encoded as base64 (if applicable)
- **server** (string) - MCP server name

#### Response Example

```json
{
  "contents": [
    {
      "uri": "resource://file1",
      "mimeType": "text/plain",
      "text": "Hello, World!",
      "blob": null
    }
  ],
  "server": "my-mcp-server"
}
```

````

--------------------------------

### Define KillBash Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

This snippet defines the input and output schema for the `KillBash` tool. It takes a `shell_id` to terminate a running background shell process. The tool returns a confirmation `message` and the `shell_id` of the killed shell.

```python
# Input
{
    "shell_id": str  # The ID of the background shell to kill
}

# Output
{
    "message": str,  # Success message
    "shell_id": str  # ID of the killed shell
}
````

---

### Define BashOutput Tool Input/Output Schema (Python)

Source: https://platform.claude.com/docs/en/agent-sdk/python

This snippet defines the input and output schema for the `BashOutput` tool. The tool is used to retrieve output from a background shell process identified by `bash_id`, optionally filtering lines with a regex. It returns the new output, the shell's current status (running, completed, or failed), and an `exitCode` if completed.

```python
# Input
{
    "bash_id": str,  # The ID of the background shell
    "filter": str | None  # Optional regex to filter output lines
}

# Output
{
    "output": str,  # New output since last check
    "status": "running" | "completed" | "failed",  # Current shell status
    "exitCode": int | None  # Exit code when completed
}
```

---

### Monitor Real-time Task Progress in Python

Source: https://docs.claude.com/en/api/agent-sdk/python

Stream and inspect agent messages in real-time to track task progress, including tool execution and completion. Iterates through AssistantMessage blocks to identify ToolUseBlock (tool invocations), ToolResultBlock (execution results), and TextBlock (Claude's responses). Useful for displaying live progress updates during long-running tasks.

```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ToolUseBlock,
    ToolResultBlock,
    TextBlock,
)
import asyncio


async def monitor_progress():
    options = ClaudeAgentOptions(
        allowed_tools=["Write", "Bash"], permission_mode="acceptEdits"
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Create 5 Python files with different sorting algorithms")

        # Monitor progress in real-time
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        if block.name == "Write":
                            file_path = block.input.get("file_path", "")
                            print(f"Creating: {file_path}")
                    elif isinstance(block, ToolResultBlock):
                        print("Completed tool execution")
                    elif isinstance(block, TextBlock):
                        print(f"Claude says: {block.text[:100]}...")

        print("Task completed!")


asyncio.run(monitor_progress())
```

---

### Query with Custom Tools and Allowed Tools Configuration

Source: https://platform.claude.com/docs/en/agent-sdk/custom-tools

Pass custom MCP servers to the query function using streaming input mode with an async generator. Configure allowed tools to control which tools Claude can access. The tool name format follows the pattern mcp**{server_name}**{tool_name}.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Use the custom tools in your query with streaming input
async function* generateMessages() {
  yield {
    type: "user" as const,
    message: {
      role: "user" as const,
      content: "What's the weather in San Francisco?",
    },
  };
}

for await (const message of query({
  prompt: generateMessages(), // Use async generator for streaming input
  options: {
    mcpServers: {
      "my-custom-tools": customServer, // Pass as object/dictionary, not array
    },
    // Optionally specify which tools Claude can use
    allowedTools: [
      "mcp__my-custom-tools__get_weather", // Allow the weather tool
      // Add other tools as needed
    ],
    maxTurns: 3,
  },
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}
```

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
import asyncio

# Use the custom tools with Claude
options = ClaudeAgentOptions(
    mcp_servers={"my-custom-tools": custom_server},
    allowed_tools=[
        "mcp__my-custom-tools__get_weather",  # Allow the weather tool
        # Add other tools as needed
    ],
)


async def main():
    async with ClaudeSDKClient(options=options) as client:
        await client.query("What's the weather in San Francisco?")

        # Extract and print response
        async for msg in client.receive_response():
            print(msg)


asyncio.run(main())
```

---

### Create utility functions for mathematical operations (Python/TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/file-checkpointing

This code defines a set of basic mathematical utility functions: `add`, `subtract`, `multiply`, and `divide`. The `divide` function includes error handling for division by zero. These files (`utils.py` or `utils.ts`) serve as the target for the Claude Agent SDK to demonstrate adding documentation comments.

```python
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

```typescript
export function add(a: number, b: number): number {
  return a + b;
}

export function subtract(a: number, b: number): number {
  return a - b;
}

export function multiply(a: number, b: number): number {
  return a * b;
}

export function divide(a: number, b: number): number {
  if (b === 0) {
    throw new Error("Cannot divide by zero");
  }
  return a / b;
}
```

---

### AgentDefinition

Source: https://docs.claude.com/en/api/agent-sdk/python

Configuration for defining a subagent programmatically, including its description, prompt, allowed tools, and model override.

````APIDOC
## AgentDefinition

### Description
Configuration for a subagent defined programmatically.

### Definition
```python
@dataclass
class AgentDefinition:
    description: str
    prompt: str
    tools: list[str] | None = None
    model: Literal["sonnet", "opus", "haiku", "inherit"] | None = None
````

### Fields

- **description** (str) - Required - Natural language description of when to use this agent
- **tools** (list[str] | None) - Optional - Array of allowed tool names. If omitted, inherits all tools
- **prompt** (str) - Required - The agent's system prompt
- **model** (Literal["sonnet", "opus", "haiku", "inherit"] | None) - Optional - Model override for this agent. If omitted, uses the main model

````

--------------------------------

### Define Subagents with Task Tool in Python and TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/subagents

Creates multiple subagents with different tool access levels and model configurations. The code-reviewer subagent has read-only access (Read, Grep, Glob tools) for security analysis, while the test-runner subagent includes Bash access for command execution. The Task tool must be included in allowedTools/allowed_tools to enable Claude to invoke subagents. Each subagent receives a description and prompt that define its behavior and expertise.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition


async def main():
    async for message in query(
        prompt="Review the authentication module for security issues",
        options=ClaudeAgentOptions(
            # Task tool is required for subagent invocation
            allowed_tools=["Read", "Grep", "Glob", "Task"],
            agents={
                "code-reviewer": AgentDefinition(
                    # description tells Claude when to use this subagent
                    description="Expert code review specialist. Use for quality, security, and maintainability reviews.",
                    # prompt defines the subagent's behavior and expertise
                    prompt="""You are a code review specialist with expertise in security, performance, and best practices.

When reviewing code:
- Identify security vulnerabilities
- Check for performance issues
- Verify adherence to coding standards
- Suggest specific improvements

Be thorough but concise in your feedback.""",
                    # tools restricts what the subagent can do (read-only here)
                    tools=["Read", "Grep", "Glob"],
                    # model overrides the default model for this subagent
                    model="sonnet",
                ),
                "test-runner": AgentDefinition(
                    description="Runs and analyzes test suites. Use for test execution and coverage analysis.",
                    prompt="""You are a test execution specialist. Run tests and provide clear analysis of results.

Focus on:
- Running test commands
- Analyzing test output
- Identifying failing tests
- Suggesting fixes for failures""",
                    # Bash access lets this subagent run test commands
                    tools=["Bash", "Read", "Grep"],
                ),
            },
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
````

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Review the authentication module for security issues",
  options: {
    // Task tool is required for subagent invocation
    allowedTools: ["Read", "Grep", "Glob", "Task"],
    agents: {
      "code-reviewer": {
        // description tells Claude when to use this subagent
        description:
          "Expert code review specialist. Use for quality, security, and maintainability reviews.",
        // prompt defines the subagent's behavior and expertise
        prompt: `You are a code review specialist with expertise in security, performance, and best practices.

When reviewing code:
- Identify security vulnerabilities
- Check for performance issues
- Verify adherence to coding standards
- Suggest specific improvements

Be thorough but concise in your feedback.`,
        // tools restricts what the subagent can do (read-only here)
        tools: ["Read", "Grep", "Glob"],
        // model overrides the default model for this subagent
        model: "sonnet",
      },
      "test-runner": {
        description:
          "Runs and analyzes test suites. Use for test execution and coverage analysis.",
        prompt: `You are a test execution specialist. Run tests and provide clear analysis of results.

Focus on:
- Running test commands
- Analyzing test output
- Identifying failing tests
- Suggesting fixes for failures`,
        // Bash access lets this subagent run test commands
        tools: ["Bash", "Read", "Grep"],
      },
    },
  },
})) {
  if ("result" in message) console.log(message.result);
}
```

---

### TOOL Task

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the input and output structure for the 'Task' tool, used for delegating and managing subagent tasks.

```APIDOC
## TOOL /tools/Task

### Description
A tool for defining and executing tasks with subagents.

### Method
TOOL

### Endpoint
/tools/Task

### Parameters
#### Path Parameters
- No path parameters.

#### Query Parameters
- No query parameters.

#### Request Body
- **description** (string) - Required - A short (3-5 word) description of the task
- **prompt** (string) - Required - The task for the agent to perform
- **subagent_type** (string) - Required - The type of specialized agent to use

### Request Example
{
  "description": "Analyze codebase for vulnerabilities",
  "prompt": "Scan the 'src' directory for common security flaws and report findings.",
  "subagent_type": "SecurityAnalyst"
}

### Response
#### Success Response (200)
- **result** (string) - Final result from the subagent
- **usage** (object | null) - Token usage statistics
- **total_cost_usd** (number | null) - Total cost in USD
- **duration_ms** (integer | null) - Execution duration in milliseconds

#### Response Example
{
  "result": "No critical vulnerabilities found in 'src' directory.",
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 50
  },
  "total_cost_usd": 0.0025,
  "duration_ms": 15000
}
```

---

### BaseHookInput - Foundation Hook Type

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the base fields present in all hook input types. This serves as the foundation for all other hook input structures, providing essential session and context information.

````APIDOC
## BaseHookInput

### Description
Base fields present in all hook input types. This TypedDict serves as the parent structure for all hook event inputs.

### Structure
```python
class BaseHookInput(TypedDict):
    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: NotRequired[str]
````

### Fields

- **session_id** (str) - Required - Current session identifier
- **transcript_path** (str) - Required - Path to the session transcript file
- **cwd** (str) - Required - Current working directory
- **permission_mode** (str) - Optional - Current permission mode

````

--------------------------------

### Define SandboxNetworkConfig TypedDict

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the network-specific configuration structure for sandbox mode with properties controlling local binding, Unix socket access, and proxy settings. This TypedDict is used to configure network policies for sandboxed processes, with all properties being optional.

```python
class SandboxNetworkConfig(TypedDict, total=False):
    allowLocalBinding: bool
    allowUnixSockets: list[str]
    allowAllUnixSockets: bool
    httpProxyPort: int
    socksProxyPort: int
````

---

### Explicitly Invoke a Claude Subagent in Prompt (Text)

Source: https://platform.claude.com/docs/en/agent-sdk/subagents

This snippet demonstrates how to explicitly instruct Claude to use a specific subagent by mentioning its name directly in the prompt. This method bypasses automatic subagent matching and guarantees the named subagent is invoked.

```text
"Use the code-reviewer agent to check the authentication module"
```

---

### Implement Custom Permission Handler for Tool Execution

Source: https://docs.claude.com/en/api/agent-sdk/python

Demonstrates advanced permission control using a custom handler function that validates and modifies tool execution requests. The handler can deny operations (e.g., system directory writes), redirect file paths to safe locations, or allow operations with modified inputs. Returns PermissionResultAllow or PermissionResultDeny based on security policies.

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)


async def custom_permission_handler(
    tool_name: str, input_data: dict, context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    """Custom logic for tool permissions."""

    # Block writes to system directories
    if tool_name == "Write" and input_data.get("file_path", "").startswith("/system/"):
        return PermissionResultDeny(
            message="System directory write not allowed", interrupt=True
        )

    # Redirect sensitive file operations
    if tool_name in ["Write", "Edit"] and "config" in input_data.get("file_path", ""):
        safe_path = f"./sandbox/{input_data['file_path']}"
        return PermissionResultAllow(
            updated_input={**input_data, "file_path": safe_path}
        )

    # Allow everything else
    return PermissionResultAllow(updated_input=input_data)


async def main():
    options = ClaudeAgentOptions(
        can_use_tool=custom_permission_handler, allowed_tools=["Read", "Write", "Edit"]
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Update the system config file")

        async for message in client.receive_response():
            # Will use sandbox path instead
            print(message)


asyncio.run(main())
```

---

### Set Claude Agent SDK Permission Mode at Query Time (Python, TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/permissions

This snippet demonstrates how to configure the permission mode for the Claude Agent SDK when initiating a new query. The specified mode, such as "default", will apply for the entire session unless it is explicitly changed later. This is done by passing `permission_mode` (Python) or `permissionMode` (TypeScript) within the `ClaudeAgentOptions` object.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    async for message in query(
        prompt="Help me refactor this code",
        options=ClaudeAgentOptions(
            permission_mode="default",  # Set the mode here
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

async function main() {
  for await (const message of query({
    prompt: "Help me refactor this code",
    options: {
      permissionMode: "default", // Set the mode here
    },
  })) {
    if ("result" in message) {
      console.log(message.result);
    }
  }
}

main();
```

---

### Define Agent SDK Control Initialization Response Type (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

The `SDKControlInitializeResponse` type specifies the structure of the data returned by the `initializationResult()` method. It encapsulates essential session startup information, including a list of available slash commands, agent details, current and available output styles, supported models, and the user's account information. This type is crucial for understanding the initial state and capabilities of an Agent SDK session.

```typescript
type SDKControlInitializeResponse = {
  commands: SlashCommand[];
  agents: AgentInfo[];
  output_style: string;
  available_output_styles: string[];
  models: ModelInfo[];
  account: AccountInfo;
};
```

---

### Update Permissions Programmatically with PermissionUpdate

Source: https://docs.claude.com/en/api/agent-sdk/python

Dataclass for applying permission updates including adding/replacing/removing rules, setting permission modes, managing directories, and specifying update destination (user/project/local settings or session).

```python
@dataclass
class PermissionUpdate:
    type: Literal[
        "addRules",
        "replaceRules",
        "removeRules",
        "setMode",
        "addDirectories",
        "removeDirectories",
    ]
    rules: list[PermissionRuleValue] | None = None
    behavior: Literal["allow", "deny", "ask"] | None = None
    mode: PermissionMode | None = None
    directories: list[str] | None = None
    destination: (
        Literal["userSettings", "projectSettings", "localSettings", "session"] | None
    ) = None
```

---

### PreCompactHookInput Type

Source: https://docs.claude.com/en/api/agent-sdk/python

Input data for PreCompact hook events. Triggered before transcript compaction, allowing handlers to prepare for or customize the compaction process.

```APIDOC
## PreCompactHookInput

### Description
Input data provided to PreCompact hook handlers. Triggered before the agent compacts its transcript, containing information about what triggered the compaction.

### Type Definition
```

class PreCompactHookInput(BaseHookInput):
hook_event_name: Literal["PreCompact"]
trigger: Literal["manual", "auto"]
custom_instructions: str | None

```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `hook_event_name` | `Literal["PreCompact"]` | Yes | Always "PreCompact" |
| `trigger` | `Literal["manual", "auto"]` | Yes | What triggered the compaction (manual or automatic) |
| `custom_instructions` | `str \| None` | No | Custom instructions for compaction |

### Inherited Fields
Inherits all fields from BaseHookInput: `session_id`, `transcript_path`, `cwd`, `permission_mode`
```

---

### Troubleshoot Missing Skills: Verify Working Directory (cwd) in Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/skills

This snippet demonstrates the importance of correctly setting the `cwd` (current working directory) option. Skills are loaded relative to this path, so `cwd` must point to a directory containing the `.claude/skills/` structure for Skills to be discovered and loaded by the SDK.

```python
# Ensure your cwd points to the directory containing .claude/skills/
options = ClaudeAgentOptions(
    cwd="/path/to/project",  # Must contain .claude/skills/
    setting_sources=["user", "project"],  # Required to load Skills
    allowed_tools=["Skill"],
)
```

```typescript
// Ensure your cwd points to the directory containing .claude/skills/
const options = {
  cwd: "/path/to/project", // Must contain .claude/skills/
  settingSources: ["user", "project"], // Required to load Skills
  allowedTools: ["Skill"],
};
```

---

### Dynamically Change Permission Mode

Source: https://platform.claude.com/docs/en/agent-sdk/permissions

This section explains how to change the permission mode mid-session using `set_permission_mode()` (Python) or `setPermissionMode()` (TypeScript). The new mode takes effect immediately for all subsequent tool requests.

````APIDOC
## SDK Function: set_permission_mode() / setPermissionMode() - Dynamically Change Permission Mode

### Description
This SDK function allows for dynamically changing the permission mode of an active Claude Agent session. The new mode takes effect immediately for all subsequent tool requests within that session.

### Method
SDK Function Call

### Endpoint
`q.set_permission_mode()` (Python) \n`q.setPermissionMode()` (TypeScript)

### Parameters
#### Request Body
- **mode** (string) - Required - The new permission mode to apply. Valid values include `default`, `dontAsk`, `acceptEdits`, `bypassPermissions`, `plan`.

### Request Example
```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    q = query(
        prompt="Help me refactor this code",
        options=ClaudeAgentOptions(
            permission_mode="default",  # Start in default mode
        ),
    )

    # Change mode dynamically mid-session
    await q.set_permission_mode("acceptEdits")

    # Process messages with the new permission mode
    async for message in q:
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
````

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

async function main() {
  const q = query({
    prompt: "Help me refactor this code",
    options: {
      permissionMode: "default", // Start in default mode
    },
  });

  // Change mode dynamically mid-session
  await q.setPermissionMode("acceptEdits");

  // Process messages with the new permission mode
  for await (const message of q) {
    if ("result" in message) {
      console.log(message.result);
    }
  }
}

main();
```

### Response

#### Success Response (No direct return value for mode change)

The function call itself does not return a value. The effect is observed in subsequent tool requests within the agent's session.

#### Response Example

(No direct response body for this operation)

````

--------------------------------

### Implement Robust API Data Fetching Tool with Error Handling

Source: https://platform.claude.com/docs/en/agent-sdk/custom-tools

This snippet demonstrates how to create a tool for fetching data from an external API, showcasing robust error handling practices in both TypeScript and Python. It includes `try-catch` (TypeScript) or `try-except` (Python) blocks to manage network errors and checks `response.ok` or `response.status` to handle non-successful HTTP responses. The tool returns structured error messages or the fetched data, formatted for readability.

```typescript
tool(
  "fetch_data",
  "Fetch data from an API",
  {
    endpoint: z.string().url().describe("API endpoint URL")
  },
  async (args) => {
    try {
      const response = await fetch(args.endpoint);

      if (!response.ok) {
        return {
          content: [
            {
              type: "text",
              text: `API error: ${response.status} ${response.statusText}`
            }
          ]
        };
      }

      const data = await response.json();
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(data, null, 2)
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Failed to fetch data: ${error.message}`
          }
        ]
      };
    }
  }
);
````

```python
import json
import aiohttp
from typing import Any


@tool(
    "fetch_data",
    "Fetch data from an API",
    {"endpoint": str},  # Simple schema
)
async def fetch_data(args: dict[str, Any]) -> dict[str, Any]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(args["endpoint"]) as response:
                if response.status != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"API error: {response.status} {response.reason}",
                            }
                        ]
                    }

                data = await response.json()
                return {
                    "content": [{"type": "text", "text": json.dumps(data, indent=2)}]
                }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Failed to fetch data: {str(e)}"}]
        }
```

---

### Define ConfigChangeHookInput Type in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the input type for configuration change hook events. Extends BaseHookInput with source (user_settings, project_settings, local_settings, policy_settings, or skills) and optional file_path. Triggered when configuration changes occur.

```typescript
type ConfigChangeHookInput = BaseHookInput & {
  hook_event_name: "ConfigChange";
  source:
    | "user_settings"
    | "project_settings"
    | "local_settings"
    | "policy_settings"
    | "skills";
  file_path?: string;
};
```

---

### Query Object Interface

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

The Query object is an AsyncGenerator that represents an active query session with Claude. It provides methods to control the query execution, manage models and permissions, interact with MCP servers, and retrieve system information.

````APIDOC
## Query Object Interface

### Description
Interface returned by the `query()` function. Extends AsyncGenerator<SDKMessage, void> and provides methods for managing Claude interactions, permissions, models, and MCP servers.

### Type Definition
```typescript
interface Query extends AsyncGenerator<SDKMessage, void> {
  interrupt(): Promise<void>;
  rewindFiles(
    userMessageId: string,
    options?: { dryRun?: boolean }
  ): Promise<RewindFilesResult>;
  setPermissionMode(mode: PermissionMode): Promise<void>;
  setModel(model?: string): Promise<void>;
  setMaxThinkingTokens(maxThinkingTokens: number | null): Promise<void>;
  initializationResult(): Promise<SDKControlInitializeResponse>;
  supportedCommands(): Promise<SlashCommand[]>;
  supportedModels(): Promise<ModelInfo[]>;
  supportedAgents(): Promise<AgentInfo[]>;
  mcpServerStatus(): Promise<McpServerStatus[]>;
  accountInfo(): Promise<AccountInfo>;
  reconnectMcpServer(serverName: string): Promise<void>;
  toggleMcpServer(serverName: string, enabled: boolean): Promise<void>;
  setMcpServers(servers: Record<string, McpServerConfig>): Promise<McpSetServersResult>;
  streamInput(stream: AsyncIterable<SDKUserMessage>): Promise<void>;
  stopTask(taskId: string): Promise<void>;
  close(): void;
}
````

### Methods

#### interrupt()

- **Description**: Interrupts the query execution
- **Availability**: Only available in streaming input mode
- **Returns**: `Promise<void>`

#### rewindFiles(userMessageId, options?)

- **Parameters**:
  - `userMessageId` (string) - Required - The ID of the user message to rewind to
  - `options` (object) - Optional - Configuration object
    - `dryRun` (boolean) - Optional - Preview changes without applying them
- **Description**: Restores files to their state at the specified user message
- **Requirements**: Requires `enableFileCheckpointing: true`
- **Returns**: `Promise<RewindFilesResult>`

#### setPermissionMode(mode)

- **Parameters**:
  - `mode` (PermissionMode) - Required - The new permission mode
- **Description**: Changes the permission mode for the query
- **Availability**: Only available in streaming input mode
- **Returns**: `Promise<void>`

#### setModel(model?)

- **Parameters**:
  - `model` (string) - Optional - The model identifier to switch to
- **Description**: Changes the model used for the query
- **Availability**: Only available in streaming input mode
- **Returns**: `Promise<void>`

#### setMaxThinkingTokens(maxThinkingTokens)

- **Parameters**:
  - `maxThinkingTokens` (number | null) - Required - Maximum thinking tokens or null to disable
- **Description**: Changes the maximum thinking tokens
- **Deprecated**: Use the `thinking` configuration option instead
- **Returns**: `Promise<void>`

#### initializationResult()

- **Description**: Returns the full initialization result including supported commands, models, account info, and output style configuration
- **Returns**: `Promise<SDKControlInitializeResponse>`

#### supportedCommands()

- **Description**: Returns available slash commands
- **Returns**: `Promise<SlashCommand[]>`

#### supportedModels()

- **Description**: Returns available models with display information
- **Returns**: `Promise<ModelInfo[]>`

#### supportedAgents()

- **Description**: Returns available subagents
- **Returns**: `Promise<AgentInfo[]>`

#### mcpServerStatus()

- **Description**: Returns status of connected MCP servers
- **Returns**: `Promise<McpServerStatus[]>`

#### accountInfo()

- **Description**: Returns account information
- **Returns**: `Promise<AccountInfo>`

#### reconnectMcpServer(serverName)

- **Parameters**:
  - `serverName` (string) - Required - Name of the MCP server to reconnect
- **Description**: Reconnect an MCP server by name
- **Returns**: `Promise<void>`

#### toggleMcpServer(serverName, enabled)

- **Parameters**:
  - `serverName` (string) - Required - Name of the MCP server
  - `enabled` (boolean) - Required - Enable or disable the server
- **Description**: Enable or disable an MCP server by name
- **Returns**: `Promise<void>`

#### setMcpServers(servers)

- **Parameters**:
  - `servers` (Record<string, McpServerConfig>) - Required - Configuration for MCP servers
- **Description**: Dynamically replace the set of MCP servers for this session
- **Returns**: `Promise<McpSetServersResult>` - Info about added, removed servers and any errors

#### streamInput(stream)

- **Parameters**:
  - `stream` (AsyncIterable<SDKUserMessage>) - Required - Stream of user messages
- **Description**: Stream input messages to the query for multi-turn conversations
- **Returns**: `Promise<void>`

#### stopTask(taskId)

- **Parameters**:
  - `taskId` (string) - Required - ID of the background task to stop
- **Description**: Stop a running background task by ID
- **Returns**: `Promise<void>`

#### close()

- **Description**: Close the query and terminate the underlying process. Forcefully ends the query and cleans up all resources
- **Returns**: `void`

````

--------------------------------

### Create New Session with unstable_v2_createSession()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Creates a new session for multi-turn conversations with the Claude Agent SDK. Accepts configuration options including model specification and returns an SDKSession instance for managing the conversation.

```typescript
function unstable_v2_createSession(options: {
  model: string;
  // Additional options supported
}): SDKSession;
````

---

### Configure allowedTools for Claude Agent SDK in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

This snippet demonstrates how to configure the `allowedTools` option within the Claude Agent SDK. By specifying a glob pattern like `"mcp__servername__*"`, you grant Claude permission to use tools from a particular MCP server, which is essential for enabling tool usage and preventing issues where tools are not called.

```typescript
const _ = {
  options: {
    mcpServers: {
      // your servers
    },
    allowedTools: ["mcp__servername__*"], // Required for Claude to use the tools
  },
};
```

---

### Define SpawnOptions Interface for Process Spawning in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the `SpawnOptions` TypeScript interface, which specifies the options passed to a custom spawn function. It includes the command to execute, arguments, an optional current working directory, environment variables, and an `AbortSignal` for cancellation.

```typescript
interface SpawnOptions {
  command: string;
  args: string[];
  cwd?: string;
  env: Record<string, string | undefined>;
  signal: AbortSignal;
}
```

---

### Parse User Response as Option Number or Free Text - Python

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

Utility function that parses user input to handle both numeric option selection and free text responses. Converts comma-separated numbers to option labels or returns the raw text input. Used to normalize user choices before storing answers.

```python
def parse_response(response: str, options: list) -> str:
    """Parse user input as option number(s) or free text."""
    try:
        indices = [int(s.strip()) - 1 for s in response.split(",")]
        labels = [options[i]["label"] for i in indices if 0 <= i < len(options)]
        return ", ".join(labels) if labels else response
    except ValueError:
        return response
```

---

### Task Tool Input/Output Schema

Source: https://platform.claude.com/docs/en/agent-sdk/python

Defines the input and output schemas for the Task tool in Claude Agent SDK. The Task tool executes specialized agent operations with a description, prompt, and subagent type, returning results with token usage and execution metrics.

```python
# Task Tool Input
{
    "description": str,  # A short (3-5 word) description of the task
    "prompt": str,  # The task for the agent to perform
    "subagent_type": str,  # The type of specialized agent to use
}

# Task Tool Output
{
    "result": str,  # Final result from the subagent
    "usage": dict | None,  # Token usage statistics
    "total_cost_usd": float | None,  # Total cost in USD
    "duration_ms": int | None,  # Execution duration in milliseconds
}
```

---

### Break Down Token Usage and Cost Per Model in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/cost-tracking

This snippet illustrates how to access and display detailed token usage and cost information for each model used within a single `query()` call. It iterates through the `modelUsage` map in the result message, providing insights into where tokens and costs are allocated, especially useful in multi-model scenarios.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({ prompt: "Summarize this project" })) {
  if (message.type !== "result") continue;

  for (const [modelName, usage] of Object.entries(message.modelUsage)) {
    console.log(`${modelName}: $${usage.costUSD.toFixed(4)}`);
    console.log(`  Input tokens: ${usage.inputTokens}`);
    console.log(`  Output tokens: ${usage.outputTokens}`);
    console.log(`  Cache read: ${usage.cacheReadInputTokens}`);
    console.log(`  Cache creation: ${usage.cacheCreationInputTokens}`);
  }
}
```

---

### Define ToolPermissionContext dataclass

Source: https://platform.claude.com/docs/en/agent-sdk/python

Dataclass that encapsulates context information passed to tool permission callbacks. Contains an optional abort signal (reserved for future use) and a list of permission update suggestions from the CLI.

```python
@dataclass
class ToolPermissionContext:
    signal: Any | None = None  # Future: abort signal support
    suggestions: list[PermissionUpdate] = field(default_factory=list)
```

---

### PermissionResultAllow

Source: https://docs.claude.com/en/api/agent-sdk/python

Indicates that a tool call should be allowed. It can optionally provide modified input or permission updates.

````APIDOC
## PermissionResultAllow

### Description
Result indicating the tool call should be allowed. This object can also specify modified input or permission updates to apply.

### Definition
```python
@dataclass
class PermissionResultAllow:
    behavior: Literal["allow"] = "allow"
    updated_input: dict[str, Any] | None = None
    updated_permissions: list[PermissionUpdate] | None = None
````

### Fields

- **behavior** (Literal["allow"]) - Default: "allow" - Must be "allow"
- **updated_input** (dict[str, Any] | None) - Default: None - Modified input to use instead of original
- **updated_permissions** (list[PermissionUpdate] | None) - Default: None - Permission updates to apply

````

--------------------------------

### Define Config Tool Input Type (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the input type for the `Config` tool. It requires a `setting` string to identify the configuration item and an optional `value` which can be a string, boolean, or number, used for setting the configuration.

```typescript
type ConfigInput = {
  setting: string;
  value?: string | boolean | number;
};

````

---

### Set Permission Mode at Query Time

Source: https://platform.claude.com/docs/en/agent-sdk/permissions

This section describes how to set the permission mode when initiating a new query with the Claude Agent SDK. The chosen mode will apply for the entire session unless dynamically changed later.

````APIDOC
## SDK Function: query() - Set Permission Mode

### Description
This SDK function initiates a new query with the Claude Agent and allows setting the initial permission mode for the session. The mode applies for the entire session unless explicitly changed dynamically.

### Method
SDK Function Call

### Endpoint
`query()`

### Parameters
#### Request Body
- **prompt** (string) - Required - The user's prompt for the Claude Agent.
- **options** (object) - Required - Configuration options for the query.
  - **permission_mode** (string) - Optional - Python: The permission mode to use for the session. Valid values include `default`, `dontAsk`, `acceptEdits`, `bypassPermissions`, `plan`.
  - **permissionMode** (string) - Optional - TypeScript: The permission mode to use for the session. Valid values include `default`, `dontAsk`, `acceptEdits`, `bypassPermissions`, `plan`.

### Request Example
```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    async for message in query(
        prompt="Help me refactor this code",
        options=ClaudeAgentOptions(
            permission_mode="default",  # Set the mode here
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
````

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

async function main() {
  for await (const message of query({
    prompt: "Help me refactor this code",
    options: {
      permissionMode: "default", // Set the mode here
    },
  })) {
    if ("result" in message) {
      console.log(message.result);
    }
  }
}

main();
```

### Response

#### Success Response (Stream of Messages)

- **message** (object) - A stream of messages from the Claude Agent. Each message object may contain a `result` field.
  - **result** (string) - The final result or output from the agent, if available in a message.

#### Response Example

````json
{
  "result": "Refactoring complete. Here's the updated code for main.py:\n\n```python\nimport os\n\ndef new_func():\n    print(\"Hello from new_func\")\n\nif __name__ == \"__main__\":\n    new_func()\n```"
}
````

---

### Stream Text Responses with Partial Messages

Source: https://platform.claude.com/docs/en/agent-sdk/streaming-output

Demonstrates how to stream and display text responses in real-time by listening for content_block_delta events with text_delta type. This implementation enables incremental text output as the model generates responses. Requires include_partial_messages (Python) or includePartialMessages (TypeScript) to be enabled in the query options.

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import StreamEvent
import asyncio


async def stream_text():
    options = ClaudeAgentOptions(include_partial_messages=True)

    async for message in query(prompt="Explain how databases work", options=options):
        if isinstance(message, StreamEvent):
            event = message.event
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    # Print each text chunk as it arrives
                    print(delta.get("text", ""), end="", flush=True)

    print()  # Final newline


asyncio.run(stream_text())
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Explain how databases work",
  options: { includePartialMessages: true },
})) {
  if (message.type === "stream_event") {
    const event = message.event;
    if (
      event.type === "content_block_delta" &&
      event.delta.type === "text_delta"
    ) {
      process.stdout.write(event.delta.text);
    }
  }
}

console.log(); // Final newline
```

---

### Resuming Sessions - TypeScript and Python

Source: https://platform.claude.com/docs/en/agent-sdk/sessions

Shows how to resume a previous session using its session ID with the `resume` option. The SDK automatically loads conversation history and context, allowing Claude to continue from the exact point where it left off with full context preservation.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Resume a previous session using its ID
const response = query({
  prompt:
    "Continue implementing the authentication system from where we left off",
  options: {
    resume: "session-xyz", // Session ID from previous conversation
    model: "claude-opus-4-6",
    allowedTools: ["Read", "Edit", "Write", "Glob", "Grep", "Bash"],
  },
});

// The conversation continues with full context from the previous session
for await (const message of response) {
  console.log(message);
}
```

```python
from claude_agent_sdk import query, ClaudeAgentOptions

# Resume a previous session using its ID
async for message in query(
    prompt="Continue implementing the authentication system from where we left off",
    options=ClaudeAgentOptions(
        resume="session-xyz",  # Session ID from previous conversation
        model="claude-opus-4-6",
        allowed_tools=["Read", "Edit", "Write", "Glob", "Grep", "Bash"],
    ),
):
    print(message)

# The conversation continues with full context from the previous session
```

---

### Define BaseHookInput TypedDict

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the base fields common to all hook input types including session identifier, transcript path, working directory, and optional permission mode. All other hook input types inherit from this base.

```python
class BaseHookInput(TypedDict):
    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: NotRequired[str]
```

---

### Configure Claude Code to use proxy with ANTHROPIC_BASE_URL

Source: https://platform.claude.com/docs/en/agent-sdk/secure-deployment

Set the ANTHROPIC_BASE_URL environment variable to route sampling API requests through a proxy. This method is simple but only affects sampling requests to the Claude API. The proxy receives plaintext HTTP requests and can inspect, modify, and inject credentials before forwarding to the real API.

```bash
export ANTHROPIC_BASE_URL="http://localhost:8080"
```

---

### PermissionUpdate

Source: https://docs.claude.com/en/api/agent-sdk/python

Configuration for programmatically updating permissions, allowing various operations like adding/removing rules, setting modes, or modifying directories.

````APIDOC
## PermissionUpdate

### Description
Configuration for updating permissions programmatically. This allows for various operations such as adding, replacing, or removing rules, setting a permission mode, or modifying allowed directories.

### Definition
```python
@dataclass
class PermissionUpdate:
    type: Literal[
        "addRules",
        "replaceRules",
        "removeRules",
        "setMode",
        "addDirectories",
        "removeDirectories",
    ]
    rules: list[PermissionRuleValue] | None = None
    behavior: Literal["allow", "deny", "ask"] | None = None
    mode: PermissionMode | None = None
    directories: list[str] | None = None
    destination: (
        Literal["userSettings", "projectSettings", "localSettings", "session"] | None
    ) = None
````

### Fields

- **type** (Literal[...]) - Required - The type of permission update operation
- **rules** (list[PermissionRuleValue] | None) - Optional - Rules for add/replace/remove operations
- **behavior** (Literal["allow", "deny", "ask"] | None) - Optional - Behavior for rule-based operations
- **mode** (PermissionMode | None) - Optional - Mode for setMode operation
- **directories** (list[str] | None) - Optional - Directories for add/remove directory operations
- **destination** (Literal[...]) - Optional - Where to apply the permission update (e.g., user, project, local settings, or session)

````

--------------------------------

### Define SettingSource Literal for Claude Agent SDK

Source: https://docs.claude.com/en/api/agent-sdk/python

This Python `Literal` defines the allowed values for `SettingSource`, which controls which filesystem-based configuration sources the Claude Agent SDK loads settings from. The possible values are 'user', 'project', and 'local', corresponding to global, shared project, and local project settings respectively.

```python
SettingSource = Literal["user", "project", "local"]
````

---

### Method ClaudeSDKClient.receive_messages

Source: https://platform.claude.com/docs/en/agent-sdk/python

Asynchronously yields messages received from the Claude agent during the conversation.

````APIDOC
## METHOD ClaudeSDKClient.receive_messages

### Description
Asynchronously yields messages received from the Claude agent during the conversation.

### Method
Async Class Method

### Endpoint
async def receive_messages(self) -> AsyncIterator[Message]

### Parameters
#### Request Body
- No parameters.

### Request Example
```python
# Assuming 'client' is an initialized ClaudeSDKClient instance
async for message in client.receive_messages():
    print(message)
````

### Response

#### Success Response (200)

- **AsyncIterator[Message]** - An asynchronous iterator yielding `Message` objects.

#### Response Example

```json
{
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Paris."
    }
  ]
}
```

````

--------------------------------

### Define Sandbox Network Configuration Type (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

This TypeScript type defines the configuration options for network access within a sandboxed environment. It allows specifying allowed domains, controlling local port binding, and configuring HTTP/SOCKS proxies for sandboxed processes.

```typescript
type SandboxNetworkConfig = {
  allowedDomains?: string[];
  allowManagedDomainsOnly?: boolean;
  allowLocalBinding?: boolean;
  allowUnixSockets?: string[];
  allowAllUnixSockets?: boolean;
  httpProxyPort?: number;
  socksProxyPort?: number;
};
````

---

### Define UserPromptSubmitHookInput TypedDict

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the input structure for UserPromptSubmit hook events, triggered when a user submits a prompt. Contains the submitted prompt text along with inherited base fields.

```python
class UserPromptSubmitHookInput(BaseHookInput):
    hook_event_name: Literal["UserPromptSubmit"]
    prompt: str
```

---

### Automatic Session Cleanup with await using (TypeScript 5.2+)

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Demonstrates automatic resource cleanup for Claude Agent SDK sessions using TypeScript 5.2+ await using declaration. The session closes automatically when the block exits, eliminating the need for manual cleanup. Requires TypeScript 5.2 or later.

```typescript
import { unstable_v2_createSession } from "@anthropic-ai/claude-agent-sdk";

await using session = unstable_v2_createSession({
  model: "claude-opus-4-6",
});
// Session closes automatically when the block exits
```

---

### Resume Existing Session with unstable_v2_resumeSession()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Resumes a previously created session by its ID, allowing continuation of multi-turn conversations. Requires a valid sessionId and model configuration to restore the session state.

```typescript
function unstable_v2_resumeSession(
  sessionId: string,
  options: {
    model: string;
    // Additional options supported
  },
): SDKSession;
```

---

### Log File Changes with PostToolUse Hook

Source: https://platform.claude.com/docs/en/agent-sdk/overview

Implements a PostToolUse hook to audit file modifications by logging timestamps and file paths to an audit log. The hook intercepts Edit and Write tool operations and records them asynchronously. Useful for compliance and debugging purposes.

```python
import asyncio
from datetime import datetime
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher


async def log_file_change(input_data, tool_use_id, context):
    file_path = input_data.get("tool_input", {}).get("file_path", "unknown")
    with open("./audit.log", "a") as f:
        f.write(f"{datetime.now()}: modified {file_path}\n")
    return {}


async def main():
    async for message in query(
        prompt="Refactor utils.py to improve readability",
        options=ClaudeAgentOptions(
            permission_mode="acceptEdits",
            hooks={
                "PostToolUse": [
                    HookMatcher(matcher="Edit|Write", hooks=[log_file_change])
                ]
            },
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
```

```typescript
import { query, HookCallback } from "@anthropic-ai/claude-agent-sdk";
import { appendFile } from "fs/promises";

const logFileChange: HookCallback = async (input) => {
  const filePath = (input as any).tool_input?.file_path ?? "unknown";
  await appendFile(
    "./audit.log",
    `${new Date().toISOString()}: modified ${filePath}\n`,
  );
  return {};
};

for await (const message of query({
  prompt: "Refactor utils.py to improve readability",
  options: {
    permissionMode: "acceptEdits",
    hooks: {
      PostToolUse: [{ matcher: "Edit|Write", hooks: [logFileChange] }],
    },
  },
})) {
  if ("result" in message) console.log(message.result);
}
```

---

### PermissionResultDeny

Source: https://docs.claude.com/en/api/agent-sdk/python

Indicates that a tool call should be denied. It can include a message explaining the denial and whether to interrupt execution.

````APIDOC
## PermissionResultDeny

### Description
Result indicating the tool call should be denied. It provides a message for the denial and an option to interrupt the current execution.

### Definition
```python
@dataclass
class PermissionResultDeny:
    behavior: Literal["deny"] = "deny"
    message: str = ""
    interrupt: bool = False
````

### Fields

- **behavior** (Literal["deny"]) - Default: "deny" - Must be "deny"
- **message** (str) - Default: "" - Message explaining why the tool was denied
- **interrupt** (bool) - Default: False - Whether to interrupt the current execution

````

--------------------------------

### Modify Agent Input and Behavior (JavaScript)

Source: https://platform.claude.com/docs/en/agent-sdk/user-input

This JavaScript snippet demonstrates how to conditionally modify an agent's input and behavior. It shows a pattern where an agent's default action (e.g., file deletion) can be overridden with a user's preferred action (e.g., file compression) by returning an updated input string. Otherwise, the agent's behavior is allowed with the original input. This code fragment appears to be part of a larger function that processes agent input.

```javascript
"User doesn't want to delete files. They asked if you could compress them into an archive instead."
        };
      }
      return { behavior: "allow", updatedInput: input };
    };
````

---

### TOOL Edit

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the input and output structure for the 'Edit' tool, used for modifying file content by replacing specified strings.

```APIDOC
## TOOL /tools/Edit

### Description
Modifies a file by replacing a specified string with a new one.

### Method
TOOL

### Endpoint
/tools/Edit

### Parameters
#### Path Parameters
- No path parameters.

#### Query Parameters
- No query parameters.

#### Request Body
- **file_path** (string) - Required - The absolute path to the file to modify
- **old_string** (string) - Required - The text to replace
- **new_string** (string) - Required - The text to replace it with
- **replace_all** (boolean | null) - Optional - Replace all occurrences (default False)

### Request Example
{
  "file_path": "/app/src/main.py",
  "old_string": "DEBUG = True",
  "new_string": "DEBUG = False",
  "replace_all": false
}

### Response
#### Success Response (200)
- **message** (string) - Confirmation message
- **replacements** (integer) - Number of replacements made
- **file_path** (string) - File path that was edited

#### Response Example
{
  "message": "File updated successfully.",
  "replacements": 1,
  "file_path": "/app/src/main.py"
}
```

---

### Define SdkBeta Literal Type for Claude Agent SDK (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This literal type specifies available beta features for the SDK. It is used with the `betas` field in `ClaudeAgentOptions` to enable experimental functionalities. Developers can opt-in to test new features before general release.

```python
SdkBeta = Literal["context-1m-2025-08-07"]
```

---

### PermissionMode

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the available permission modes for controlling how tool execution is handled within the SDK.

````APIDOC
## PermissionMode

### Description
Permission modes for controlling tool execution.

### Definition
```python
PermissionMode = Literal[
    "default",  # Standard permission behavior
    "acceptEdits",  # Auto-accept file edits
    "plan",  # Planning mode - no execution
    "bypassPermissions",  # Bypass all permission checks (use with caution)
]
````

### Possible Values

- **"default"** - Standard permission behavior
- **"acceptEdits"** - Auto-accept file edits
- **"plan"** - Planning mode - no execution
- **"bypassPermissions"** - Bypass all permission checks (use with caution)

````

--------------------------------

### Configure Agent Hooks with Options Object - TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/hooks

Sets up hooks in TypeScript by passing an options object with hook configuration to the query function. The PreToolUse hook is configured with a matcher for Bash commands and a callback function. Messages are processed asynchronously using a for-await loop.

```typescript
for await (const message of query({
  prompt: "Your prompt",
  options: {
    hooks: {
      PreToolUse: [{ matcher: "Bash", hooks: [myCallback] }]
    }
  }
})) {
  console.log(message);
}
````

---

### query()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

The primary function for interacting with Claude Code. Creates an async generator that streams messages as they arrive.

````APIDOC
## Function query()

### Description
The primary function for interacting with Claude Code. Creates an async generator that streams messages as they arrive.

### Method
Function

### Endpoint
query()

### Parameters
#### Path Parameters
(None)

#### Query Parameters
(None)

#### Request Body
- **prompt** (string | AsyncIterable<SDKUserMessage>) - Required - The input prompt as a string or async iterable for streaming mode
- **options** (Options) - Optional - Optional configuration object (see Options type below)

### Request Example
```typescript
// Example of calling the query function
const response = query({
  prompt: "Hello Claude!",
  options: { /* ... */ }
});

for await (const message of response) {
  console.log(message);
}
````

### Response

#### Success Response (Returns Query object)

- **Query** (object) - An object that extends `AsyncGenerator<SDKMessage, void>` with additional methods.

#### Response Example

```json
{
  "type": "message_chunk",
  "content": "Hello! How can I help you today?"
}
```

````

--------------------------------

### Pass Credentials via Environment Variables to MCP Servers

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

Configure authentication credentials for MCP servers by passing environment variables through the env field in server configuration. This approach securely passes API keys and tokens from the runtime environment to the MCP server without hardcoding sensitive values.

```TypeScript
const _ = {
  options: {
    mcpServers: {
      github: {
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-github"],
        env: {
          GITHUB_TOKEN: process.env.GITHUB_TOKEN
        }
      }
    },
    allowedTools: ["mcp__github__list_issues"]
  }
};
````

```Python
options = ClaudeAgentOptions(
    mcp_servers={
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_TOKEN": os.environ["GITHUB_TOKEN"]},
        }
    },
    allowed_tools=["mcp__github__list_issues"],
)
```

```JSON
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

---

### Send Slash Commands with Claude Agent SDK (TypeScript/Python)

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

This snippet illustrates how to send a slash command, such as `/compact`, to a Claude Code session using the SDK. The command is included directly in the `prompt` string, and the result is processed when a message of type `result` is received.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

// Send a slash command
for await (const message of query({
  prompt: "/compact",
  options: { maxTurns: 1 },
})) {
  if (message.type === "result") {
    console.log("Command executed:", message.result);
  }
}
```

```python
import asyncio
from claude_agent_sdk import query


async def main():
    # Send a slash command
    async for message in query(prompt="/compact", options={"max_turns": 1}):
        if message.type == "result":
            print("Command executed:", message.result)


asyncio.run(main())
```

---

### Define Tool Use Request Block (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

Defines the `ToolUseBlock` dataclass, representing a request from the agent to use a specific tool. It includes a unique `id` for the tool use, the `name` of the tool, and a dictionary of `input` parameters for the tool's execution.

```python
@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
```

---

### Define Permission Request Hook Input Data Structure (Python)

Source: https://docs.claude.com/en/api/agent-sdk/python

This Python class specifies the input data structure for 'PermissionRequest' hook events. It allows hooks to programmatically handle permission decisions by providing details like the tool name requesting permission, its input parameters, and optional permission suggestions. This enables custom logic for granting or denying tool access.

```python
class PermissionRequestHookInput(BaseHookInput):
    hook_event_name: Literal["PermissionRequest"]
    tool_name: str
    tool_input: dict[str, Any]
    permission_suggestions: NotRequired[list[Any]]
```

---

### Client Method: receive_response()

Source: https://platform.claude.com/docs/en/agent-sdk/python

Receives messages from Claude until and including a `ResultMessage`. This method simplifies response handling by providing a stream that concludes when a final result is available.

````APIDOC
## Client Method: receive_response()

### Description
Receive messages until and including a ResultMessage. This method is useful for processing a complete turn of conversation.

### Method
receive_response

### Parameters
#### Arguments
- **None**

### Request Example
```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient, AssistantMessage, TextBlock

async def main():
    async with ClaudeSDKClient() as client:
        await client.query("What's the capital of France?")
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")

asyncio.run(main())
````

### Response

#### Return Value

- **Async Iterator** - An asynchronous iterator that yields message objects, similar to `receive_messages()`, but it will stop iterating once a `ResultMessage` (or equivalent final message) is encountered.

#### Response Example

```json
{
  "type": "message_start",
  "message": {
    "id": "msg_01A01B01C01D01E01F01G01H",
    "type": "message",
    "role": "assistant",
    "content": [],
    "model": "claude-3-opus-20240229",
    "stop_reason": null,
    "stop_sequence": null,
    "usage": {
      "input_tokens": 10,
      "output_tokens": 1
    }
  }
}
---
{
  "type": "content_block_delta",
  "index": 0,
  "delta": {
    "type": "text_delta",
    "text": "Paris"
  }
}
---
{
  "type": "message_stop",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "output_tokens": 5
  }
}
---
{
  "type": "result_message",
  "status": "success",
  "final_content": "Paris is the capital of France."
}
```

````

--------------------------------

### Method ClaudeSDKClient.get_mcp_status

Source: https://platform.claude.com/docs/en/agent-sdk/python

Retrieves the current status of the MCP (Multi-Cloud Platform) servers connected to the client.

```APIDOC
## METHOD ClaudeSDKClient.get_mcp_status

### Description
Retrieves the current status of the MCP (Multi-Cloud Platform) servers connected to the client.

### Method
Async Class Method

### Endpoint
async def get_mcp_status(self) -> dict[str, Any]

### Parameters
#### Request Body
- No parameters.

### Request Example
```python
# Assuming 'client' is an initialized ClaudeSDKClient instance
status = await client.get_mcp_status()
print(status)
````

### Response

#### Success Response (200)

- **dict[str, Any]** - A dictionary containing the status of MCP servers.

#### Response Example

```json
{
  "server_name": {
    "status": "running",
    "tools_loaded": ["tool1", "tool2"]
  }
}
```

````

--------------------------------

### Define `query()` function signature in Python SDK

Source: https://docs.claude.com/en/api/agent-sdk/python

This is the function signature for the `query()` method, which initiates a new, independent session with Claude Code for each interaction. It accepts a prompt, optional configuration, and transport, returning an async iterator of messages. This function is suitable for one-off tasks without conversation history.

```python
async def query(
    *,
    prompt: str | AsyncIterable[dict[str, Any]],
    options: ClaudeAgentOptions | None = None,
    transport: Transport | None = None
) -> AsyncIterator[Message]
````

---

### tool()

Source: https://docs.claude.com/en/api/agent-sdk/python

The `tool()` decorator is used to define type-safe MCP tools within the Python Agent SDK. It allows specifying a tool's name, description, input schema, and optional annotations.

````APIDOC
## tool()

### Description
Decorator for defining MCP tools with type safety.

### Method
SDK Decorator

### Endpoint
N/A

### Parameters
#### Path Parameters
N/A

#### Query Parameters
N/A

#### Request Body
- **name** (`str`) - Required - Unique identifier for the tool
- **description** (`str`) - Required - Human-readable description of what the tool does
- **input_schema** (`type | dict[str, Any]`) - Required - Schema defining the tool's input parameters
- **annotations** (`ToolAnnotations | None`) - Optional - Optional MCP tool annotations (e.g., `readOnlyHint`, `destructiveHint`, `openWorldHint`). Imported from `mcp.types`

### Request Example
N/A (parameters are direct arguments)

### Response
#### Success Response (Returns)
- `Callable[[Callable[[Any], Awaitable[dict[str, Any]]]], SdkMcpTool[Any]]` - A decorator function that wraps the tool implementation and returns an `SdkMcpTool` instance.

#### Response Example
```python
from claude_agent_sdk import tool
from typing import Any


@tool("greet", "Greet a user", {"name": str})
async def greet(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Hello, {args['name']}!"}]}
````

````

--------------------------------

### Define ListMcpResourcesOutput Type - TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the output type for listing available MCP (Model Context Protocol) resources returning an array of resource metadata including URI, name, MIME type, description, and server information.

```typescript
type ListMcpResourcesOutput = Array<{
  uri: string;
  name: string;
  mimeType?: string;
  description?: string;
  server: string;
}>;
````

---

### BashOutput Tool - Background Shell Command Output Monitoring

Source: https://docs.claude.com/en/api/agent-sdk/python

Retrieves new output from a background shell process identified by bash_id. Supports optional regex filtering of output lines and returns current shell status (running, completed, failed) with exit code when available.

```json
{
  "bash_id": "str",
  "filter": "str | None"
}
```

```json
{
  "output": "str",
  "status": "running | completed | failed",
  "exitCode": "int | None"
}
```

---

### Create Specialized Subagent for Code Review

Source: https://platform.claude.com/docs/en/agent-sdk/overview

Defines a specialized code-reviewer subagent that the main agent can delegate code review tasks to. The subagent has restricted tool access (Read, Glob, Grep) and custom instructions for quality analysis. Requires Task tool in allowedTools to invoke subagents.

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition


async def main():
    async for message in query(
        prompt="Use the code-reviewer agent to review this codebase",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep", "Task"],
            agents={
                "code-reviewer": AgentDefinition(
                    description="Expert code reviewer for quality and security reviews.",
                    prompt="Analyze code quality and suggest improvements.",
                    tools=["Read", "Glob", "Grep"],
                )
            },
        ),
    ):
```

---

### Edit Tool

Source: https://platform.claude.com/docs/en/agent-sdk/python

Modifies file contents by replacing specified text strings. Supports single or multiple replacements and returns confirmation with the number of replacements made.

````APIDOC
## Edit Tool

### Description
Modifies file contents by replacing text strings with support for single or multiple replacements.

### Tool Name
`Edit`

### Input Parameters
- **file_path** (str) - Required - The absolute path to the file to modify
- **old_string** (str) - Required - The text to replace
- **new_string** (str) - Required - The text to replace it with
- **replace_all** (bool | None) - Optional - Replace all occurrences (default False)

### Request Example
```python
{
    "file_path": "/home/user/app.py",
    "old_string": "DEBUG = True",
    "new_string": "DEBUG = False",
    "replace_all": false
}
````

### Response

#### Success Response (200)

- **message** (str) - Confirmation message
- **replacements** (int) - Number of replacements made
- **file_path** (str) - File path that was edited

#### Response Example

```python
{
    "message": "File successfully edited",
    "replacements": 1,
    "file_path": "/home/user/app.py"
}
```

````

--------------------------------

### CanUseTool

Source: https://docs.claude.com/en/api/agent-sdk/python

Type alias for callback functions used to determine if a tool can be executed. It receives tool details and context, returning a permission result.

```APIDOC
## CanUseTool

### Description
Type alias for tool permission callback functions. The callback receives the tool name, input parameters, and a context object, and must return a `PermissionResult`.

### Definition
```python
CanUseTool = Callable[
    [str, dict[str, Any], ToolPermissionContext], Awaitable[PermissionResult]
]
````

### Parameters

- **tool_name** (str) - Name of the tool being called
- **input_data** (dict[str, Any]) - The tool's input parameters
- **context** (ToolPermissionContext) - A `ToolPermissionContext` with additional information

### Returns

- (PermissionResult) - A `PermissionResult` (either `PermissionResultAllow` or `PermissionResultDeny`)

````

--------------------------------

### Deny Tool Execution with PermissionResultDeny

Source: https://docs.claude.com/en/api/agent-sdk/python

Dataclass indicating a tool call should be denied with an optional explanation message and interrupt flag to stop current execution. Default behavior is 'deny'.

```python
@dataclass
class PermissionResultDeny:
    behavior: Literal["deny"] = "deny"
    message: str = ""
    interrupt: bool = False
````

---

### SettingSource Type

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Controls which filesystem-based configuration sources the SDK loads settings from, providing options for user, project, or local settings.

```APIDOC
## TYPE DEFINITION SettingSource

### Description
Controls which filesystem-based configuration sources the SDK loads settings from, providing options for user, project, or local settings.

### Method
TYPE DEFINITION

### Endpoint
SettingSource

### Parameters
#### Request Body
- **SettingSource** ("user" | "project" | "local") - Required - Specifies the source of settings.
  - `'user'` - Global user settings (`~/.claude/settings.json`)
  - `'project'` - Shared project settings (version controlled) (`.claude/settings.json`)
  - `'local'` - Local project settings (gitignored) (`.claude/settings.local.json`)

### Request Example
{
  "options": {
    "settingSources": ["user", "project", "local"]
  }
}

### Response
#### Success Response (200)
Not applicable for type definitions.

#### Response Example
{}
```

---

### Define `McpStdioServerConfig` Type in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the `McpStdioServerConfig` type for configuring a standard I/O (stdio) based MCP server. It specifies the `command` to execute, optional `args` for the command, and `env` variables for the process, with an optional `type` field set to 'stdio'.

```typescript
type McpStdioServerConfig = {
  type?: "stdio";
  command: string;
  args?: string[];
  env?: Record<string, string>;
};
```

---

### Register Security and Audit Hooks in Claude Agent SDK

Source: https://docs.claude.com/en/api/agent-sdk/python

Demonstrates registering multiple hooks to validate dangerous bash commands and log all tool usage for auditing purposes. The security hook uses a matcher to filter only Bash commands, while the logging hook applies to all tools. Both hooks are configured with PreToolUse and PostToolUse event types.

```python
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher, HookContext
from typing import Any


async def validate_bash_command(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Validate and potentially block dangerous bash commands."""
    if input_data["tool_name"] == "Bash":
        command = input_data["tool_input"].get("command", "")
        if "rm -rf /" in command:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Dangerous command blocked",
                }
            }
    return {}


async def log_tool_use(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Log all tool usage for auditing."""
    print(f"Tool used: {input_data.get('tool_name')}")
    return {}


options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(
                matcher="Bash", hooks=[validate_bash_command], timeout=120
            ),
            HookMatcher(
                hooks=[log_tool_use]
            ),
        ],
        "PostToolUse": [HookMatcher(hooks=[log_tool_use])],
    }
)

async for message in query(prompt="Analyze this codebase", options=options):
    print(message)
```

---

### Class ClaudeSDKClient

Source: https://platform.claude.com/docs/en/agent-sdk/python

Maintains a conversation session across multiple exchanges, providing session continuity, interrupt support, and custom tool integration. It's the Python equivalent of the TypeScript SDK's internal `query()` function.

````APIDOC
## CLASS ClaudeSDKClient

### Description
Maintains a conversation session across multiple exchanges, providing session continuity, interrupt support, and custom tool integration. It's the Python equivalent of the TypeScript SDK's internal `query()` function.

### Method
Class

### Endpoint
class ClaudeSDKClient:
    def __init__(self, options: ClaudeAgentOptions | None = None, transport: Transport | None = None)

### Parameters
#### Request Body
- **options** (ClaudeAgentOptions | None) - Optional - Configuration options for the client.
- **transport** (Transport | None) - Optional - Custom transport layer for communication.

### Request Example
```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

client = ClaudeSDKClient(options=ClaudeAgentOptions(api_key="YOUR_API_KEY"))
````

### Response

#### Success Response (200)

- **ClaudeSDKClient** (object) - An instance of the `ClaudeSDKClient`.

#### Response Example

```python
# ClaudeSDKClient instance
```

````

--------------------------------

### SDKSession.close()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Closes the session.

```APIDOC
## SDKSession.close()

### Description
Closes the session.

### Method
SDK Function

### Parameters
(None)

### Request Example
(No request body)

### Response
#### Success Response (void)
- No explicit return value. The session is closed.

#### Response Example
(No response body)
````

---

### GlobInput Type - File Pattern Matching TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the input schema for the Glob tool that performs fast file pattern matching compatible with any codebase size. Supports glob patterns and optional path specification for targeted file discovery.

```typescript
type GlobInput = {
  pattern: string;
  path?: string;
};
```

---

### Define SandboxSettings Type for Sandbox Configuration

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines a comprehensive TypeScript type for sandbox configuration controlling command execution behavior, network restrictions, filesystem access, and security policies. Enables programmatic control over sandbox isolation and command permissions.

```typescript
type SandboxSettings = {
  enabled?: boolean;
  autoAllowBashIfSandboxed?: boolean;
  excludedCommands?: string[];
  allowUnsandboxedCommands?: boolean;
  network?: SandboxNetworkConfig;
  filesystem?: SandboxFilesystemConfig;
  ignoreViolations?: Record<string, string[]>;
  enableWeakerNestedSandbox?: boolean;
  ripgrep?: { command: string; args?: string[] };
};
```

---

### Define Tool Permission Callback with CanUseTool

Source: https://docs.claude.com/en/api/agent-sdk/python

Type alias for asynchronous permission callback functions that receive tool name, input parameters, and context to determine if a tool call should be allowed. Returns a PermissionResult indicating allow or deny decision.

```python
CanUseTool = Callable[
    [str, dict[str, Any], ToolPermissionContext], Awaitable[PermissionResult]
]
```

---

### Define Permission Rules with PermissionRuleValue

Source: https://docs.claude.com/en/api/agent-sdk/python

Dataclass representing a single permission rule containing a tool name and optional rule content for use in permission update operations.

```python
@dataclass
class PermissionRuleValue:
    tool_name: str
    rule_content: str | None = None
```

---

### AgentInput Type - Task Tool TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the input schema for the Task tool that launches a new agent to handle complex, multi-step tasks autonomously. Supports configuration for model selection, execution mode, background execution, and isolation settings.

```typescript
type AgentInput = {
  description: string;
  prompt: string;
  subagent_type: string;
  model?: "sonnet" | "opus" | "haiku";
  resume?: string;
  run_in_background?: boolean;
  max_turns?: number;
  name?: string;
  team_name?: string;
  mode?: "acceptEdits" | "bypassPermissions" | "default" | "dontAsk" | "plan";
  isolation?: "worktree";
};
```

---

### Detect Claude model refusals using `stop_reason` in Agent SDK (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/stop-reasons

This snippet provides a `safeQuery` function that checks for `refusal` as a `stop_reason`. It demonstrates how to handle declined requests by logging a message and returning null, ensuring a more robust interaction with the Claude model by gracefully managing content policy violations or other refusals.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

async function safeQuery(prompt: string): Promise<string | null> {
  for await (const message of query({ prompt })) {
    if (message.type === "result") {
      if (message.stop_reason === "refusal") {
        console.log("Request was declined. Please revise your prompt.");
        return null;
      }
      if (message.subtype === "success") {
        return message.result;
      }
      return null;
    }
  }
  return null;
}
```

---

### Define ExitPlanMode Tool Input Type (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the input type for the `ExitPlanMode` tool. This type allows specifying an optional array of `allowedPrompts`, which are objects detailing specific tool permissions (e.g., 'Bash' with a prompt) required to implement the plan after exiting planning mode.

```typescript
type ExitPlanModeInput = {
  allowedPrompts?: Array<{
    tool: "Bash";
    prompt: string;
  }>;
};
```

---

### Configure Permission Mode in TypeScript

Source: https://platform.claude.com/docs/en/agent-sdk/mcp

Set the permissionMode option to control tool usage approval behavior. 'acceptEdits' automatically approves non-destructive operations, while 'bypassPermissions' skips all safety prompts. This configuration eliminates the need for explicit allowedTools lists.

```typescript
const _ = {
  options: {
    mcpServers: {
      // your servers
    },
    permissionMode: "acceptEdits", // No need for allowedTools
  },
};
```

---

### SDKSession.stream()

Source: https://platform.claude.com/docs/en/agent-sdk/typescript-v2-preview

Streams messages from the session as an asynchronous generator.

```APIDOC
## SDKSession.stream()

### Description
Streams messages from the session as an asynchronous generator.

### Method
SDK Function

### Parameters
(None)

### Request Example
(No request body)

### Response
#### Success Response (AsyncGenerator<SDKMessage, void>)
- **SDKMessage** (object) - An asynchronous generator yielding `SDKMessage` objects. The specific structure of `SDKMessage` is not detailed in the provided text.

#### Response Example
(A stream of `SDKMessage` objects, e.g., partial text, tool calls, etc., not representable as a single JSON object.)
```

---

### BaseHookInput Type

Source: https://docs.claude.com/en/api/agent-sdk/python

Base fields present in all hook input types. This TypedDict provides common session and context information available to all hook handlers.

```APIDOC
## BaseHookInput

### Description
Base TypedDict containing fields that are present in all hook input types. Provides session context and environment information.

### Type Definition
```

class BaseHookInput(TypedDict):
session_id: str
transcript_path: str
cwd: str
permission_mode: NotRequired[str]

```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | `str` | Yes | Current session identifier |
| `transcript_path` | `str` | Yes | Path to the session transcript file |
| `cwd` | `str` | Yes | Current working directory |
| `permission_mode` | `str` | No | Current permission mode |
```

---

### Compact Conversation History using /compact command in Claude Agent SDK (TypeScript/Python)

Source: https://platform.claude.com/docs/en/agent-sdk/slash-commands

This snippet demonstrates how to use the `/compact` slash command to reduce the conversation history size. It listens for a system message with `subtype` 'compact_boundary' to confirm compaction and retrieve metadata like pre-compaction token count and trigger.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "/compact",
  options: { maxTurns: 1 },
})) {
  if (message.type === "system" && message.subtype === "compact_boundary") {
    console.log("Compaction completed");
    console.log("Pre-compaction tokens:", message.compact_metadata.pre_tokens);
    console.log("Trigger:", message.compact_metadata.trigger);
  }
}
```

```python
import asyncio
from claude_agent_sdk import query


async def main():
    async for message in query(prompt="/compact", options={"max_turns": 1}):
        if message.type == "system" and message.subtype == "compact_boundary":
            print("Compaction completed")
            print("Pre-compaction tokens:", message.compact_metadata.pre_tokens)
            print("Trigger:", message.compact_metadata.trigger)


asyncio.run(main())
```

---

### Define ListMcpResources Tool Input Type (TypeScript)

Source: https://platform.claude.com/docs/en/agent-sdk/typescript

Defines the input type for the `ListMcpResources` tool. This type allows an optional `server` property, which can be used to filter the MCP resources listed from connected servers.

```typescript
type ListMcpResourcesInput = {
  server?: string;
};
```

---

### Control Tool Access for Skills in Claude Agent SDK

Source: https://platform.claude.com/docs/en/agent-sdk/skills

This snippet demonstrates how to restrict the tools an SDK application can use by specifying an `allowedTools` list in the `ClaudeAgentOptions`. Tools not present in this list will be denied access, ensuring controlled execution within the application. It also shows how to load skills from filesystem using `settingSources`.

```python
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Load Skills from filesystem
    allowed_tools=["Skill", "Read", "Grep", "Glob"],
)

async for message in query(prompt="Analyze the codebase structure", options=options):
    print(message)
```

```typescript
for await (const message of query({
  prompt: "Analyze the codebase structure",
  options: {
    settingSources: ["user", "project"], // Load Skills from filesystem
    allowedTools: ["Skill", "Read", "Grep", "Glob"],
    permissionMode: "dontAsk", // Deny anything not in allowedTools
  },
})) {
  console.log(message);
}
```
