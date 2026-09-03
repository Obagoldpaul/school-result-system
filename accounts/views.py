from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from schools.models import School, PlatformSettings
from academics.models import SchoolSettings

from .permissions import is_platform_admin
from .utils import school_subscription_access_allowed
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse_lazy

from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import (
    LoginView,
    PasswordResetView,
    PasswordResetConfirmView,
)


class SchoolHubLoginView(LoginView):
    """
    Custom login view for Paul SchoolHub school users.

    School domains automatically identify the school.

    Direct school login using ?school=CODE remains supported when
    no school domain has been resolved.
    """

    template_name = "registration/login.html"

    def dispatch(self, request, *args, **kwargs):

        if request.user.is_authenticated:

            from django.contrib.auth import logout

            logout(request)

        return super().dispatch(request, *args, **kwargs)

    def get_school(self):
        """
        Determine the school for this login request.

        A resolved school domain is authoritative and takes priority
        over any ?school=CODE parameter.

        If no school domain is resolved, the existing ?school=CODE
        mechanism remains available.
        """

        # ---------------------------------------------------------
        # SCHOOL DOMAIN
        # ---------------------------------------------------------

        domain_school = getattr(self.request, "school", None)

        if domain_school:
            return domain_school

        # ---------------------------------------------------------
        # DIRECT SCHOOL LOGIN
        # ---------------------------------------------------------

        school_code = self.request.GET.get("school")

        if not school_code:
            school_code = self.request.POST.get("school")

        if not school_code:
            return None

        return School.objects.filter(
            code__iexact=school_code.strip()
        ).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        school = self.get_school()

        context["login_school"] = school

        if school:
            try:
                context["login_school_settings"] = SchoolSettings.load(
                    school
                )
            except SchoolSettings.DoesNotExist:
                context["login_school_settings"] = None
        else:
            context["login_school_settings"] = None

        return context

    def form_valid(self, form):

        user = form.get_user()

        # ---------------------------------------------------------
        # PLATFORM ADMINISTRATOR
        # ---------------------------------------------------------

        if is_platform_admin(user):
            messages.error(
                self.request,
                "Platform administrators must use the Paul SchoolHub "
                "platform login."
            )
            return self.form_invalid(form)

        # ---------------------------------------------------------
        # SCHOOL USER
        # ---------------------------------------------------------

        school = getattr(user, "school", None)

        if school is None:
            messages.error(
                self.request,
                "Your account is not linked to a school."
            )
            return self.form_invalid(form)

        # ---------------------------------------------------------
        # SCHOOL STATUS
        # ---------------------------------------------------------

        if not school.is_active:
            messages.error(
                self.request,
                "Your school account is currently inactive. "
                "Please contact the platform administrator."
            )
            return self.form_invalid(form)

        # ---------------------------------------------------------
        # SUBSCRIPTION STATUS
        # ---------------------------------------------------------

        if not school_subscription_access_allowed(school):
            messages.error(
                self.request,
                "Your school's subscription has expired or is inactive. "
                "Please contact your school administrator."
            )
            return self.form_invalid(form)

        # ---------------------------------------------------------
        # SCHOOL MATCHING
        # ---------------------------------------------------------

        login_school = self.get_school()

        if login_school and login_school.id != school.id:
            messages.error(
                self.request,
                "This account does not belong to the selected school."
            )
            return self.form_invalid(form)

        return super().form_valid(form)
    
    
@method_decorator(never_cache, name="dispatch")
class PlatformLoginView(LoginView):
    """
    Dedicated login page for Paul SchoolHub platform administrators.

    Only users with the PLATFORM_ADMIN role are allowed to enter
    the platform administration area.
    """

    template_name = "registration/platform_login.html"

    def dispatch(self, request, *args, **kwargs):

        # If already logged in, only allow Platform Administrators
        # to continue to the platform login flow.
        if request.user.is_authenticated:

            if request.user.role == request.user.Role.PLATFORM_ADMIN:
                return redirect("/platform/")

            # School users must log out before using the
            # Platform Administrator login.
            from django.contrib.auth import logout

            logout(request)

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return "/platform/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        platform_settings, created = PlatformSettings.objects.get_or_create(
            pk=1
        )

        context["platform_settings"] = platform_settings

        return context

    def form_valid(self, form):
        user = form.get_user()

        if user.role != user.Role.PLATFORM_ADMIN:
            form.add_error(
                None,
                "This login is for Paul SchoolHub platform administrators only."
            )

            return self.form_invalid(form)

        if not user.is_active:
            form.add_error(
                None,
                "This platform administrator account is inactive."
            )

            return self.form_invalid(form)

        return super().form_valid(form)

class SetPasswordView(PasswordResetConfirmView):
    """
    Secure one-time password setup for newly created users.

    The token is generated with Django's default password-reset
    token generator. Once the user successfully sets a password,
    the token becomes invalid.
    """

    template_name = "registration/set_password.html"
    token_generator = default_token_generator
    success_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # The password-reset confirmation view resolves the user
        # from the secure UID/token before rendering the page.
        school = getattr(self.user, "school", None)

        context["school"] = school

        return context

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            "Your password has been created successfully. "
            "You can now log in.",
        )

        return response

class PlatformPasswordResetForm(PasswordResetForm):
    """
    Password reset form for Paul SchoolHub.

    Reset links always use the platform domain, regardless
    of the school domain from which the request originated.
    """

    def save(self, **kwargs):
        kwargs["domain_override"] = "paulschoolhub.com.ng"
        kwargs["use_https"] = True

        return super().save(**kwargs)

class PasswordResetRequestView(PasswordResetView):
    """
    Start the password-reset process for a user.

    Reset links always use the Paul SchoolHub platform domain,
    regardless of the school domain used to request the reset.
    """

    template_name = "registration/password_reset.html"
    email_template_name = "registration/password_reset_email.txt"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")
    form_class = PlatformPasswordResetForm