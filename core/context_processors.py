from academics.models import SchoolSettings


def school_settings(request):
    return {
        "school_settings": SchoolSettings.load()
    }