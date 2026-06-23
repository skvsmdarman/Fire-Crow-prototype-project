path = "frontend/src/app/dashboard/page.tsx"
with open(path, "r") as f:
    content = f.read()

content = content.replace("  if (!authSession.hasDashboardSession) {\n      router.push(\"/signin\");\n    }\n  }, [authSession.hasDashboardSession, router]);\n\n  \n\n  const [active", "  if (!authSession.hasDashboardSession) {\n      router.push(\"/signin\");\n    }\n  }, [authSession.hasDashboardSession, router]);\n\n  if (!authSession.hasDashboardSession) return null;\n\n  const [active")

with open(path, "w") as f:
    f.write(content)

path2 = "frontend/src/app/dashboard/audits/[jobId]/ClientAuditRunPage.tsx"
with open(path2, "r") as f:
    content2 = f.read()

content2 = content2.replace("  if (!session.hasDashboardSession) {\n      router.push(\"/signin\");\n    }\n  }, [session.hasDashboardSession, router]);\n\n  \n\n\n  const {", "  if (!session.hasDashboardSession) {\n      router.push(\"/signin\");\n    }\n  }, [session.hasDashboardSession, router]);\n\n  if (!session.hasDashboardSession) return null;\n\n  const {")

with open(path2, "w") as f:
    f.write(content2)
