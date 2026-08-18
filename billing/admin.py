from django.contrib import admin
from .models import (
    FeeCategory,
    FeeAssignment,
    Payment,
    OpeningBalance,
)


admin.site.register(FeeCategory)
admin.site.register(FeeAssignment)
admin.site.register(Payment)
admin.site.register(OpeningBalance)