from rest_framework import authentication
from rest_framework.generics import (ListAPIView, ListCreateAPIView,
                                     RetrieveAPIView)
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from auth_app.models import Reason, Tag
from .serializers import TagSerializer, TagRetrieveSerializer, ReasonSerializer
from rest_framework.response import Response


class BasicView:
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]


class TagList(BasicView, APIView):

    @classmethod
    def get(cls, request, *args, **kwargs):
        tags = [tag.to_json_name_only() for tag in Tag.objects.all()]
        return Response({'tags': tags})


class TagDetailView(BasicView, RetrieveAPIView):
    serializer_class = TagRetrieveSerializer
    queryset = Tag.objects.filter(flags='A')


class ReasonListView(BasicView, ListAPIView):
    serializer_class = ReasonSerializer

    def get_queryset(self):
        if tags := self.request.GET.getlist('tag'):
            return Reason.objects.filter(tags__in=tags)
        return Reason.objects.all()[:10]
