from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def help_home(request):
    return render(
        request,
        "help_center/home.html",
    )


@login_required
def about(request):
    return render(
        request,
        "help_center/about.html",
    )
    
@login_required
def getting_started(request):
    return render(
        request,
        "help_center/getting_started.html",
    )

@login_required
def school_administration(request):
    return render(
        request,
        "help_center/school_administration.html",
    )
    
@login_required
def teaching_academics(request):
    return render(
        request,
        "help_center/teaching_academics.html",
    )
    
@login_required
def fees_payments(request):
    return render(
        request,
        "help_center/fees_payments.html",
    )
    
@login_required
def student_parent_portal(request):
    return render(
        request,
        "help_center/student_parent_portal.html",
    )