from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from accounts.permissions import is_platform_admin

from .forms import (
    SchoolRegistrationForm,
    SchoolSubscriptionForm,
)
from .models import School, SchoolSubscription, SubscriptionPackage


@login_required
def platform_dashboard(request):
    """
    Main dashboard for Paul SchoolHub platform administrators.

    Platform administrators manage the entire SchoolHub platform,
    including schools, packages, features, and subscriptions.
    """

    if not is_platform_admin(request.user):
        messages.error(
            request,
            "You do not have permission to access the platform administration area."
        )
        return redirect("dashboard_home")

    context = {
        "schools": School.objects.select_related(
            "subscription",
            "subscription__package",
        ).order_by("name"),

        "schools_count": School.objects.count(),

        "active_schools_count": School.objects.filter(
            is_active=True
        ).count(),

        "inactive_schools_count": School.objects.filter(
            is_active=False
        ).count(),

        "packages_count": SubscriptionPackage.objects.filter(
            is_active=True
        ).count(),

        "subscriptions_count": SchoolSubscription.objects.filter(
            is_active=True
        ).count(),

        "basic_schools_count": SchoolSubscription.objects.filter(
            is_active=True,
            package__name=SubscriptionPackage.PackageType.BASIC,
        ).count(),

        "standard_schools_count": SchoolSubscription.objects.filter(
            is_active=True,
            package__name=SubscriptionPackage.PackageType.STANDARD,
        ).count(),

        "premium_schools_count": SchoolSubscription.objects.filter(
            is_active=True,
            package__name=SubscriptionPackage.PackageType.PREMIUM,
        ).count(),
    }

    return render(
        request,
        "schools/platform_dashboard.html",
        context,
    )

@login_required
def create_school(request):
    """
    Register a new school together with its first administrator
    and subscription.
    """

    if not is_platform_admin(request.user):
        messages.error(
            request,
            "You do not have permission to register schools."
        )
        return redirect("dashboard_home")

    if request.method == "POST":
        form = SchoolRegistrationForm(request.POST)

        if form.is_valid():

            User = get_user_model()

            try:
                with transaction.atomic():

                    # -------------------------------------------------
                    # CREATE SCHOOL
                    # -------------------------------------------------

                    school = School.objects.create(
                        name=form.cleaned_data["school_name"].strip(),
                        code=form.cleaned_data["school_code"],
                        email=form.cleaned_data["email"],
                        phone=form.cleaned_data["phone"].strip(),
                        address=form.cleaned_data["address"].strip(),
                    )

                    # -------------------------------------------------
                    # CREATE SUBSCRIPTION
                    # -------------------------------------------------

                    SchoolSubscription.objects.create(
                        school=school,
                        package=form.cleaned_data["package"],
                        billing_cycle=form.cleaned_data["billing_cycle"],
                        start_date=timezone.now().date(),
                        is_active=True,
                    )

                    # -------------------------------------------------
                    # CREATE SCHOOL ADMINISTRATOR
                    # -------------------------------------------------

                    administrator = User.objects.create_user(
                        username=form.cleaned_data["admin_username"],
                        email=form.cleaned_data["admin_email"],
                        password=form.cleaned_data["admin_password"],
                        first_name=form.cleaned_data["admin_first_name"],
                        last_name=form.cleaned_data["admin_last_name"],
                        role=User.Role.ADMIN,
                        school=school,
                    )

                messages.success(
                    request,
                    f"{school.name} was registered successfully."
                )

                return redirect("platform_dashboard")

            except Exception:
                messages.error(
                    request,
                    "The school could not be registered. "
                    "Please try again."
                )

    else:
        form = SchoolRegistrationForm()

    return render(
        request,
        "schools/school_create.html",
        {
            "form": form,
        },
    )


@login_required
def edit_subscription(request, school_id):
    """
    Allow Platform Administrators to change an existing
    school's subscription package and billing cycle.
    """

    if not is_platform_admin(request.user):
        messages.error(
            request,
            "You do not have permission to manage subscriptions."
        )
        return redirect("dashboard_home")

    school = get_object_or_404(
        School,
        id=school_id,
    )

    subscription = school.subscription

    if request.method == "POST":
        form = SchoolSubscriptionForm(
            request.POST,
            instance=subscription,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f"{school.name}'s subscription was updated successfully."
            )

            return redirect(
                "platform_dashboard"
            )

    else:
        form = SchoolSubscriptionForm(
            instance=subscription,
        )

    return render(
        request,
        "schools/edit_subscription.html",
        {
            "school": school,
            "subscription": subscription,
            "form": form,
        },
    )
