"""
3D Editor Experiment

Stress test: build a 3D object editor with rotate, scale, translate, pan.
Uses @react-three/fiber + @react-three/drei for the 3D viewport.
Same implicit fork architecture on Groq.

## Experiment Results (2026-03-28)

Model: openai/gpt-oss-120b on Groq
Task: 3D object editor with cube, transform gizmos, orbit controls, properties panel.

### Result

    Built in:     13.7s
    Runs:         YES — 3D viewport with cube, orbit, transform gizmos
    Buggy:        Some minor issues but functional

### What was built

    - 3D viewport with a cube on a grid (react-three-fiber Canvas)
    - Orbit controls for rotating/panning the camera
    - Toolbar with Translate/Rotate/Scale mode buttons
    - Transform gizmo handles on the cube matching selected mode
    - Properties panel showing live position/rotation/scale values
    - Header bar

### Key Findings

- 13.7s for a working 3D editor. Same architecture, just a harder task.
- The agent correctly used @react-three/fiber Canvas, @react-three/drei
  OrbitControls and TransformControls without being told how.
- Had to fix: @/ alias detection in import scanner, stub dual exports
  (named + default), drei event handler type hints in system prompt.
- A few bugs in the output but the core functionality works —
  you can orbit, select transform modes, and see live property values.
- This validates the "creative tool primitives" approach: pre-install
  the 3D libraries, let the agent compose them.
"""

