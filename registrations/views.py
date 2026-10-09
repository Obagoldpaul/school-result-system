from django.shortcuts import render

from core.choices import NIGERIAN_LGAS

from .forms import (
    StudentRegistrationApplicationForm,
    TeacherRegistrationApplicationForm,
)

from django.contrib.auth.decorators import login_required

from accounts.permissions import school_permission_required

from .models import RegistrationApplication


from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse

from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from students.models import Student
from students.forms import generate_admission_number
from teachers.models import Teacher
from teachers.forms import generate_staff_id


def send_password_setup_email(request, user, school, account_type):
    if not user.email:
        return

    token = default_token_generator.make_token(user)

    uid = urlsafe_base64_encode(
        force_bytes(user.pk)
    )

    setup_url = request.build_absolute_uri(
        reverse(
            "set_password",
            kwargs={
                "uidb64": uid,
                "token": token,
            },
        )
    )

    send_mail(
        subject="Set Up Your Paul SchoolHub Password",
        message=(
            f"Hello {user.get_full_name()},\n\n"
            f"Your {account_type} account has been created on "
            f"Paul SchoolHub for {school.name}.\n\n"
            f"Username: {user.username}\n\n"
            f"Set your password using this link:\n\n"
            f"{setup_url}\n\n"
            f"This link is valid for 72 hours and can only be "
            f"used once.\n\n"
            f"If you did not expect this email, please contact "
            f"{school.name}.\n\n"
            f"Regards,\n"
            f"{school.name}\n"
            f"Powered by Paul SchoolHub"
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )


def student_registration(request):
    school = getattr(request, "school", None)

    if school is None:
        return render(
            request,
            "registrations/registration_unavailable.html",
            status=404,
        )

    if not school.settings.student_registration_enabled:
        return render(
            request,
            "registrations/registration_unavailable.html",
            {"school": school},
            status=403,
        )

    if request.method == "POST":
        form = StudentRegistrationApplicationForm(
            request.POST,
            request.FILES,
            school=school,
        )

        if form.is_valid():
            form.save()

            return render(
                request,
                "registrations/student_registration_success.html",
                {"school": school},
            )
    else:
        form = StudentRegistrationApplicationForm(
            school=school,
        )

    return render(
        request,
        "registrations/student_registration.html",
        {
            "form": form,
            "school": school,
            "nigerian_lgas": NIGERIAN_LGAS,
        },
    )
    
def teacher_registration(request):
    school = getattr(request, "school", None)

    if school is None:
        return render(
            request,
            "registrations/registration_unavailable.html",
            status=404,
        )

    if not school.settings.teacher_registration_enabled:
        return render(
            request,
            "registrations/registration_unavailable.html",
            {"school": school},
            status=403,
        )

    if request.method == "POST":
        form = TeacherRegistrationApplicationForm(
            request.POST,
            request.FILES,
            school=school,
        )

        if form.is_valid():
            form.save()

            return render(
                request,
                "registrations/teacher_registration_success.html",
                {"school": school},
            )
    else:
        form = TeacherRegistrationApplicationForm(
            school=school,
        )

    return render(
        request,
        "registrations/teacher_registration.html",
        {
            "form": form,
            "school": school,
            "nigerian_lgas": NIGERIAN_LGAS,
        },
    )

@school_permission_required("registrations.view")
@login_required
def registration_application_list(request):
    applications = RegistrationApplication.objects.filter(
        school=request.user.school,
    ).select_related(
        "requested_class",
        "requested_department",
        "reviewed_by",
    ).order_by("-submitted_at")

    return render(
        request,
        "registrations/registration_application_list.html",
        {
            "applications": applications,
        },
    )
    
@school_permission_required("registrations.view")
@login_required
def registration_application_detail(request, application_id):
    application = (
        RegistrationApplication.objects
        .select_related(
            "requested_class",
            "requested_department",
            "reviewed_by",
        )
        .get(
            id=application_id,
            school=request.user.school,
        )
    )

    return render(
        request,
        "registrations/registration_application_detail.html",
        {
            "application": application,
        },
    )
    

@school_permission_required("registrations.review")
@login_required
def approve_registration_application(request, application_id):
    if request.method != "POST":
        return redirect("registration_application_detail", application_id)

    application = get_object_or_404(
        RegistrationApplication,
        id=application_id,
        school=request.user.school,
    )

    if application.status != RegistrationApplication.Status.PENDING:
        return redirect(
            "registration_application_detail",
            application_id,
        )

    if User.objects.filter(
        username=application.username,
    ).exists():
        return redirect(
            "registration_application_detail",
            application_id,
        )

    with transaction.atomic():

        user = User.objects.create(
            username=application.username,
            first_name=application.first_name,
            other_name=application.other_name,
            last_name=application.last_name,
            email=application.email,
            phone_number=application.phone_number,
            school=application.school,
            role=(
                User.Role.STUDENT
                if application.role == RegistrationApplication.Role.STUDENT
                else User.Role.TEACHER
            ),
        )

        user.set_unusable_password()
        user.save(update_fields=["password"])

        if application.role == RegistrationApplication.Role.STUDENT:

            student = Student.objects.create(
                user=user,
                school_class=application.requested_class,
                department=application.requested_department,
                admission_number=generate_admission_number(
                    application.school
                ),
                date_of_birth=application.date_of_birth,
                gender=application.gender,
                state_of_origin=application.state_of_origin,
                local_government=application.local_government,
                nationality=application.nationality,
                religion=application.religion,
                home_address=application.home_address,
                blood_group=application.blood_group,
                genotype=application.genotype,
                guardian_name=application.guardian_name,
                guardian_relationship=application.guardian_relationship,
                guardian_phone=application.guardian_phone,
                guardian_email=application.guardian_email,
                medical_condition=application.medical_condition,
                previous_school=application.previous_school,
                admission_status="ACTIVE",
                is_active=True,
            )

            if application.passport:
                student.passport.save(
                    application.passport.name.split("/")[-1],
                    application.passport.file,
                    save=True,
                )

            if student.department_id:
                default_electives = (
                    student.department.default_electives.filter(
                        school=student.user.school,
                        is_elective=True,
                        is_active=True,
                        classsubject__school_class=student.school_class,
                    )
                    .distinct()
                )

                student.elective_subjects.set(default_electives)

            account_type = "student"

        else:

            teacher = Teacher.objects.create(
                user=user,
                staff_id=generate_staff_id(application.school),
                date_of_birth=application.date_of_birth,
                gender=application.gender,
                phone_number=application.phone_number,
                home_address=application.home_address,
                state_of_origin=application.state_of_origin,
                local_government=application.local_government,
                nationality=application.nationality,
                religion=application.religion,
                qualification=application.qualification,
                years_of_experience=application.years_of_experience,
                bank_name=application.bank_name,
                account_name=application.account_name,
                account_number=application.account_number,
                is_class_teacher=False,
                is_active=True,
            )

            if application.passport:
                teacher.passport.save(
                    application.passport.name.split("/")[-1],
                    application.passport.file,
                    save=True,
                )

            if application.certificate:
                teacher.certificate.save(
                    application.certificate.name.split("/")[-1],
                    application.certificate.file,
                    save=True,
                )

            account_type = "teacher"

        application.status = RegistrationApplication.Status.APPROVED
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
            ]
        )

        send_password_setup_email(
            request=request,
            user=user,
            school=application.school,
            account_type=account_type,
        )

    return redirect(
        "registration_application_detail",
        application_id,
    )
    
@school_permission_required("registrations.review")
@login_required
def reject_registration_application(request, application_id):
    if request.method != "POST":
        return redirect(
            "registration_application_detail",
            application_id,
        )

    application = get_object_or_404(
        RegistrationApplication,
        id=application_id,
        school=request.user.school,
    )

    if application.status != RegistrationApplication.Status.PENDING:
        return redirect(
            "registration_application_detail",
            application_id,
        )

    rejection_reason = request.POST.get(
        "rejection_reason",
        "",
    ).strip()

    if not rejection_reason:
        return redirect(
            "registration_application_detail",
            application_id,
        )

    application.status = RegistrationApplication.Status.REJECTED
    application.reviewed_by = request.user
    application.reviewed_at = timezone.now()
    application.rejection_reason = rejection_reason

    application.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
        ]
    )

    return redirect(
        "registration_application_detail",
        application_id,
    )