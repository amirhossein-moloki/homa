from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    """
    Custom permission to only allow users with the ADMIN role to access the view.
    """

    def has_permission(self, request, view):
        # Check if the user is authenticated and has the 'ADMIN' role.
        return bool(
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == 'ADMIN'
        )
