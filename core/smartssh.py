
'''My customized SSH client base on paramiko.SSHClient'''
from __future__ import print_function

#import socks  
#import socket 
#socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, '127.0.0.1', 1080, False)
#socket.socket = socks.socksocket

import paramiko
from paramiko.config import SSH_PORT
import re
#import traceback
from hostinfo import get_hostinfo
from util import ping



class SmartSSHClient(paramiko.SSHClient):
    '''A smart SSHClient that could try multiple passwords on connecting.'''
    
    def is_connected(self):
        transport = self.get_transport()
        return transport and transport.is_active()
    

def cus_exec_command(host=None, prod_ip=None, mng_ip=None, cmd='hostname; id', user_='', pass_='', key_filename='', timeout=5, mergeout=False):
    if not user_:
        user_='root'
    if not pass_ and not key_filename and user_!= 'root':
        user='root'
        cmdline='su - %s -c "%s" ' % (user_, cmd)
    else:
        user=user_
        cmdline=cmd
    
    ssh = SmartSSHClient()
    try:
        ssh.connect(host=host, prod_ip=prod_ip, mng_ip=mng_ip, username=user, password=pass_, key_filename=key_filename, timeout=timeout)
    except Exception as e:
        #traceback.print_exc()
        return str(e)
    #print("cmdline is " + cmdline)
    stdin, stdout, stderr = ssh.exec_command(cmdline)
    out_=''.join(stdout.readlines())
    err_=''.join(stderr.readlines())
    ssh.close()
    if mergeout:
        return out_ + '\n---stderr---\n' + err_
    else:
        return out_, err_


if __name__=='__main__':
    ret = cus_exec_command('192.168.1.1', cmd='hostname;ls /tmp/sdfgsdf; id;', user_='fund' )
    if isinstance(ret, str):
        print(ret)
    else:
        print(ret[0])
        print(ret[1])
    exit(1)
            
