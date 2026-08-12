from academics.models import SchoolSettings


def school_settings(request):

    if not request.user.is_authenticated:
        return {
            "school_settings": None
        }

    if not request.user.school:
        return {
            "school_settings": None
        }

    try:
        settings = SchoolSettings.load(
            request.user.school
        )
    except SchoolSettings.DoesNotExist:
        settings = None

    return {
        "school_settings": settings
    }