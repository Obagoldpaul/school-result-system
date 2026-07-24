from django.contrib import admin
from .models import Department, SchoolClass, Student

admin.site.register(Department)
admin.site.register(SchoolClass)
admin.site.register(Student)