from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.core.exceptions import PermissionDenied

from accounts.permissions import school_permission_required

from .forms import SchoolSettingsForm
from .models import SchoolSettings


@login_required
@school_permission_required("school_settings.manage")
def school_settings(request):
    """
    View and edit settings belonging only to the logged-in user's school.
    """

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

            # -------------------------------------------------
            # KEEP BASIC SCHOOL INFORMATION IN SCHOOL MODEL
            # -------------------------------------------------

            school = request.user.school

            school.name = form.cleaned_data["school_name"]
            school.address = form.cleaned_data["school_address"]
            school.phone = form.cleaned_data["school_phone"]
            school.email = form.cleaned_data["school_email"]

            if "school_logo" in form.cleaned_data:
                uploaded_logo = form.cleaned_data["school_logo"]

                if uploaded_logo:
                    school.logo = uploaded_logo

            school.save()

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