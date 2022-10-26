from rest_framework import authentication, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.fcm_views.services import validate_token_request
from auth_app.models import FCMToken


class SaveFCMToken(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def post(cls, request, *args, **kwargs):
        token = request.data.get('token')
        if token is not None:
            token_object, state = FCMToken.objects.get_or_create(token=token, user=request.user)
            if state:
                return Response({"token": token_object.token}, status=status.HTTP_201_CREATED)
            return Response({"token": token_object.token}, status=status.HTTP_200_OK)
        return Response("Отсутствует поле token",
                        status=status.HTTP_400_BAD_REQUEST)


class RefreshFCMToken(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def post(cls, request, *args, **kwargs):
        old_token = request.data.get('old_token')
        new_token = request.data.get('new_token')
        if validate_token_request(old_token, new_token):
            old_token_object = FCMToken.objects.filter(token=old_token, user=request.user).first()
            if old_token_object is not None:
                old_token_object.token = new_token
                old_token_object.save(update_fields=['token'])
                return Response({"token": new_token}, status=status.HTTP_200_OK)
            return Response("Указанный старый токен не найден", status=status.HTTP_404_NOT_FOUND)
