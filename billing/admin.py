from django.contrib import admin
from .models import FeeStructure, Payment, OpeningBalance

admin.site.register(FeeStructure)
admin.site.register(Payment)
admin.site.register(OpeningBalance)