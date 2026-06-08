import re

with open("backend/app/services/storage.py", "r") as f:
    content = f.read()

upload_replacement = """        if self.s3_client is not None:
            try:
                logger.info("Uploading artifact key '%s' to S3/R2", object_key)
                self.s3_client.put_object(
                    Bucket=self.r2_bucket,
                    Key=object_key,
                    Body=data,
                    ContentType=mime_type
                )
                storage_provider = "cloudflare_r2"
            except Exception as e:
                logger.error("S3 upload failed: %s", redact_text(str(e)))
                from backend.app.config import settings
                if getattr(settings, "REPORT_LOCAL_FALLBACK", True):
                    logger.info("Falling back to local storage")
                    self._write_local_file(object_key, data)
                    storage_provider = "local"
                else:
                    raise HTTPException(status_code=500, detail="Cloud storage upload failed and local fallback is disabled.")
        else:
            from backend.app.config import settings
            if getattr(settings, "REPORT_LOCAL_FALLBACK", True):
                self._write_local_file(object_key, data)
                storage_provider = "local"
            else:
                logger.error("Cloud storage not configured and local fallback is disabled.")
                raise HTTPException(status_code=500, detail="Cloud storage not configured and local fallback is disabled.")"""

content = re.sub(
    r'^ *if self\.s3_client is not None:.*?(?=        # Save to DB)',
    upload_replacement + "\n",
    content,
    flags=re.DOTALL | re.MULTILINE
)

with open("backend/app/services/storage.py", "w") as f:
    f.write(content)
