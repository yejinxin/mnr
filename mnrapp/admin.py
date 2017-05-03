from django.contrib import admin

# Register your models here.
from .models import Application, RootModification, DiskModification, CpuMemModification

#class ModificationInline(admin.StackedInline):
class ModificationInline(admin.TabularInline):
    fields = ('host', 'prod_ip', 'mng_ip', )

class RootModificationInline(ModificationInline):
    fields = ('host', 'prod_ip', 'mng_ip', 'os_type', 'status', 'user', 'password', 'message',)
    model = RootModification
    extra = 0
    readonly_fields = ('type', 'message',)

class DiskModificationInline(ModificationInline):
    fields = ('host', 'prod_ip', 'mng_ip', 'os_type', 'status', 'fs', 'size', 'message',)
    model = DiskModification
    extra = 0
    readonly_fields = ('type', 'message',)

class CpuMemModificationInline(ModificationInline):
    fields = ('host', 'prod_ip', 'mng_ip', 'os_type', 'status', 'cpu_ori', 'cpu_new', 'mem_ori', 'mem_new', 'message',)
    model = CpuMemModification
    extra = 0
    readonly_fields = ('type', 'message',)

class ApplicationAdmin(admin.ModelAdmin):
    fields = ('applicant', 'type', 'apply_name', 'apply_desp', 'status', 'recoverable', 'autorecover', 'apply_time', 'expire_time',)
    #readonly_fields = ('apply_time', 'type')
    readonly_fields = ('apply_time', )
    list_display = ( 'id', 'applicant', 'type', 'apply_time', 'apply_name', 'status', 'mods_num', )
    list_filter = ('applicant', 'type', 'status',)
    search_fields = ('id', 'apply_name')
    inlines = ( RootModificationInline, DiskModificationInline, CpuMemModificationInline)
    list_per_page = 10
    #date_hierarchy = ('apply_time')

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super(ApplicationAdmin, self).get_search_results(request, queryset, search_term)
        try:
            search_term_as_int = int(search_term)
        except ValueError:
            pass
        else:
            #queryset |= self.model.objects.filter(pk=search_term_as_int)
            queryset = self.model.objects.filter(pk=search_term_as_int)
        return queryset, use_distinct 

    def get_inline_instances(self, request, obj=None):
        if obj:
            if obj.type == 'ROOT':
                return [RootModificationInline(self.model, self.admin_site)]
            elif obj.type == 'DISK':
                return [DiskModificationInline(self.model, self.admin_site)]
            elif obj.type == 'CPUMEM':
                return [CpuMemModificationInline(self.model, self.admin_site)]
        return [inline(self.model, self.admin_site) for inline in self.inlines]

admin.site.register(Application, ApplicationAdmin)
#admin.site.register(Modification)
