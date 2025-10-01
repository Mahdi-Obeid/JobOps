import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jobops.settings')

app = Celery('jobops')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Schedule periodic tasks
app.conf.beat_schedule = {
    'check-overdue-jobs-daily': {
        'task': 'jobs.tasks.check_overdue_jobs',
        'schedule': crontab(hour=0, minute=0),  # Run daily at midnight
    },
}