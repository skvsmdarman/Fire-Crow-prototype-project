import re

with open("backend/app/agents/sast_semgrep.py", "r") as f:
    content = f.read()

search = """    logger.info("Semgrep unavailable; no Semgrep findings will be generated.")
    if settings.DEBUG:
        return _simulated_findings(tech_stack)
    return []"""

replace = """    logger.info("Semgrep unavailable; no Semgrep findings will be generated.")
    return []"""

if search in content:
    content = content.replace(search, replace)
    with open("backend/app/agents/sast_semgrep.py", "w") as f:
        f.write(content)
    print("Patched sast_semgrep.py")
else:
    print("Search string not found in sast_semgrep.py")
