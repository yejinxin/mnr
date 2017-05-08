import os
import subprocess
from django.conf import settings
import socket
import sys

#def call_mc(action):
#    virtual_env = os.environ.get('VIRTUAL_ENV', '')
#    if virtual_env:
#        cmd = ". %s/bin/activate; " % virtual_env
#    else:
#        cmd = ""
#    cmd = cmd + "cd %s; python manage.py %s &" % (settings.BASE_DIR, action)
#    somehow, os.system does not work with uWsgi/nginx
#    os.system(cmd)

def call_mc(action):
    virtual_env = os.environ.get('VIRTUAL_ENV', '')
    if virtual_env:
        py = "%s/bin/python" % virtual_env
    else:
        py = "python"
    manage = os.path.join(settings.BASE_DIR, 'manage.py')
    cmd = ' '.join([py, manage, action])
    #print cmd
    subprocess.Popen(cmd, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)


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

