import logging

from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class IsSystemAdmin(BasePermission):
    """
    Проверка, что пользователь является администратором системы
    """
    message = 'Вы не являетесь администратором системы'

    def has_permission(self, request, view):
        return bool(request.user.is_superuser)


class IsController(BasePermission):
    """
    Проверка, является ли пользователь контроллером
    """
    message = 'Вы не являетесь контроллером или администратором'

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_staff or (request.user.is_authenticated
                    and request.user.privileged.filter(role__in=['A', 'C'])))


class IsAnonymous(BasePermission):
    """
    Проверка, является ли пользователь анонимным
    """

    def has_permission(self, request, view):
        return bool(request.user.is_anonymous)


class IsOrganizationAdmin(BasePermission):
    """
    Проверка, является ли пользователь администратором организации
    """

    message = 'Вы не являетесь администратором организации'

    def has_permission(self, request, view):
        if request.user.is_authenticated:
            user_organization_pk = request.user.profile.organization.pk
            user_privileged_organization = request.user.privileged.filter(
                role='A', organization__top_id=user_organization_pk).first()
            if user_privileged_organization is not None:
                return True
        return False


class IsDepartmentAdmin(BasePermission):
    """
    Проверка, является ли пользователь администратором подразделения
    """
    message = 'Вы не являетесь администратором подразделения'

    def has_permission(self, request, view):
        if request.user.is_authenticated:
            users_department_pk = request.user.profile.department.pk
            users_privileged_department = request.user.privileged.filter(
                role='A', organization_id=users_department_pk).first()
            if users_privileged_department is not None:
                return True
        return False


class IsUserUpdatesHisProfile(BasePermission):
    """
    Проверка, что пользователь обновляет свой профиль, а не чей-то ещё
    """
    message = "Вы не можете изменить данные чужого профиля"

    def has_object_permission(self, request, view, obj):
        return bool(request.user.is_authenticated
                    and request.user.profile.pk == obj.pk)


class IsUserUpdatesHisContact(BasePermission):
    """
    Проверка, что пользователь обновляет свой контакт, а не чей-то ещё
    """
    message = "Вы не можете изменить данные чужого контакта"

    def has_object_permission(self, request, view, obj):
        return bool(request.user.is_authenticated
                    and request.user.profile.pk == obj.profile.pk)
