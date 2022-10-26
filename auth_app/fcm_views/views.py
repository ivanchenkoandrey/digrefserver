from rest_framework import authentication, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import (validate_token_request,
                       update_or_create_fcm_token)


class SetFCMToken(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def post(cls, request, *args, **kwargs):
        device = request.data.get('device')
        token = request.data.get('token')
        if validate_token_request(device, token):
            fcm_token, created = update_or_create_fcm_token(device, token, request.user)
            response_data = {"token": token, "device": device}
            if created:
                return Response(response_data, status=status.HTTP_201_CREATED)
            return Response(response_data)
