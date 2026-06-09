import re

with open("backend/app/agents/dependency_scan.py", "r") as f:
    content = f.read()

search = """    logger.info("Dependency scanner unavailable; no dependency findings will be generated.")
    if settings.DEBUG:
        return _simulated_findings(dependency_manifests)
    return []"""

replace = """    logger.info("Dependency scanner unavailable; no dependency findings will be generated.")
    return []"""

if search in content:
    content = content.replace(search, replace)
    with open("backend/app/agents/dependency_scan.py", "w") as f:
        f.write(content)
    print("Patched dependency_scan.py")
else:
    print("Search string not found in dependency_scan.py")
