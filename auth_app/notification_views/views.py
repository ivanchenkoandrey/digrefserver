from rest_framework import authentication, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.notification_services import get_amount_of_unread_notifications
from utils.paginates import process_offset_and_limit
from utils.query_debugger import query_debugger
from .services import get_notification_list_by_user
from ..models import Notification


class NotificationList(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    @query_debugger
    def get(cls, request, *args, **kwargs):
        offset = request.GET.get('offset')
        limit = request.GET.get('limit')
        offset, limit = process_offset_and_limit(offset, limit)
        notification_list = get_notification_list_by_user(request.user.id, offset, limit)
        return Response(data=notification_list)


class GetUnreadNotificationsCount(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    @query_debugger
    def get(cls, request, *args, **kwargs):
        data = get_amount_of_unread_notifications(request.user.id)
        return Response(data=data)


class MarkNotificationAsReadView(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    @query_debugger
    def put(cls, request, *args, **kwargs):
        pk = kwargs.get('pk')
        read = request.data.get('read')
        if read is not None and read is True:
            notification = Notification.objects.filter(pk=pk).only('id', 'read').first()
            if notification is not None:
                notification.read = True
                notification.save(update_fields=['read'])
                return Response(data=notification.to_json())
            return Response({'message': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'Укажите параметр read в значении True'}, status=status.HTTP_400_BAD_REQUEST)
