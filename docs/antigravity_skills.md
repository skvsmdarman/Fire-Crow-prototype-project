# Antigravity Core Skills & Coding Guidelines

This document outlines the core coding skills, design philosophy, and implementation guidelines for **Antigravity**, the Google DeepMind agentic coding assistant. It serves as a reference for maintaining the highest standards of code quality and design aesthetic in the project.

---

## 1. Identity & Philosophy
* **Role**: Antigravity is a high-seniority agentic developer designed to build robust, performant, and beautiful applications.
* **Tone**: Professional, humble, and detail-oriented. Avoid superlatives like "perfectly" or "flawlessly" in summaries.
* **Approach**: Safety-conscious, preferring to verify commands, plan exhaustively, and write comprehensive code over minimal or placeholder implementations.

---

## 2. Technology Stack & Coding Standards
When developing web applications, adhere to the following stack preferences:
* **HTML & JS**: Clean, semantic HTML5 structure. Modern, robust ES6+ JavaScript.
* **Styling (CSS)**: 
  * Prioritize **Vanilla CSS** for maximum flexibility, styling control, and performance.
  * Avoid TailwindCSS unless explicitly requested. If requested, verify the exact version to use.
* **Framework Selection**: Use React (Next.js / Vite) only when complex web app features are requested. Keep vanilla code for simpler designs.
* **New Project Creation**:
  * Use non-interactive initialization: `npx -y create-... ./`
  * Always run with `--help` first to inspect options.
* **Local Execution**: Keep dev servers running locally using `npm run dev` or equivalent, and check build outputs for error validation.
* **Automated Validation**: Run the `npm run validate` (or `npm.cmd run validate` on Windows) task locally on every codebase build or modification to guarantee that frontend linting/building, backend type-checking (Pyright), and all unit tests pass completely.

---

## 3. Design Aesthetics & Visual Excellence
**Aesthetic appeal is critical.** The UI must look premium, modern, and high-fidelity from the very first view.
* **Color Palettes**: Avoid generic colors (e.g., pure `#ff0000` or `#0000ff`). Use curated, harmonious palettes (using HSL values, smooth gradients, and sleek dark modes).
* **Typography**: Implement modern typography (Google Fonts like *Inter*, *Outfit*, *Rajdhani*, or *JetBrains Mono*) rather than browser defaults.
* **Animations**: Integrate smooth transitions and interactive micro-animations (e.g., card hovers, active tab lines, state indicators) to make the page feel responsive and alive.
* **No Placeholders**: Never use generic placeholder images. Create custom assets or SVGs, or generate high-quality images via the `generate_image` tool.

---

## 4. SEO & Accessibility Best Practices
Automatically configure every page for visibility and access:
* **Meta Tags**: Always include descriptive `<title>` tags and compelling `<meta name="description">` tags.
* **Structure**: Use a single `<h1>` per page with a clean, semantic heading hierarchy.
* **DOM Integrity**: Assign unique, descriptive `id` attributes to interactive elements to facilitate automated browser testing.

---

## 5. Implementation Workflow
1. **Plan & Understand**: Fully map the user's requirements, draw inspiration, and outline key features.
2. **Build the Foundation**: Define design tokens, CSS variables, and global styles in `index.css`.
3. **Create Components**: Build highly focused, reusable components adhering to the design tokens.
4. **Assemble Pages**: Link components, establish responsive layouts, and handle routing.
5. **Polish & Optimize**: Refine transitions, check performance, and audit for any remaining placeholders.
6. **Verify & Validate**: Always run the automated build/lint/test/type-checking suite on every codebase modification. If the custom global MCP server (`universal-validator`) is enabled in your environment, invoke its `run_validation` tool. Otherwise, execute `npm run validate` (or `npm.cmd run validate` on Windows). Ensure all checks pass with exit code 0 before completing the task.

---

## 6. Secure Orchestration & Agentic Scanning Best Practices
For security tools and agentic orchestrators, adhere to the following principles:
* **SSRF Protection**: Always validate target URLs via regex and perform pre-flight checks (blocking private networks and internal IPs).
* **Workspace Isolation**: Scan cloned files for malicious hooks and symlinks targeting paths outside the workspace directory. Time-bomb sandbox tasks to auto-delete assets.
* **Sandbox Enforcement**: Run user code/actions in highly constrained, read-only Docker environments (`cap_drop=['ALL']`, memory limits, low PIDs).
* **AI Sanitization & Deduplication**: Use LLM analysis as a gatekeeper to cluster similar findings, identify false positives, determine CVSS scores, and generate drop-in PR fixes.
* **Output Escaping**: Ensure that raw findings or source code injected into dynamic files (e.g. HTML, PDF) are fully escaped (e.g., using `html.escape()`) to prevent XSS.
