from rest_framework import authentication, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import (validate_token_request,
                       validate_delete_token_request,
                       update_or_create_fcm_token,
                       get_fcm_token_by_device_and_user_id
                       )


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


class RemoveFCMToken(APIView):
    @classmethod
    def post(cls, request, *args, **kwargs):
        device = request.data.get('device')
        user_id = request.data.get('user_id')
        if validate_delete_token_request(device, user_id):
            fcm_token = get_fcm_token_by_device_and_user_id(device, user_id)
            if fcm_token is not None:
                fcm_token.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(status=status.HTTP_404_NOT_FOUND)
