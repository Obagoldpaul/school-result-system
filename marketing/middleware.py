from django.conf import settings


class MarketingDomainMiddleware:
    """
    Route the public Paul SchoolHub website through
    its dedicated URL configuration.
    """

    MARKETING_HOST = "www.paulschoolhub.com.ng"
    LOCAL_MARKETING_HOST = "marketing.localhost"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        hostname = request.get_host().split(":")[0].lower().rstrip(".")

        is_marketing_domain = (
            hostname == self.MARKETING_HOST
            or (
                settings.DEBUG
                and hostname == self.LOCAL_MARKETING_HOST
            )
        )

        if is_marketing_domain:
            request.urlconf = "config.marketing_urls"

        return self.get_response(request)