
from datetime import timedelta
from django.utils import timezone

from dateutil.relativedelta import relativedelta

from .models import SchoolSubscription


def get_school_subscription(school):
    """
    Return the school's active subscription record.

    This function does not determine whether the subscription
    has expired. Expiry is handled separately using end_date.
    """

    if not school:
        return None

    try:
        subscription = school.subscription
    except SchoolSubscription.DoesNotExist:
        return None

    return subscription


def is_subscription_expired(subscription):
    """
    Determine whether a subscription has expired.

    The subscription is considered expired when its end_date
    is before today's date.

    A missing end_date is not treated as expired here because
    the subscription record may still be incomplete.
    """

    if not subscription:
        return False

    if not subscription.end_date:
        return False

    from django.utils import timezone

    return subscription.end_date < timezone.now().date()


def is_subscription_expiring_soon(subscription, days=30):
    """
    Determine whether a subscription will expire within the
    specified number of days.

    Expired subscriptions are never considered 'expiring soon'.
    """

    if not subscription:
        return False

    if not subscription.end_date:
        return False

    from django.utils import timezone

    today = timezone.now().date()

    if subscription.end_date < today:
        return False

    return subscription.end_date <= today + timedelta(days=days)


def get_subscription_status(subscription):
    """
    Return the subscription status used by the platform dashboard.

    Possible values:

        ACTIVE
        EXPIRING_SOON
        EXPIRED
    """

    if not subscription:
        return "EXPIRED"

    if is_subscription_expired(subscription):
        return "EXPIRED"

    if is_subscription_expiring_soon(subscription):
        return "EXPIRING_SOON"

    return "ACTIVE"


def school_has_active_subscription(school):
    """
    Return True when the school has a subscription that has not expired.

    Platform-level access is handled separately.
    """

    subscription = get_school_subscription(school)

    if not subscription:
        return False

    return (
        subscription.is_active
        and not is_subscription_expired(subscription)
    )


def school_has_feature(school, feature_code):
    """
    Check whether a school has access to a particular feature
    through its subscription package.

    The subscription must be active and must not have expired.
    """

    subscription = get_school_subscription(school)

    if not subscription:
        return False

    if not subscription.is_active:
        return False

    if is_subscription_expired(subscription):
        return False

    return subscription.package.features.filter(
        code=feature_code,
        is_active=True,
    ).exists()


def calculate_subscription_end_date(start_date, billing_cycle):
    """
    Calculate a school's subscription end date.

    Termly:
        Start Date + 3 calendar months + 14 days

    Yearly:
        Start Date + 1 calendar year
    """

    if billing_cycle == SchoolSubscription.BillingCycle.TERMLY:
        return (
            start_date
            + relativedelta(months=3)
            + timedelta(days=14)
        )

    if billing_cycle == SchoolSubscription.BillingCycle.YEARLY:
        return start_date + relativedelta(years=1)

    return None
