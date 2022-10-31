from rest_framework import authentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.paginates import process_offset_and_limit
from utils.query_debugger import query_debugger
from .services import get_notification_list_by_user


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
