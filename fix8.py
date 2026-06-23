import re
def fix_hooks(path):
    with open(path, "r") as f:
        content = f.read()

    # We need to move `if (!authSession.hasDashboardSession) return null;`
    # to the very bottom of the hooks list.

    # Let's remove the return early statement
    content = content.replace("if (!authSession.hasDashboardSession) return null;", "")
    content = content.replace("if (!session.hasDashboardSession) return null;", "")

    with open(path, "w") as f:
        f.write(content)

    with open(path, "r") as f:
        content = f.read()

    lines = content.split('\n')
    new_lines = []
    return_added = False

    for i, line in enumerate(lines):
        if "return (" in line and not return_added:
            if "authSession" in content:
                new_lines.append("  if (!authSession.hasDashboardSession) return null;")
            elif "session" in content:
                new_lines.append("  if (!session.hasDashboardSession) return null;")
            return_added = True
        new_lines.append(line)

    with open(path, "w") as f:
        f.write("\n".join(new_lines))

fix_hooks("frontend/src/app/dashboard/page.tsx")
fix_hooks("frontend/src/app/dashboard/audits/[jobId]/ClientAuditRunPage.tsx")
