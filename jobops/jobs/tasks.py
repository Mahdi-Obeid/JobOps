from celery import shared_task
from django.utils import timezone
from .models import Job

@shared_task
def check_overdue_jobs():
    """
    Background task that runs daily to check if jobs are overdue.
    A job is considered overdue if:
    - Status is not COMPLETED or CANCELLED
    - scheduled_date is in the past
    """
    now = timezone.now()
    
    # Find jobs that should be marked as overdue
    overdue_jobs = Job.objects.filter(
        scheduled_date__lt=now,
        status__in=['PENDING', 'IN_PROGRESS'],
        overdue=False
    )
    
    # Mark them as overdue
    updated_count = overdue_jobs.update(overdue=True)
    
    # Find jobs that are no longer overdue (scheduled date changed or completed)
    not_overdue_jobs = Job.objects.filter(
        overdue=True
    ).exclude(
        scheduled_date__lt=now,
        status__in=['PENDING', 'IN_PROGRESS']
    )
    
    # Unmark them
    cleared_count = not_overdue_jobs.update(overdue=False)
    
    return {
        'marked_overdue': updated_count,
        'cleared_overdue': cleared_count,
        'timestamp': now.isoformat()
    }