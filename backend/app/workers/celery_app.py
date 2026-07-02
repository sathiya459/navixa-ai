from celery import Celery

from app.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "navixa",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# NAVIXA Watch groundwork (Section 2, Phase 5): poll for due scheduled
# discoveries every 5 minutes rather than registering one dynamic Celery
# Beat entry per schedule, since Beat's schedule is code-defined and this
# platform doesn't otherwise depend on a DB-backed scheduler (e.g.
# django-celery-beat). Requires running `celery -A app.workers.celery_app
# beat` alongside the worker for this to actually fire.
celery_app.conf.beat_schedule = {
    "navixa-watch-check-scheduled-discoveries": {
        "task": "navixa.check_scheduled_discoveries",
        "schedule": 300.0,
    },
}
