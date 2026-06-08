import os

with open('backend/app/services/storage.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_str = """from backend.app.services.redaction import redact_text

logger = logging.getLogger("firecrow.services.storage")"""

new_str = """from backend.app.services.redaction import redact_text
from backend.app.services.reporter import _is_r2_auth_error

logger = logging.getLogger("firecrow.services.storage")"""

content = content.replace(old_str, new_str)

old_str2 = """class StorageService:
    def __init__(self):
        self.s3_client = None"""

new_str2 = """class StorageService:
    def __init__(self):
        self.s3_client = None
        self.r2_bucket = settings.R2_BUCKET_NAME or os.getenv("CLOUDFLARE_R2_BUCKET") or "firecrow-reports\""""

content = content.replace(old_str2, new_str2)

with open('backend/app/services/storage.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Replaced successfully")
import os
with open('backend/app/services/storage.py', 'r', encoding='utf-8') as f:
    content = f.read()
old_str = 'from backend.app.services.redaction import redact_text\n\nlogger = logging.getLogger(\"firecrow.services.storage\")'
new_str = 'from backend.app.services.redaction import redact_text\nfrom backend.app.services.reporter import _is_r2_auth_error\n\nlogger = logging.getLogger(\"firecrow.services.storage\")'
content = content.replace(old_str, new_str)
old_str2 = 'class StorageService:\n    def __init__(self):\n        self.s3_client = None'
new_str2 = 'class StorageService:\n    def __init__(self):\n        self.s3_client = None\n        self.r2_bucket = settings.R2_BUCKET_NAME or os.getenv(\"CLOUDFLARE_R2_BUCKET\") or \"firecrow-reports\"'
content = content.replace(old_str2, new_str2)
with open('backend/app/services/storage.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('done')
