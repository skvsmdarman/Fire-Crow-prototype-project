import importlib
import pkgutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "backend"
sys.path.append(str(BASE))

PACKAGE = "app.agents"

def walk_package(pkg_name):
    pkg = importlib.import_module(pkg_name)
    for _, mod_name, is_pkg in pkgutil.iter_modules(pkg.__path__):
        full_name = f"{pkg_name}.{mod_name}"
        yield full_name
        if is_pkg:
            yield from walk_package(full_name)

failed = []
for mod in walk_package(PACKAGE):
    try:
        importlib.import_module(mod)
    except Exception as exc:  # noqa: BLE001
        failed.append((mod, exc))

if not failed:
    print("✅ All agents imported successfully.")
else:
    print("❌ Import errors:")
    for name, err in failed:
        print(f"  - {name}: {err}")
