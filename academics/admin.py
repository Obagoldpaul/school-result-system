from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, reverse

from .models import AcademicSession, Term, SchoolSettings


admin.site.register(AcademicSession)
admin.site.register(Term)


@admin.register(SchoolSettings)
class SchoolSettingsAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return SchoolSettings.objects.count() == 0

    def changelist_view(self, request, extra_context=None):
        settings = SchoolSettings.load()

        return HttpResponseRedirect(
            reverse(
                "admin:academics_schoolsettings_change",
                args=[settings.pk]
            )
        )