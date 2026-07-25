from django.contrib import admin
from .models import AcademicSession, Term

admin.site.register(AcademicSession)
admin.site.register(Term)