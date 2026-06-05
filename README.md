# Fire Crow

## Concurrent local startup

From the repository root, start the local project stack with:

```powershell
npm run dev
```

That launcher starts:
- the FastAPI backend on the first free port at or after `8000`
- the Next.js frontend on the first free port at or after `3000`
- the Celery worker when Redis is reachable on `127.0.0.1:6379`

The launcher prints the exact ports it selected and injects the matching `NEXT_PUBLIC_API_URL` into the frontend process.
If a healthy backend or frontend is already running on the requested port, the launcher reuses it instead of starting a duplicate process.

If Redis is not running, the launcher skips the worker and the backend falls back to local background execution.

To force frontend + backend only:

```powershell
npm run dev:no-worker
```

To request specific starting ports:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-dev.ps1 --skip-worker --backend-port 8010 --frontend-port 3001
```
