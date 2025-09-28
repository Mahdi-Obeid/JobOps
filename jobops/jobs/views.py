from rest_framework import viewsets, generics, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import User, Job, JobTask, Equipment
from .serializers import (UserSerializer, JobSerializer, JobTaskSerializer, 
                         EquipmentSerializer)
from .permissions import (IsAdmin, IsAdminOrSalesAgent,  CanManageTasks)


@extend_schema(tags=['Users - Admin Only'])
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    @extend_schema(
        description="Create a new user account with specified role. ONLY admins can create users.",
        examples=[
            OpenApiExample(
                "Create Admin User",
                value={
                    "username": "admin_user",
                    "email": "admin@company.com",
                    "first_name": "John",
                    "last_name": "Admin",
                    "role": "ADMIN",
                    "password": "password123"
                }
            ),
            OpenApiExample(
                "Create Technician",
                value={
                    "username": "tech_user",
                    "email": "technician@company.com",
                    "first_name": "Jane",
                    "last_name": "Tech",
                    "role": "TECHNICIAN",
                    "password": "password123"
                }
            ),
            OpenApiExample(
                "Create Sales Agent",
                value={
                    "username": "sales_user",
                    "email": "sales@company.com",
                    "first_name": "Bob",
                    "last_name": "Sales",
                    "role": "SALES_AGENT",
                    "password": "password123"
                }
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(tags=["Jobs - Admin/Sales Only"])
class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [IsAdminOrSalesAgent]

    @extend_schema(
        description="Create a new job and assign it to a technician. ONLY admins and sales agents can create jobs.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


@extend_schema(tags=["Tasks - Admin/Sales Only"])
class JobTaskViewSet(viewsets.ModelViewSet):
    serializer_class = JobTaskSerializer
    permission_classes = [CanManageTasks]

    def get_queryset(self):
        return JobTask.objects.all()

    @extend_schema(
        summary="create a new task",
        description="Create a new task for a job with optional equipment requirements.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


@extend_schema(tags=["Equipment - Admin/Sales Only"])
class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    permission_classes = [IsAdminOrSalesAgent]

    @extend_schema(
        description="Add new equipment to the global catalog.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


# ============= TECHNICIAN DASHBOARD ENDPOINTS =============

@extend_schema(tags=["Technician Dashboard"])
class TechnicianDashboardView(APIView):
    """Main dashboard view for technicians showing their assigned jobs and tasks"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Returns all jobs assigned to the authenticated technician, organized by schedule (today, upcoming, overdue, unscheduled). Includes active tasks and required equipment for each job."
    )
    def get(self, request):
        user = request.user

        if not hasattr(user, 'role') or user.role != "TECHNICIAN":
            return Response({"detail": "This endpoint is only for technicians"}, status=403)

        jobs = Job.objects.filter(assigned_to=user).prefetch_related('jobtask_set__jobtaskequipment_set__equipment')

        if not jobs.exists():
            return Response({"detail": "No jobs assigned yet"}, status=200)

        # Group jobs by status and scheduled date
        grouped_jobs = {
            "today": [],
            "upcoming": [],
            "overdue": [],
            "unscheduled": []
        }
        
        from datetime import date
        today = date.today()

        for job in jobs:
            if job.status == "COMPLETED":
                continue
                
            # Get active tasks for this job
            active_tasks = job.jobtask_set.filter(
                status__in=["NOT_STARTED", "IN_PROGRESS"]
            ).order_by('order')
            
            job_data = {
                "id": job.id,
                "title": job.title,
                "client_name": job.client_name,
                "status": job.status,
                "priority": job.priority,
                "scheduled_date": job.scheduled_date,
                "description": job.description,
                "tasks_count": job.jobtask_set.count(),
                "completed_tasks": job.jobtask_set.filter(status="COMPLETED").count(),
                "active_tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "order": task.order,
                        "status": task.status,
                        "required_equipment": [
                            {
                                "equipment_name": req.equipment.name,
                                "equipment_type": req.equipment.eq_type,
                                "quantity": req.quantity,
                                "notes": req.notes
                            }
                            for req in task.jobtaskequipment_set.all()
                        ]
                    }
                    for task in active_tasks
                ]
            }
            
            if not job.scheduled_date:
                grouped_jobs["unscheduled"].append(job_data)
            elif job.scheduled_date.date() == today:
                grouped_jobs["today"].append(job_data)
            elif job.scheduled_date.date() > today:
                grouped_jobs["upcoming"].append(job_data)
            else:
                grouped_jobs["overdue"].append(job_data)

        return Response({
            "jobs_by_schedule": grouped_jobs,
            "summary": {
                "total_active_jobs": len([j for group in grouped_jobs.values() for j in group]),
                "today_count": len(grouped_jobs["today"]),
                "overdue_count": len(grouped_jobs["overdue"])
            }
        })


# Custom serializer for status updates
class TaskStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=JobTask.STATUS_CHOICES,
        help_text="New status for the task"
    )

class JobStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Job.STATUS_CHOICES,
        help_text="New status for the job"
    )


@extend_schema(tags=["Technician Dashboard"])
class TechnicianTaskUpdateView(APIView):
    """Update task status for technician's assigned jobs"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Update the status of a task assigned to the authenticated technician. Auto-sets completed_at timestamp when status is changed to COMPLETED.",
        parameters=[
            OpenApiParameter("task_id", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID of the task to update"),
        ],
        request=TaskStatusUpdateSerializer,
        examples=[
            OpenApiExample(
                "Start Task",
                value={"status": "IN_PROGRESS"},
                description="Mark task as in progress"
            ),
            OpenApiExample(
                "Complete Task",
                value={"status": "COMPLETED"},
                description="Mark task as completed (will auto-set completion timestamp)"
            ),
            OpenApiExample(
                "Reset Task",
                value={"status": "NOT_STARTED"},
                description="Reset task to not started"
            )
        ]
    )
    def patch(self, request, task_id):
        user = request.user
        
        if not hasattr(user, 'role') or user.role != "TECHNICIAN":
            return Response({"detail": "This endpoint is only for technicians"}, status=403)

        # Get the task and verify it belongs to an assigned job
        task = get_object_or_404(JobTask, id=task_id)
        
        if task.job.assigned_to != user:
            return Response(
                {"detail": "You can only update tasks for jobs assigned to you"}, 
                status=403
            )

        # Validate status
        new_status = request.data.get('status')
        if new_status not in ['NOT_STARTED', 'IN_PROGRESS', 'COMPLETED']:
            return Response(
                {"detail": "Invalid status. Must be one of: NOT_STARTED, IN_PROGRESS, COMPLETED"}, 
                status=400
            )

        # Update task status
        old_status = task.status
        task.status = new_status
        
        # Auto-set completed_at when status changes to COMPLETED
        if new_status == "COMPLETED" and not task.completed_at:
            task.completed_at = timezone.now()
        elif new_status != "COMPLETED":
            task.completed_at = None
            
        task.save()

        return Response({
            "message": f"Task status updated from {old_status} to {new_status}",
            "task": {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "completed_at": task.completed_at
            }
        })


@extend_schema(tags=["Technician Dashboard"])
class TechnicianJobUpdateView(APIView):
    """Update job status for technician's assigned jobs"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Update the status of a job assigned to the authenticated technician. Cannot complete a job until all its tasks are completed.",
        parameters=[
            OpenApiParameter("job_id", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID of the job to update"),
        ],
        request=JobStatusUpdateSerializer,
        examples=[
            OpenApiExample(
                "Start Job",
                value={"status": "IN_PROGRESS"},
                description="Mark job as in progress"
            ),
            OpenApiExample(
                "Complete Job",
                value={"status": "COMPLETED"},
                description="Mark job as completed (only allowed if all tasks are completed)"
            ),
            OpenApiExample(
                "Cancel Job",
                value={"status": "CANCELLED"},
                description="Cancel the job"
            )
        ]
    )
    def patch(self, request, job_id):
        user = request.user
        
        if not hasattr(user, 'role') or user.role != "TECHNICIAN":
            return Response({"detail": "This endpoint is only for technicians"}, status=403)

        # Get the job and verify it's assigned to this technician
        job = get_object_or_404(Job, id=job_id)
        
        if job.assigned_to != user:
            return Response(
                {"detail": "You can only update jobs assigned to you"}, 
                status=403
            )

        # Validate status
        new_status = request.data.get('status')
        if new_status not in ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']:
            return Response(
                {"detail": "Invalid status. Must be one of: PENDING, IN_PROGRESS, COMPLETED, CANCELLED"}, 
                status=400
            )

        # Check if trying to complete job with incomplete tasks
        if new_status == "COMPLETED":
            incomplete_tasks = job.jobtask_set.exclude(status="COMPLETED")
            if incomplete_tasks.exists():
                incomplete_list = [{"id": t.id, "title": t.title, "status": t.status} 
                                 for t in incomplete_tasks]
                return Response({
                    "detail": "Cannot complete job until all tasks are completed",
                    "incomplete_tasks": incomplete_list
                }, status=400)

        # Update job status
        old_status = job.status
        job.status = new_status
        job.save()

        return Response({
            "message": f"Job status updated from {old_status} to {new_status}",
            "job": {
                "id": job.id,
                "title": job.title,
                "status": job.status,
                "client_name": job.client_name
            }
        })