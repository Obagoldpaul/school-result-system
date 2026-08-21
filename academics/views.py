from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.core.exceptions import PermissionDenied

from accounts.permissions import is_management

from .forms import SchoolSettingsForm
from .models import SchoolSettings


@login_required
def school_settings(request):
    """
    View and edit settings belonging only to the logged-in user's school.
    """

    if not is_management(request.user):
        raise PermissionDenied(
            "Only management can edit school settings."
        )

    if not request.user.school:
        raise PermissionDenied(
            "Your account is not assigned to a school."
        )

    settings, created = SchoolSettings.objects.get_or_create(
        school=request.user.school,
        defaults={
            "school_name": request.user.school.name,
        },
    )

    if request.method == "POST":
        form = SchoolSettingsForm(
            request.POST,
            request.FILES,
            instance=settings,
            school=request.user.school,
        )

        if form.is_valid():
            settings = form.save(commit=False)

            # Never allow the form to change the school.
            settings.school = request.user.school

            settings.save()

            messages.success(
                request,
                "School settings updated successfully.",
            )

            return redirect("school_settings")

    else:
        form = SchoolSettingsForm(
            instance=settings,
            school=request.user.school,
        )

    return render(
        request,
        "academics/school_settings.html",
        {
            "form": form,
            "school_settings": settings,
        },
    )