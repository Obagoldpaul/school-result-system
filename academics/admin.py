from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, reverse

from .models import AcademicSession, Term, SchoolSettings


admin.site.register(AcademicSession)
admin.site.register(Term)


@admin.register(SchoolSettings)
class SchoolSettingsAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return True

    def changelist_view(self, request, extra_context=None):

        school = getattr(
            request.user,
            "school",
            None
        )

        if school is None:
            return super().changelist_view(
                request,
                extra_context
            )

        settings = SchoolSettings.objects.filter(
            school=school
        ).first()

        if settings:
            return HttpResponseRedirect(
                reverse(
                    "admin:academics_schoolsettings_change",
                    args=[settings.pk]
                )
            )

        return super().changelist_view(
            request,
            extra_context
        )