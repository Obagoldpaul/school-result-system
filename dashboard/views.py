from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .services import build_dashboard


@login_required
def home(request):
    context = build_dashboard(request.user)
    return render(request, "dashboard/home.html", context)