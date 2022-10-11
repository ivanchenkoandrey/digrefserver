import logging

from rest_framework.authentication import (TokenAuthentication,
                                           SessionAuthentication)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.paginates import process_offset_and_limit
from .service import get_events_list, get_events_data

logger = logging.getLogger(__name__)


class EventListView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get(cls, request, *args, **kwargs):
        offset = request.GET.get('offset')
        limit = request.GET.get('limit')
        offset, limit = process_offset_and_limit(offset, limit)
        feed_data = get_events_list(request, offset, limit)
        return Response(feed_data)


class FeedView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get(cls, request, *args, **kwargs):
        offset = request.GET.get('offset')
        limit = request.GET.get('limit')
        offset, limit = process_offset_and_limit(offset, limit)
        return Response(get_events_data(offset, limit))
