from rest_framework.permissions import BasePermission


class IsController(BasePermission):
    """
    Проверка, является ли пользователь контроллером
    """
    def has_permission(self, request, view):
        return bool(request.user
                    and request.user.privileged.filter(role__in=['C']))
