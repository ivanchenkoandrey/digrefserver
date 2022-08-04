from rest_framework.decorators import (api_view,
                                       permission_classes,
                                       authentication_classes)
from rest_framework import authentication, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from auth_app.models import Setting
from .service import validate_anonymous_mode_request, reset_anonymous_mode

import logging

logger = logging.getLogger(__name__)


@api_view(http_method_names=['GET', 'PUT'])
@authentication_classes([authentication.SessionAuthentication,
                         authentication.TokenAuthentication])
@permission_classes([IsAdminUser])
def set_anonymous_mode(request):
    setting = Setting.objects.filter(name='anonymous_mode').first()
    try:
        if request.method == 'PUT':
            if validate_anonymous_mode_request(request):
                anonymous_status = reset_anonymous_mode(setting, request.data)
                return Response({'is_anonymous': anonymous_status})
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response({'anonymous_mode': setting.value})
    except AttributeError:
        logger.error("Отсутствует настройка анонимности")
        return Response("Настройка анонимности не создана",
                        status=status.HTTP_400_BAD_REQUEST)
