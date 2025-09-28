from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, JobViewSet, JobTaskViewSet, EquipmentViewSet,
    TechnicianDashboardView, TechnicianTaskUpdateView, TechnicianJobUpdateView,
    ProfileView, JobAnalyticsView
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("jobs", JobViewSet, basename="jobs")
router.register("tasks", JobTaskViewSet, basename="tasks")
router.register("equipment", EquipmentViewSet, basename="equipment")

urlpatterns = [
    path("", include(router.urls)),
    path("profile/", ProfileView.as_view(), name="profile"),
    
    # technician Dashboard Endpoints
    path("technician-dashboard/", TechnicianDashboardView.as_view(), name="technician-dashboard"),
    path("technician-dashboard/task/<int:task_id>/update-status/", 
         TechnicianTaskUpdateView.as_view(), name="technician-task-update"),
    path("technician-dashboard/job/<int:job_id>/update-status/", 
         TechnicianJobUpdateView.as_view(), name="technician-job-update"),

    # Admin Analytics Endpoints (ooptional feature)
    path("admin/analytics/", JobAnalyticsView.as_view(), name="job-analytics"),
]