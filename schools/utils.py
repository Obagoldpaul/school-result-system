from .models import School


def get_school_subscription(school):
    """
    Return the school's active subscription.
    Returns None if the school has no active subscription.
    """

    if not school:
        return None

    try:
        subscription = school.subscription
    except School.subscription.RelatedObjectDoesNotExist:
        return None

    if not subscription.is_active:
        return None

    return subscription


def school_has_feature(school, feature_code):
    """
    Check whether a school has access to a particular feature
    through its subscription package.
    """

    subscription = get_school_subscription(school)

    if not subscription:
        return False

    return subscription.package.features.filter(
        code=feature_code,
        is_active=True
    ).exists()