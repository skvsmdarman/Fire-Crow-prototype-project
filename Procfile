release: alembic -c Fire-Crow-/backend/alembic.ini upgrade head
web: PYTHONPATH=Fire-Crow-/backend uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
worker: PYTHONPATH=Fire-Crow-/backend celery -A app.workers.celery_app:celery_app worker --loglevel=info --concurrency=2
beat: PYTHONPATH=Fire-Crow-/backend celery -A app.workers.celery_app:celery_app beat --loglevel=info
