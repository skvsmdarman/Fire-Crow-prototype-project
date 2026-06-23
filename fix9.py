path = "frontend/src/app/dashboard/audits/[jobId]/ClientAuditRunPage.tsx"
with open(path, "r") as f:
    content = f.read()

content = content.replace("  if (!session.hasDashboardSession) return null;\n    return () => {", "    return () => {")

with open(path, "w") as f:
    f.write(content)
