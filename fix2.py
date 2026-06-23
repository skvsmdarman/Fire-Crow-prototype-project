import re

def rewrite_dashboard():
    path = "frontend/src/app/dashboard/page.tsx"
    with open(path, "r") as f:
        content = f.read()

    injection = """
  useEffect(() => {
    if (!authSession.hasDashboardSession) {
      router.push("/signin");
    }
  }, [authSession.hasDashboardSession, router]);

  if (!authSession.hasDashboardSession) return null;
"""

    if "if (!authSession.hasDashboardSession) return null;" not in content:
        content = content.replace(
            "const authSession = useAuthSession();",
            "const authSession = useAuthSession();\n" + injection
        )

        with open(path, "w") as f:
            f.write(content)
        print(f"Updated {path}")

rewrite_dashboard()
