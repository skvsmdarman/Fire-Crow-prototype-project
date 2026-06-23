import re

def fix_types():
    path = "frontend/src/app/dashboard/audits/[jobId]/ClientAuditRunPage.tsx"
    with open(path, "r") as f:
        content = f.read()

    # The useEffect returns null at the end in some cases.
    # We will replace `return null;` with `return undefined;` or just remove the return.

    # Let's see what is there.

    # We just replace `return null;` with `return undefined;` in `useEffect(() => { ... });`
    # Let's do it generally:
    # `return () => stopLogStream(jobId);`
    # `return null;` -> `return;`
    content = content.replace("return null;", "return;")
    content = content.replace("  if (!session.hasDashboardSession) return;", "  if (!session.hasDashboardSession) return null;")

    with open(path, "w") as f:
        f.write(content)

fix_types()
