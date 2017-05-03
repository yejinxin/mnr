import json
import re
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from core.hostinfo import get_wzb_data, gen_obj


class HostInfoView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q')
        verbose = request.GET.get('v', 'info')
        category = request.GET.get('c', 'all')
        if not query:
            return JsonResponse({'ret': 'bad', 'num': 0, 'objs': [], 'message': 'q param missing'})
        objs = []
        query = query.upper().replace('.', r'\.')
        wzbdata = get_wzb_data()
        i = 0
        exact = re.findall(r'^.*?\b%s\b.*?$' % query, wzbdata, re.MULTILINE)[:10]
        for line in exact:
            i += 1
            obj = gen_obj(line, i, verbose)
            objs.append(obj)
        if len(objs) < 10:
            possible = re.findall(r'^.*?\b%s.*?$' % query, wzbdata, re.MULTILINE)
            for line in possible:
                if line in exact:
                    continue
                i += 1
                obj = gen_obj(line, i, verbose)
                objs.append(obj) 
                if i >= 10:
                    break
        return JsonResponse({'ret': 'ok', 'num': len(objs), 'objs': objs})



