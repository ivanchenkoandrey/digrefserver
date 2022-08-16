import logging

from rest_framework import authentication
from rest_framework import serializers
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated

from auth_app.models import Profile
from utils.custom_permissions import IsUserUpdatesHisProfile

logger = logging.getLogger(__name__)


class ProfileImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['photo']


class UpdateProfileImageView(UpdateAPIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated, IsUserUpdatesHisProfile]
    serializer_class = ProfileImageSerializer
    lookup_field = 'pk'

    def get_queryset(self, *args, **kwargs):
        pk = self.kwargs.get('pk')
        queryset = Profile.objects.filter(pk=pk)
        return queryset
