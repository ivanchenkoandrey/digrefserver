from rest_framework.permissions import BasePermission
from auth_app.models import Organization


class IsController(BasePermission):
    """
    Проверка, является ли пользователь контроллером
    """
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated
                    and request.user.privileged.filter(role__in=['C']))


class IsAnonymous(BasePermission):
    """
    Проверка, является ли пользователь анонимным
    """
    def has_permission(self, request, view):
        return bool(request.user.is_anonymous)


class IsAllowedToMakePeriod(BasePermission):
    """
    Проверка, является ли пользователь администратором системы
    """

    message = 'У вас нет прав создавать новый период'

    def has_permission(self, request, view):
        top_id_list = Organization.objects.values_list('top_id', flat=True).distinct().order_by()
        return (bool(request.user.is_staff
                     or (request.user.is_authenticated
                         and request.user.filter.privileged.filter(role__in=['A'], organization_id__in=[top_id_list]))))
