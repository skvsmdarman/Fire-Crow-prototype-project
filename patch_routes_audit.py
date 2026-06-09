with open("backend/app/api/routes_audit.py", "r") as f:
    content = f.read()

search = """    if not celery_alive:
        logger.warning("Celery worker heartbeat missing or Redis unreachable. Falling back to local BackgroundTasks.")
        async def _run_with_limit():
            async with _bg_semaphore:
                await asyncio.to_thread(
                    execute_audit_job,
                    job_id,
                    user_id,
                    repo_url,
                    repo_branch,
                    custom_email,
                )
        background_tasks.add_task(_run_with_limit)
        return"""

replace = """    if not celery_alive:
        logger.warning("Celery worker heartbeat missing or Redis unreachable. Falling back to local BackgroundTasks.")
        if _bg_semaphore.locked():
            raise HTTPException(
                status_code=429,
                detail="Too Many Requests: System is currently under heavy load. Please try again later."
            )

        async def _run_with_limit():
            async with _bg_semaphore:
                await asyncio.to_thread(
                    execute_audit_job,
                    job_id,
                    user_id,
                    repo_url,
                    repo_branch,
                    custom_email,
                )
        background_tasks.add_task(_run_with_limit)
        return"""

if search in content:
    content = content.replace(search, replace)
    with open("backend/app/api/routes_audit.py", "w") as f:
        f.write(content)
    print("Patched routes_audit.py")
else:
    print("Search string not found")
