from django.core.cache import cache
from django.conf import settings
import codecs
import os.path
import re

import logging
logger = logging.getLogger(__name__)

def get_wzb_data():
    wzbdata = cache.get('WZBDATA')
    if not wzbdata:
        with codecs.open(os.path.join(settings.BASE_DIR, 'util/hostinfo.csv'), encoding='utf-8') as wzbfile:
            wzbdata = wzbfile.read()
            cache.set('WZBDATA', wzbdata, 3600)
    return wzbdata


def gen_obj(line, i=0, verbose='info'):
    info = line.split(',')
    obj = {}
    obj['id'] = i
    obj['host'] = info[6]
    obj['prod_ip'] = info[10]
    obj['mng_ip'] = info[11]
    if verbose == 'info' or verbose == 'detail':
        _os = info[7].upper()
        if _os == 'AIX' or _os == 'HPUX':
            obj['os_type'] = _os
        elif _os.startswith('WIN'):
            obj['os_type'] = 'WINDOWS'
        else:
            obj['os_type'] = 'LINUX'
        obj['sys'] = info[1]
        obj['desp'] = info[5]
    if verbose == 'detail':
        obj['subsys'] = info[2]
        obj['env'] = info[3]
        obj['cpu'] = info[8]
        obj['mem'] = info[9]
        if len(info) > 12:
            obj['vc'] = info[12]
    return obj


def get_hostinfo(host=None, prod_ip=None, mng_ip=None, verbose='info'):
    wzbdata = get_wzb_data()
    if host: host = host.upper()
    if prod_ip: prod_ip = prod_ip.replace('.', r'\.') 
    if mng_ip: mng_ip = mng_ip.replace('.', r'\.') 
    if host and prod_ip and mng_ip:
        pattern = r'^.*?\b%s\b.*?\b%s,%s\b.*?$' % (host, prod_ip, mng_ip)
    elif host and prod_ip:
        pattern = r'^.*?\b%s\b.*?\b%s\b.*?$' % (host, prod_ip)
    elif host and mng_ip:
        pattern = r'^.*?\b%s\b.*?\b%s\b.*?$' % (host, mng_ip)
    elif prod_ip and mng_ip:
        pattern = r'^.*?\b%s,%s\b.*?$' % (prod_ip, mng_ip)
    elif host:
        pattern = r'^.*?\b%s\b.*?$' % (host,)
    elif prod_ip:
        pattern = r'^.*?\b%s\b.*?$' % (prod_ip,)
    elif mng_ip:
        pattern = r'^.*?\b%s\b.*?$' % (mng_ip,)
    else:
        logger.error("host, prod_ip, mng_ip cannot be None in the same time!")
        return {}

    lines = re.findall(pattern, wzbdata, re.MULTILINE)
    if not lines:
        return {}
    if len(lines) > 1:
        logger.warning("Multiple matches found during hostinfo validation!")
    obj = gen_obj(lines[0], verbose=verbose)
    return obj

