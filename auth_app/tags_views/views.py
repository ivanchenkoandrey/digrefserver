from rest_framework import authentication
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from auth_app.models import Reason, Tag
from .serializers import TagSerializer, TagRetrieveSerializer, ReasonSerializer


class BasicView:
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]


class TagListView(BasicView, ListAPIView):
    serializer_class = TagSerializer
    queryset = Tag.objects.filter(flags='A')


class TagDetailView(BasicView, RetrieveAPIView):
    serializer_class = TagRetrieveSerializer
    queryset = Tag.objects.filter(flags='A')


class ReasonListView(BasicView, ListAPIView):
    serializer_class = ReasonSerializer

    def get_queryset(self):
        if tags := self.request.GET.getlist('tag'):
            return Reason.objects.filter(tags__in=tags)
        return Reason.objects.all()[:10]
