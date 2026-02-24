from rest_framework.permissions import BasePermission


class IsInGroup(BasePermission):
    """
    Custom permission to check if user is in specific groups.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Allow superusers
        if request.user.is_superuser:
            return True

        # Check if user is in required groups for analytics
        required_groups = ['Admin', 'Auditor', 'FinanceOfficer']
        return request.user.groups.filter(name__in=required_groups).exists()


class IsAdminOrAuditor(BasePermission):
    """
    Permission for admin or auditor access.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        return request.user.groups.filter(name__in=['Admin', 'Auditor']).exists()


class IsReviewerOrAssigned(BasePermission):
    """
    Permission for reviewers or users assigned to specific alerts.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        # Allow if user is a reviewer
        if request.user.groups.filter(name='Reviewer').exists():
            return True

        # Allow if user is assigned to the alert
        if hasattr(obj, 'assigned_to') and obj.assigned_to == request.user:
            return True

        return False