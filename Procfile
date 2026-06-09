# ==============================================================================
# FIRE CROW HEROKU PROCFILE
# ==============================================================================
# You can choose one of the following configurations depending on your needs.
# Uncomment the line you want to use and comment out the others.
# ==============================================================================

# OPTION 1: Run BOTH Backend and Frontend (Recommended - FastAPI serves Next.js static export)
# Note: For this to work, you must build the frontend first so that frontend/out exists.
# You can do this by adding a build step or using Heroku multi-buildpacks to run Next.js build.
web: PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT

# OPTION 2: Run Backend API ONLY
# Use this if you are hosting the Next.js frontend separately (e.g. on Vercel or Netlify)
# web: PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT

# OPTION 3: Run Frontend ONLY (SSR Next.js Node server)
# Note: You must remove `output: "export"` from `frontend/next.config.ts` first.
# web: npm run start --prefix frontend -- -p $PORT

# Optional Celery worker process (only if you have Redis configured on Heroku)
# worker: PYTHONPATH=. celery -A backend.app.workers.celery_app:celery_app worker --loglevel=info
