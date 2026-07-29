from django.contrib import admin
from .models import AcademicSession, Term, SchoolSettings

admin.site.register(AcademicSession)
admin.site.register(Term)
admin.site.register(SchoolSettings)