from rest_framework.authentication import (TokenAuthentication,
                                           SessionAuthentication)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .service import get_events_list
from utils.query_debugger import query_debugger


class EventListView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    @query_debugger
    def get(cls, request, *args, **kwargs):
        feed_data = get_events_list(request)
        return Response(feed_data)
