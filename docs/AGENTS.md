# Fire Crow Agent Instructions (Developer Guide)

This document contains rules, patterns, and style conventions that all agent systems (such as Claude, Gemini, or other code agents) must follow when modifying this repository.

---

## 1. Code Quality & Code Splitting

### 1.1 Localized Surgical Edits
* Avoid replacing entire files when making changes. Use targeted code replacement ranges to keep diffs minimal and avoid breaking unrelated features.
* Preserve all existing comments, docstrings, and logger entries.

### 1.2 TypeScript & Python Type Safety
* All newly introduced functions, interfaces, and variables must have explicit types.
* Strict TypeScript rules apply: the `any` type is forbidden. Use appropriate generic definitions or interfaces.
* Python code must pass validation under the workspace configuration. Avoid untyped function signatures.

### 1.3 Components & Directory Structure
* Page-level components in `src/app` should focus on routing, high-level layout assembly, and state flow.
* Extract reusable UI components (e.g., input fields, loaders, buttons, dialog boxes) into separate files. Keep them highly focused, self-contained, and componentized.

---

## 2. API Communication & State Synchronization

### 2.1 State Feedback for Forms
Every interactive form, audit submit action, and login card must explicitly handle and display three states:
1. **Loading State**: Disable action inputs, show spinners/skeleton loaders, and provide visible feedback during fetch wait time.
2. **Error State**: Render validation warnings or server rejection details (`HTTP 401`, `422`, `500`) directly on the UI without causing layout shifts.
3. **Success State**: Display completion markers, reset input states when appropriate, and handle page redirect transitions smoothly.

### 2.2 Client-Side Form Validation
* Perform input validation on the client-side *before* making any network requests.
* Use strict validation rules:
  * For Repository inputs: Validate GitHub HTTPS paths using the format: `^https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+(\.git)?$`.
  * For Workspace inputs: Validate that workspace names are alphanumeric, trimming trailing whitespace.

---

## 3. Strict Design & Style System

* **Never Use Utility CSS Frameworks**: Tailwind CSS, Bootstrap, or Tailwind-equivalent inline styles are prohibited.
* **Predefined Variables**: Only use variables and classes defined in [globals.css](file:///d:/Fire%20Crow/frontend/src/app/globals.css). Avoid introducing custom, ad-hoc inline color codes or typography sizes.
* **Aesthetics Directive**: Pages must retain a premium, responsive dark-theme design. Ensure hover transitions and micro-animations are responsive and smooth.

---

## 4. Verification & Testing Workflow

This repository supports a custom global MCP (Model Context Protocol) server.

### 4.1 Custom MCP Server Integration
* **Server Name**: `universal-validator`
* **Target Tool**: `run_validation`
* **Automated Invocation Rule**: **On every file update/modification**, the agent MUST immediately invoke the `run_validation` tool of the `universal-validator` MCP server.
* The tool dynamically inspects the workspace directory and executes its respective validation scripts.

### 4.2 Configuration Settings
This validator is configured globally in `~/.claude/settings.json` under `mcpServers`:
```json
{
  "mcpServers": {
    "universal-validator": {
      "command": "C:\\Users\\sahoo\\AppData\\Roaming\\uv\\python\\cpython-3.12.12-windows-x86_64-none\\python.exe",
      "args": [
        "C:\\Users\\sahoo\\.claude\\mcp_server.py"
      ]
    }
  }
}
```

### 4.3 Manual Execution Fallback
If the global MCP tool is unavailable or inactive in the current execution context, fall back to executing:
```powershell
npm run validate
```
All checks (frontend lint, build, backend type-checking, and tests) must succeed before work is finalized.
