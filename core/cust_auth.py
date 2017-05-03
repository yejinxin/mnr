# -*- coding: utf-8 -*-
import requests
from django.contrib.auth.models import User
from django.conf import settings

class FlpmAuthBackend(object):
    """
    Authentication via FLPM interface.
    """
    POST_URL="http://FLPM:8000/service/login"

    def authenticate(self, username=None, password=None):
        r=requests.post(self.POST_URL, json={ "username": username, "password": password })
        if r.status_code==200:
            data=r.json()
            if data.get('flag', None):
                try:
                    user=User.objects.get(username=username)
                except User.DoesNotExist:
                    nickname=data.get('nickname', '')
                    email=data.get('email', '')
                    user=User(username=username, email=email, first_name=nickname[1:], last_name=nickname[:1])
                    user.set_password(password)
                    if username in settings.STAFF:
                        user.is_staff = True
                    user.save()
                return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

