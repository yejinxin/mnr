import os
from django.conf import settings
import socket
import sys

def call_mc(action):
    virtual_env = os.environ.get('VIRTUAL_ENV', '')
    if virtual_env:
        cmd = ". %s/bin/activate; " % virtual_env
    else:
        cmd = ""
    cmd = cmd + "cd %s; python manage.py %s &" % (settings.BASE_DIR, action)
    os.system(cmd)

def ping(ip, port, timeout=1):
    try:
        cs=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        address=(str(ip), int(port))
        status=cs.connect_ex((address))
        cs.settimeout(timeout)
        if status != 0:
            return False 
    except Exception as e:
        return False
    return True

