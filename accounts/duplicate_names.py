from django.db.models.functions import Lower, Trim

from accounts.models import User
from registrations.models import RegistrationApplication


def find_possible_duplicate_names(
    school,
    first_name,
    last_name,
    exclude_user=None,
    exclude_application=None,
):
    """
    Find possible duplicate people within one school.

    Matches first name and last name together, ignoring case
    and leading/trailing whitespace.

    Returns existing users and pending applications separately.
    This is advisory only; it does not block registration.
    """

    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()

    if not school or not first_name or not last_name:
        return {
            "users": [],
            "applications": [],
        }

    users = (
        User.objects
        .filter(school=school)
        .annotate(
            normalized_first_name=Lower(Trim("first_name")),
            normalized_last_name=Lower(Trim("last_name")),
        )
        .filter(
            normalized_first_name=first_name.lower(),
            normalized_last_name=last_name.lower(),
        )
    )

    if exclude_user and exclude_user.pk:
        users = users.exclude(pk=exclude_user.pk)

    applications = (
        RegistrationApplication.objects
        .filter(
            school=school,
            status=RegistrationApplication.Status.PENDING,
        )
        .annotate(
            normalized_first_name=Lower(Trim("first_name")),
            normalized_last_name=Lower(Trim("last_name")),
        )
        .filter(
            normalized_first_name=first_name.lower(),
            normalized_last_name=last_name.lower(),
        )
    )

    if exclude_application and exclude_application.pk:
        applications = applications.exclude(
            pk=exclude_application.pk
        )

    return {
        "users": list(
            users.values(
                "id",
                "username",
                "first_name",
                "last_name",
            )
        ),
        "applications": list(
            applications.values(
                "id",
                "role",
                "first_name",
                "last_name",
            )
        ),
    }