from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
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
    # OpenAI-compatible tool format for Groq
    AGENT_TOOLS = [
        {"type": "function", "function": {"name": "read_file", "description": "Read a file.", "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}}},
        {"type": "function", "function": {"name": "write_file", "description": "Write content to a file. OVERWRITES the entire file. Creates dirs if needed.", "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}}},
        {"type": "function", "function": {"name": "done", "description": "Signal you are finished.", "parameters": {"type": "object", "properties": {}}}},
    ]

    SYSTEM_PROMPT = """\
You are a senior React/TypeScript developer AND a skilled UI designer.
Write code directly to files.

Tools: read_file, write_file, done.

You are building ONE component or module. Write it to your assigned file.
Use inline styles. Include proper imports. Call done() when finished.

STYLING:
- Use Tailwind CSS utility classes for ALL styling. Do NOT use inline styles.
- Use shadcn/ui components where possible. ONLY these are available (do NOT import others):
  import { Button } from "@/components/ui/button"
  import { Input } from "@/components/ui/input"
  import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
  import { Badge } from "@/components/ui/badge"
  import { Separator } from "@/components/ui/separator"
  import { Skeleton } from "@/components/ui/skeleton"
- Do NOT import: Select, Slider, Switch, Tabs, ScrollArea, Tooltip, Dialog, or any
  other shadcn component not listed above. They are NOT installed.
- For icons use lucide-react: import { Search, Star, ChevronDown, etc } from "lucide-react"
- Compose shadcn components with Tailwind for layout and custom styling.
- Make it look like a real, polished product.

3D / CREATIVE TOOL LIBRARIES (pre-installed, use them):
- @react-three/fiber — React renderer for Three.js. Use <Canvas> as the 3D viewport.
  import { Canvas } from "@react-three/fiber"
- @react-three/drei — Helpers for react-three-fiber: OrbitControls, TransformControls,
  Grid, Environment, etc.
  import { OrbitControls, TransformControls, Grid, GizmoHelper, GizmoViewport } from "@react-three/drei"
- three — The underlying Three.js library. Use for types and math.
  import * as THREE from "three"

IMPORTANT drei/fiber type notes:
- TransformControls onChange event is NOT a THREE.Object3D. Use onObjectChange instead,
  or cast with `as any` for event handlers if needed.
- Canvas events use react-three-fiber's own event system. When in doubt, use `any` for
  drei component event handler types rather than guessing wrong.

If you need child components, just IMPORT and USE them in your JSX as if they
already exist. You don't need to implement them — other agents will handle that
automatically. Just write the import and use the component with the props you need.

The system will detect that undefined components and create them for you.
"""

    PACKAGE_JSON = json.dumps({
        "name": "morph-app", "private": True, "version": "0.0.1", "type": "module",
        "scripts": {"dev": "vite"},
        "dependencies": {
            "react": "^18.2.0", "react-dom": "^18.2.0",
            "three": "^0.162.0", "@react-three/fiber": "^8.15.0",
            "@react-three/drei": "^9.97.0", "@types/three": "^0.162.0",
            "class-variance-authority": "^0.7.0", "clsx": "^2.1.0",
            "tailwind-merge": "^2.2.0", "lucide-react": "^0.344.0",
            "@radix-ui/react-slot": "^1.0.2",
            "@radix-ui/react-separator": "^1.0.3",
            "@radix-ui/react-select": "^2.0.0",
            "@radix-ui/react-slider": "^1.1.2",
            "@radix-ui/react-switch": "^1.0.3",
            "@radix-ui/react-tabs": "^1.0.4",
            "@radix-ui/react-scroll-area": "^1.0.5",
            "@radix-ui/react-tooltip": "^1.0.7",
        },
        "devDependencies": {
            "@types/react": "^18.2.0", "@types/react-dom": "^18.2.0",
            "@vitejs/plugin-react": "^4.2.0", "typescript": "^5.3.0",
            "vite": "^5.0.0", "tailwindcss": "^3.4.0",
            "autoprefixer": "^10.4.0", "postcss": "^8.4.0",
        },
    })

    TSCONFIG_JSON = json.dumps({
        "compilerOptions": {
            "target": "ES2020", "useDefineForClassFields": True,
            "lib": ["ES2020", "DOM", "DOM.Iterable"],
            "module": "ESNext", "skipLibCheck": True,
            "moduleResolution": "bundler", "resolveJsonModule": True,
            "isolatedModules": True, "noEmit": True, "jsx": "react-jsx",
            "strict": True, "noUnusedLocals": False, "noUnusedParameters": False,
            "baseUrl": ".", "paths": {"@/*": ["./src/*"]},
        },
        "include": ["src"],
    })

    INDEX_HTML = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/><title>Morph App</title></head><body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>'

    MAIN_TSX = "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\nimport './index.css';\n\nReactDOM.createRoot(document.getElementById('root')!).render(\n  <React.StrictMode><App /></React.StrictMode>\n);\n"

    VITE_CONFIG = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
"""

    TAILWIND_CONFIG = """/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
        destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
        muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        accent: { DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))' },
        popover: { DEFAULT: 'hsl(var(--popover))', foreground: 'hsl(var(--popover-foreground))' },
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [],
};
"""

    POSTCSS_CONFIG = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""

    INDEX_CSS = """@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
  }
}

@layer base {
  * { @apply border-border; }
  body { @apply bg-background text-foreground; }
}
"""

    # shadcn/ui utility: cn()
    CN_UTIL = """import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
