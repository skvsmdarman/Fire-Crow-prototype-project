path = "frontend/src/app/dashboard/page.tsx"
with open(path, "r") as f:
    content = f.read()

content = content.replace("  if (!authSession.hasDashboardSession) return null;\n  return (\n    <span className=\"mono\"", "  return (\n    <span className=\"mono\"")

with open(path, "w") as f:
    f.write(content)
