from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    # role choices for different user types
    ROLE_CHOICES = [
        ("ADMIN", "Administrator"),
        ("TECHNICIAN", "Technician"),
        ("SALES_AGENT", "Sales Agent"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="TECHNICIAN")

    # override inherited fields to make them REQUIRED
    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    # timestamp field
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role"], name="idx_users_role"),
            models.Index(fields=["is_active"], name="idx_users_active"),
        ]

    # return username and role
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Job(models.Model):
    # status choices for different tasks
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    # priority choices for urgency of a task
    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("URGENT", "Urgent"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    client_name = models.CharField(max_length=255)
    scheduled_date = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="MEDIUM",
    )

    # foreign key relationships
    created_by = models.ForeignKey(
        User,
        # delete jobs when creator is deleted
        on_delete=models.CASCADE,
        related_name='created_jobs',
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        # only technicians can be assigned
        limit_choices_to={"role": "TECHNICIAN"},
        related_name='assigned_jobs',
    )

    # timestamp fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # boolean field for celery
    overdue = models.BooleanField(default=False)

    class Meta:
        db_table = "job"
        indexes = [
            models.Index(fields=["status"], name="idx_jobs_status"),
            models.Index(fields=["priority"], name="idx_jobs_priority"),
            models.Index(fields=["scheduled_date"], name="idx_jobs_scheduled_date"),
            models.Index(fields=["assigned_to", "status"], name="idx_jobs_assigned_status"),
            models.Index(fields=["created_by"], name="idx_jobs_created_by"),
        ]

        ordering = ["-created_at"]  # Newest jobs first by default

    # shows job title, client, and current status
    def __str__(self):
        return f"{self.title} - {self.client_name} ({self.get_status_display()})"


class JobTask(models.Model):
    # status choices for a task
    STATUS_CHOICES = [
        ("NOT_STARTED", "Not Started"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    order = models.PositiveIntegerField(default=1)
    completed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="NOT_STARTED",
    )

    job = models.ForeignKey(
        Job,
        # delete tasks when job is deleted
        on_delete=models.CASCADE,
    )

    # timestamp fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_task"
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["job", "order"]),
        ]

        # ensure order is unique within the same job
        unique_together = ["job", "order"]
        ordering = ["job", "order"]  # default ordering

    # return job title, task title, and order number
    def __str__(self):
        return f"{self.job.title} - {self.title} (Step {self.order})"


class Equipment(models.Model):
    name = models.CharField(max_length=255)
    eq_type = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    # timestamp fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "equipment"
        indexes = [
            models.Index(fields=["eq_type"], name="idx_equipment_type"),
            models.Index(fields=["is_active"], name="idx_equipment_active"),
            models.Index(fields=["serial_number"], name="idx_equipment_serial"),
        ]
        ordering = ["eq_type", "name"]

    # Return equipment name, type, and serial number
    def __str__(self):
        return f"{self.name} ({self.eq_type}) - SN: {self.serial_number}"


class JobTaskEquipment(models.Model):
    job_task = models.ForeignKey(
        JobTask,
        on_delete=models.CASCADE,
    )
    equipment = models.ForeignKey(
        Equipment,
        # don't allow deletion of equipment in use
        on_delete=models.RESTRICT,
    )

    quantity = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)

    # timestamp field
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "job_task_equipment"
        indexes = [
            models.Index(fields=["job_task"], name="idx_jte_task_id"),
            models.Index(fields=["equipment"], name="idx_jte_equipment_id"),
        ]
        # Prevent duplicate equipment per task
        unique_together = ["job_task", "equipment"]

    # return task description, equipment name, and quantity
    def __str__(self):
        return f"{self.job_task} requires {self.quantity}x {self.equipment.name}"
