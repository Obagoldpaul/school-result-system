from .utils import get_school_from_host


class SchoolDomainMiddleware:
    """
    Resolve the school associated with the incoming hostname.

    The resolved school is attached to request.school.
    Unknown or platform hosts leave request.school as None.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.school = get_school_from_host(request.get_host())

        return self.get_response(request)