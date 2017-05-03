#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import os.path

import logging
logger=logging.getLogger("mnrapp")

import re
from crypt import crypt
from random import choice

from django.contrib.auth.models import User
from mnrapp.models import Application
from core.hostinfo import get_hostinfo
from core.smartssh import cus_exec_command

import winrm


class MnrTask(object):
    """
    Mnr Task worker.
    """

    def __init__(self):
        super(MnrTask, self).__init__()
    
    def collect_msg(self, text):
        if text.find('---stderr---') != -1:
            parts = text.split('---stderr---')
            stdout = parts[0]
            stderr = parts[1] if len(parts) > 1 else ''
        else:
            stdout = ''
            stderr = text
        return '\n'.join(re.findall(r'\[MNR\].*?$', stdout, re.MULTILINE)) + stderr

    def work(self, app):
        logger.info("Starting working")
        app.update_status('DOING')
        for mod in app.modifications.all():
            if mod.type == 'ROOT':
                self.work_root(app, mod) 
            elif mod.type == 'DISK':
                self.work_disk(app, mod)
            elif mod.type == 'CPUMEM':
                self.work_cpumem(app, mod)
            else:
                logger.error("Impossible happens!")
        app.update_status('DONE')
        logger.info("Ending working")
   
    def work_root(self, app, mod):
        logger.info("Start working on appid=%d applicant=%s root modification=%s", app.id, app.applicant, mod)
        if mod.user == 'root':
            script='core/scripts/work_rootroot.sh'
        else:
            script='core/scripts/work_root_user.sh'
        with open(script) as f:
            _data = f.read()
        if mod.os_type == 'HPUX':
            if mod.user == 'root' and mod.password != 'FIX_PASSWORD':
                logger.warning("Bad password for %s, ignoring!", mod)
                mod.password = 'FIX_PASSWORD'
            password = crypt(mod.password, choice(("RA", "ND", "OM", "SA", "LT")))
        else:
            password = mod.password
        cmd = _data % {'user': mod.user, 'password': password}
        logger.debug(cmd)
        ret = cus_exec_command(host=mod.host, prod_ip=mod.prod_ip, mng_ip=mod.mng_ip, cmd=cmd, mergeout=True)
        logger.debug(ret)
        if ret.find("password changed successfully") != -1:
            mod.status = 'DONE'
            mo = re.search("OLD_PASS IS #(.*?)#$", ret, re.MULTILINE)
            if mo:
                mod.ori_password = mo.group(1)
            elif mod.user != 'root':
                logger.warning("OLD_PASS lost!")
        else:
            mod.status = 'ERROR'
            mod.message = self.collect_msg(ret)
        mod.save()

    def work_disk(self, app, mod):
        logger.info("Start working on appid=%d applicant=%s disk modification=%s", app.id, app.applicant, mod)
        if mod.os_type != 'LINUX':
            logger.error("Unsupported OS type for %s", mod)
            mod.status = 'ERROR'
            mod.message = "Unsupported OS type!"
            mod.save()
            return False
        with open('core/scripts/work_disk1.sh') as f:
            _data = f.read()
        cmd = _data % {'fs': mod.fs, 'size': mod.size}
        logger.debug(cmd)
        ret = cus_exec_command(host=mod.host, prod_ip=mod.prod_ip, mng_ip=mod.mng_ip, cmd=cmd, mergeout=True)
        logger.debug(ret)
        if ret.find("fs extension ok") != -1:
            mod.status = 'DONE'
        else:
            mo = re.search("New disk needed: (\d+)", ret, re.MULTILINE)
            if mo:
                size_need = mo.group(1)
                with open('core/scripts/work_disk2.ps1') as f:
                    _data = f.read()
                info = get_hostinfo(host=mod.host, prod_ip=mod.prod_ip, mng_ip=mod.mng_ip, verbose='detail')
                vc=info['vc']
                vc_account=VC_ACCOUNTS[vc]
                ps_script = _data % {'vc': vc, 'vc_user': vc_account['username'], 'vc_pass': vc_account['password'], 'host': mod.host, 'size': size_need }
                logger.debug(ps_script)
                s = winrm.Session('vSphere_client_win', auth=('vc_user', p0))
                r = s.run_ps(ps_script)
                logger.debug(r.std_out)
                logger.debug(r.std_err)
                if r.std_out.find('New disk added successfully') != -1:
                    with open('core/scripts/work_disk3.sh') as f:
                        _data = f.read()
                    cmd = _data % {'fs': mod.fs, 'size': mod.size, 'disk_size': size_need}
                    logger.debug(cmd)
                    ret = cus_exec_command(host=mod.host, prod_ip=mod.prod_ip, mng_ip=mod.mng_ip, cmd=cmd, mergeout=True)
                    logger.debug(ret)
                    if ret.find("fs extension ok") != -1:
                        mod.status = 'DONE'
                    else:
                        mod.status = 'ERROR'
                        mod.message = self.collect_msg(ret)
                else:
                    mod.status = 'ERROR'
                    mod.message = self.collect_msg(r.std_out + r.std_err)
            else:
                mod.status = 'ERROR'
                mod.message = self.collect_msg(ret)
        mod.save()
        

    def work_cpumem(self, app, mod):
        logger.info("Start working on appid=%d applicant=%s cpu/mem modification=%s", app.id, app.applicant, mod)
        info = get_hostinfo(host=mod.host, prod_ip=mod.prod_ip, mng_ip=mod.mng_ip, verbose='detail')
        if not info.get('vc', None):
            logger.error("vc info not found! %s", mod)
            mod.status = 'ERROR'
            mod.message = "vc info not found!"
            mod.save()
            return False
        if mod.os_type != 'LINUX' and mod.os_type != 'WINDOWS':
            logger.error("Unsupported OS type for %s", mod)
            mod.status = 'ERROR'
            mod.message = "Unsupported OS type!"
            mod.save()
            return False
        with open('core/scripts/work_cpumem.ps1') as f:
            _data = f.read()
        vc=info['vc']
        vc_account=VC_ACCOUNTS[vc]
        ps_script = _data % {'vc': vc, 'vc_user': vc_account['username'], 'vc_pass': vc_account['password'], 
            'host': mod.host, 'cpu_new': mod.cpu_new, 'mem_new': mod.mem_new }
        logger.debug(ps_script)
        s = winrm.Session('vSphere_client_win', auth=('vc_user', p0))
        r = s.run_ps(ps_script)
        logger.debug(r.std_out)
        logger.debug(r.std_err)
        if r.std_out.find("Mnr operation success") != -1:
            mod.status = 'DONE'
        else:
            mod.status = 'ERROR'
            mod.message = self.collect_msg(r.std_out + r.std_err)
        mod.save()



                
    def recover(self, app):
        logger.info("Starting recovering")
        app.update_status('RECOVERING')
        for mod in app.modifications.all():
            if mod.type == 'ROOT':
                self.recover_root(app, mod) 
            elif mod.type == 'CPUMEM':
                self.recover_cpumem(app, mod)
            else:
                logger.error("Impossible happens!")
        app.update_status('FINISHED')
        logger.info("Ending recovering")

    def recover_root(self, app, mod):
        logger.info("Start recovering on appid=%d applicant=%s root modification=%s", app.id, app.applicant, mod)
        hostnum = ''.join(re.findall(r'\d', mod.host))
        script='core/scripts/recover_root.sh'
        with open(script) as f:
            _data = f.read()
        if mod.user == 'root':
            password = GENERATE_PASSWORD
            if mod.os_type == 'HPUX':
                password = crypt(password, choice(("RA", "ND", "OM", "SA", "LT")))
        elif mod.ori_password:
            password = mod.ori_password
        else:
            mod.status = 'ERROR'
            mod.message = "Original password lost?!"
            logger.error(mod.message)
            mod.save()
            return False

        cmd = _data % {'user': mod.user, 'password': password}
        logger.debug(cmd)
        ret = cus_exec_command(host=mod.host, prod_ip=mod.prod_ip, mng_ip=mod.mng_ip, cmd=cmd, mergeout=True)
        logger.debug(ret)
        if ret.find("password changed successfully") != -1:
            mod.status = 'FINISHED'
        else:
            mod.status = 'ERROR'
            mod.message = self.collect_msg(ret)
        mod.save()

    def recover_cpumem(self, app, mod):
        logger.info("Start recovering on appid=%d applicant=%s cpu/mem modification=%s", app.id, app.applicant, mod)
        info = get_hostinfo(host=mod.host, prod_ip=mod.prod_ip, mng_ip=mod.mng_ip, verbose='detail')
        with open('core/scripts/recover_cpumem.ps1') as f:
            _data = f.read()
        vc=info['vc']
        vc_account=VC_ACCOUNTS[vc]
        ps_script = _data % {'vc': vc, 'vc_user': vc_account['username'], 'vc_pass': vc_account['password'], 
                                'host': mod.host, 'cpu_ori': mod.cpu_ori, 'mem_ori': mod.mem_ori }
        logger.debug(ps_script)
        s = winrm.Session('vSphere_client_win', auth=('vc_user', p0))
        r = s.run_ps(ps_script)
        logger.debug(r.std_out)
        logger.debug(r.std_err)
        if r.std_out.find("Mnr operation success") != -1:
            mod.status = 'FINISHED'
        else:
            mod.status = 'ERROR'
            mod.message = self.collect_msg(r.std_out + r.std_err)
        mod.save()


if __name__ == '__main__':
    task=MnrTask()
    task.work()
    task.recover()

        
