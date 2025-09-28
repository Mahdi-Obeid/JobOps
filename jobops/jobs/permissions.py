from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "ADMIN"


class IsAdminOrSelf(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.role == "ADMIN" or obj == request.user


class IsAdminOrSalesAgent(BasePermission):
    """Only Admins or SalesAgents can create/edit jobs"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ["ADMIN", "SALES_AGENT"]


class IsAssignedTechnician(BasePermission):
    """Only assigned Technicians can update job progress"""
    def has_object_permission(self, request, view, obj):
        return (request.user.is_authenticated and 
                request.user.role == "TECHNICIAN" and 
                obj.assigned_to == request.user)


class CanManageTasks(BasePermission):
    """Admins and Sales Agents can manage tasks, Technicians use dashboard endpoints only"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Technicians should NOT access the general task endpoints
        if request.user.role == "TECHNICIAN":
            return False
        
        if request.method in ['GET']:
            return True  # Admins and Sales Agents can view
        elif request.method in ['POST']:
            # Only Admins and Sales Agents can create tasks
            return request.user.role in ["ADMIN", "SALES_AGENT"]
        
        return request.user.role in ["ADMIN", "SALES_AGENT"]

    def has_object_permission(self, request, view, obj):
        # Technicians should NOT access general task endpoints
        if request.user.role == "TECHNICIAN":
            return False
            
        # Admins and Sales Agents can update any task
        return request.user.role in ["ADMIN", "SALES_AGENT"]