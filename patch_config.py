import re

with open("backend/app/config.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "if not self.DEBUG:" in line:
        lines[i] = "        if not self.DEBUG:\n"
        lines[i+1] = "            if self.SECRET_KEY.strip() in insecure_dev_values:\n"
        lines[i+2] = "                raise ValueError(\"SECRET_KEY is required in production and cannot use a known development value.\")\n"
        lines[i+3] = "            if len(self.SECRET_KEY) < 32:\n"
        lines[i+4] = "                raise ValueError(\"SECRET_KEY must be at least 32 characters in production.\")\n"
        lines[i+5] = "            if self.DATABASE_URL.startswith(\"sqlite\"):\n"
        lines[i+6] = "                raise ValueError(\"SQLite DATABASE_URL is only allowed when DEBUG=True.\")\n"
        lines[i+7] = "            if self.FIRE_CROW_SCANNER_IMAGE.endswith(\":latest\"):\n"
        lines[i+8] = "                raise ValueError(\"FIRE_CROW_SCANNER_IMAGE must be pinned in production and cannot use :latest.\")\n"
        lines[i+9] = "            if not getattr(self, \"REPORT_LOCAL_FALLBACK\", True):\n"
        lines[i+10] = "                if not self.R2_ACCESS_KEY_ID or not self.R2_SECRET_ACCESS_KEY or not self.R2_BUCKET_NAME or not self.R2_ENDPOINT_URL:\n"
        lines[i+11] = "                    raise ValueError(\"Cloud storage configuration is missing, but REPORT_LOCAL_FALLBACK is False.\")\n"

with open("backend/app/config.py", "w") as f:
    f.writelines(lines)