"""

    # Core shadcn components (pre-bundled)
    SHADCN_BUTTON = '''import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
'''

    SHADCN_INPUT = '''import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
'''

    SHADCN_CARD = '''import * as React from "react";
import { cn } from "@/lib/utils";

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("rounded-lg border bg-card text-card-foreground shadow-sm", className)} {...props} />
  )
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />
  )
);
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn("text-2xl font-semibold leading-none tracking-tight", className)} {...props} />
  )
);
CardTitle.displayName = "CardTitle";

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
  )
);
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center p-6 pt-0", className)} {...props} />
  )
);
CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardTitle, CardContent, CardFooter };
'''

    SHADCN_BADGE = '''import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
'''

    SHADCN_SEPARATOR = '''import * as React from "react";
import * as SeparatorPrimitive from "@radix-ui/react-separator";
import { cn } from "@/lib/utils";

const Separator = React.forwardRef<
  React.ElementRef<typeof SeparatorPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>
>(({ className, orientation = "horizontal", decorative = true, ...props }, ref) => (
  <SeparatorPrimitive.Root
    ref={ref}
    decorative={decorative}
    orientation={orientation}
    className={cn("shrink-0 bg-border", orientation === "horizontal" ? "h-[1px] w-full" : "h-full w-[1px]", className)}
    {...props}
  />
));
Separator.displayName = SeparatorPrimitive.Root.displayName;

export { Separator };
'''

    SHADCN_SKELETON = '''import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-md bg-muted", className)} {...props} />;
}

export { Skeleton };
'''

    # Known imports that should NOT be auto-forked
    KNOWN_MODULES = {
        "react", "react-dom", "react-dom/client", "react/jsx-runtime",
        "lucide-react", "class-variance-authority", "clsx", "tailwind-merge",
        "three",
    }
    # Prefixes that should not be auto-forked
    KNOWN_PREFIXES = [
        "@/components/ui/", "@/lib/", "@radix-ui/",
        "@react-three/", "@types/three",
    ]

    def __init__(self, model="openai/gpt-oss-120b", project_root=None, max_depth=3, port=5173):
        self.model = model
        self.max_depth = max_depth
        self.project_root = project_root or tempfile.mkdtemp(prefix="morph_")
        self.client = Groq()
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
        elif name == "write_file":
            if "content" not in input:
                return "Error: missing content."
            fpath = os.path.join(root, input["file_path"])
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "w") as f:
                f.write(input["content"])
            with self._written_lock:
                self._written_files.add(input["file_path"])
            return f"Wrote {input['file_path']}."
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
                f"export {{ {component_name} }};\n"
                f"export default {component_name};\n"
            )

        with open(full_path, "w") as f:
            f.write(stub)
        self._print(f"    [stub] {file_path} — placeholder for {component_name}")

    def _detect_undefined_imports(self, file_path: str, content: str) -> list[dict]:
        """Scan written code for imports of local files that don't exist yet."""
        undefined = []

        # Match: import X from './components/X' or import { X } from '@/hooks/useX'
        import_pattern = re.compile(
            r"""import\s+(?:(?:\{[^}]*\}|\w+)(?:\s*,\s*(?:\{[^}]*\}|\w+))*)\s+from\s+['"]((?:\.|@/)[^'"]+)['"]"""
        )

        for match in import_pattern.finditer(content):
            import_path = match.group(1)

            # Skip known modules and prefixes
            if any(import_path.startswith(k) for k in self.KNOWN_MODULES):
                continue
            if any(import_path.startswith(p) for p in self.KNOWN_PREFIXES):
                continue

            # Resolve @/ alias to src/
            if import_path.startswith("@/"):
                rel_path = "src/" + import_path[2:]
            else:
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
        """Run an agent using Groq (OpenAI-compatible). Returns undefined imports."""
        indent = "  " * depth
        self._print(f"{indent}[{node.name}] Building...")

        node.messages.append({"role": "user", "content": user_message})
        all_undefined: list[dict] = []
        is_done = False

        # Ensure system message is first
        messages_to_send = [{"role": "system", "content": self.SYSTEM_PROMPT}] + node.messages

        while not is_done:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_to_send,
                tools=self.AGENT_TOOLS,
                tool_choice="auto",
                max_tokens=8192,
                temperature=0.6,
            )

            msg = response.choices[0].message
            tool_calls = msg.tool_calls or []

            # Debug: show what the model returned
            if msg.content:
                # Truncate thinking tags if present
                content_preview = msg.content[:200].replace("\n", " ")
                self._print(f"{indent}  [response] {content_preview}...")
            if not tool_calls:
                self._print(f"{indent}  [no tools called — model responded with text only]")

            # Append assistant message to history
            assistant_msg = {"role": "assistant", "content": msg.content or ""}
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in tool_calls
                ]
            node.messages.append(assistant_msg)
            messages_to_send.append(assistant_msg)

            if not tool_calls:
                break

            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    tool_input = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    tool_input = {}

                if tool_name in ("read_file", "write_file"):
                    result = self._exec_fs(tool_name, tool_input)
                    fp = tool_input.get("file_path", "?")
                    self._print(f"{indent}  [{tool_name}] {fp[:50]}")

                    # After a write, scan for undefined imports and create stubs
                    if tool_name == "write_file":
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
                    result = "Done."

                else:
                    result = f"Unknown tool: {tool_name}"

                # Add tool result (OpenAI format)
                tool_msg = {"role": "tool", "tool_call_id": tc.id, "content": result}
                node.messages.append(tool_msg)
                messages_to_send.append(tool_msg)

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
                f"In your FIRST response, call write_file on {child_path} to replace the\n"
                f"ENTIRE stub content with your real implementation. Then done().\n"
                f"That's it — one write_file, one done. Two tool calls total.\n\n"
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
        root = self.project_root

        # Root config files
        for name, content in [
            ("package.json", self.PACKAGE_JSON), ("tsconfig.json", self.TSCONFIG_JSON),
            ("index.html", self.INDEX_HTML), ("vite.config.ts", self.VITE_CONFIG),
            ("tailwind.config.js", self.TAILWIND_CONFIG), ("postcss.config.js", self.POSTCSS_CONFIG),
        ]:
            with open(os.path.join(root, name), "w") as f:
                f.write(content)

        # src files
        scaffolds = {
            "src/main.tsx": self.MAIN_TSX,
            "src/index.css": self.INDEX_CSS,
            "src/lib/utils.ts": self.CN_UTIL,
            "src/components/ui/button.tsx": self.SHADCN_BUTTON,
            "src/components/ui/input.tsx": self.SHADCN_INPUT,
            "src/components/ui/card.tsx": self.SHADCN_CARD,
            "src/components/ui/badge.tsx": self.SHADCN_BADGE,
            "src/components/ui/separator.tsx": self.SHADCN_SEPARATOR,
            "src/components/ui/skeleton.tsx": self.SHADCN_SKELETON,
        }
        for path, content in scaffolds.items():
            full = os.path.join(root, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w") as f:
                f.write(content)

        # App.tsx stub
        app_path = os.path.join(root, "src", "App.tsx")
        with open(app_path, "w") as f:
            f.write(
                "import React from 'react';\n\n"
                "const App: React.FC = () => (\n"
                '  <div className="flex items-center justify-center min-h-screen bg-background text-muted-foreground text-lg">\n'
                "    Building your app...\n"
                "  </div>\n"
                ");\n\n"
                "export default App;\n"
            )

        # Register all scaffolded files
        with self._written_lock:
            for path in scaffolds:
                self._written_files.add(path)
            self._written_files.add("src/App.tsx")

        # npm install
        self._print("Installing dependencies...")
        subprocess.run(["npm", "install", "--silent"], cwd=root, capture_output=True, timeout=120)

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
            "1. src/types/index.ts — shared TypeScript types for the editor state\n"
            "2. src/App.tsx — the main app component with the full layout\n\n"
            "src/App.tsx already exists as a stub showing 'Building your app...'. \n"
            "Use write_file to replace its ENTIRE content with your real App component.\n\n"
            "For App.tsx, import and use sub-components as if they exist.\n"
            "Don't implement them — just import and use them with the right props.\n"
            "Other agents will auto-implement any component you reference.\n\n"
            "Write all files with write_file. Then done()."
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
            f"Read the relevant files, make changes with write_file, done().\n"
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
    print("3D EDITOR — MORPH")
    print("=" * 60)
    print(f"Project: {app.path}")
    print(f"Open http://localhost:5173 NOW\n")

    app.build(
        "Build a 3D object editor. The app should have:\n"
        "- A large 3D viewport in the center showing a cube on a grid\n"
        "- The user can rotate the view by dragging (orbit controls)\n"
        "- The user can pan around the scene\n"
        "- A toolbar on the left with transform mode buttons: Translate, Rotate, Scale\n"
        "- When a mode is selected, the cube gets transform gizmo handles for that mode\n"
        "- A properties panel on the right showing the cube's position, rotation, and scale values\n"
        "- The properties panel updates in real time as the user transforms the cube\n"
        "- A header bar with the app name"
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
