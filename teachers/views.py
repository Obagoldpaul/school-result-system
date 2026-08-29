from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from students.models import SchoolClass
from .forms import TeacherRegistrationForm
from .models import Teacher
from accounts.decorators import staff_required, management_required
from accounts.permissions import school_permission_required
from django.core.mail import send_mail

from core.choices import (
    NIGERIAN_STATES,
    NIGERIAN_LGAS,
    NATIONALITY_CHOICES,
    RELIGION_CHOICES,
)

@management_required
@school_permission_required("teachers.add")
@login_required
def register_teacher(request):

    if request.method == "POST":

        form = TeacherRegistrationForm(
            request.POST,
            request.FILES,
            user=request.user,
        )

        if form.is_valid():

            # Get the plain-text password before it is hashed.
            password = form.cleaned_data["password"]

            # Create the teacher and user account.
            teacher = form.save(
                user=request.user
            )

            # Send login credentials if an email address was provided.
            if teacher.user.email:
                send_mail(
                    subject="Your Paul SchoolHub Login Details",
                    message=(
                        f"Hello {teacher.user.get_full_name()},\n\n"
                        f"Your teacher account has been created on "
                        f"Paul SchoolHub for "
                        f"{request.user.school.name}.\n\n"
                        f"Username: {teacher.user.username}\n"
                        f"Password: {password}\n\n"
                        f"You can now log in to your school portal "
                        f"using these credentials.\n\n"
                        f"Please keep your login details secure.\n\n"
                        f"Regards,\n"
                        f"{request.user.school.name}\n"
                        f"Powered by Paul SchoolHub"
                    ),
                    from_email=None,
                    recipient_list=[teacher.user.email],
                    fail_silently=True,
                )

            return redirect(
                "teacher_list"
            )

    else:

        form = TeacherRegistrationForm(
            user=request.user,
        )

    return render(
        request,
        "teachers/register_teacher.html",
        {
            "form": form,
            "nigerian_lgas": NIGERIAN_LGAS,
        },
    )




@staff_required
@school_permission_required("teachers.view")
@login_required
def teacher_list(request):

    teachers = Teacher.objects.filter(user__school=request.user.school)

    search = request.GET.get("search")
    filter_type = request.GET.get("filter")

    if search:
        teachers = teachers.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(staff_id__icontains=search) |
            Q(phone_number__icontains=search)
        )

    if filter_type == "class":
        teachers = teachers.filter(
            is_class_teacher=True
        )

    elif filter_type == "assigned":
        teachers = teachers.exclude(
            assigned_class__isnull=True
        )

    elif filter_type == "inactive":
        teachers = teachers.filter(
            is_active=False
        )

    context = {

        "teachers": teachers,

        "search": search or "",

        "filter": filter_type or "",

        "total_teachers": teachers.count(),

        "class_teacher_count":
            teachers.filter(
                is_class_teacher=True
            ).count(),

        "assigned_count":
            teachers.exclude(
                assigned_class__isnull=True
            ).count(),

        "inactive_count":
            teachers.filter(
                is_active=False
            ).count(),
    }

    return render(
        request,
        "teachers/teacher_list.html",
        context
    )




@management_required
@school_permission_required("teachers.change")
@login_required
def edit_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id, user__school=request.user.school,)

    if request.method == 'POST':

        # ==========================
        # USER INFORMATION
        # ==========================

        teacher.user.first_name = request.POST.get('first_name', '')
        teacher.user.other_name = request.POST.get('other_name', '')
        teacher.user.last_name = request.POST.get('last_name', '')
        teacher.user.email = request.POST.get('email', '')
        teacher.user.save()

        # ==========================
        # PERSONAL INFORMATION
        # ==========================

        teacher.date_of_birth = request.POST.get('date_of_birth') or None
        teacher.gender = request.POST.get('gender', '')
        teacher.phone_number = request.POST.get('phone_number', '')
        teacher.home_address = request.POST.get('home_address', '')
        teacher.state_of_origin = request.POST.get('state_of_origin', '')
        teacher.local_government = request.POST.get('local_government', '')

        # ==========================
        # PROFESSIONAL INFORMATION
        # ==========================

        teacher.staff_id = request.POST.get('staff_id', '')
        teacher.qualification = request.POST.get('qualification', '')
        teacher.years_of_experience = request.POST.get(
            'years_of_experience'
        ) or 0
        teacher.employment_date = request.POST.get('employment_date') or None
        
        # ==========================
        # PAYMENT INFORMATION
        # ==========================

        teacher.bank_name = request.POST.get('bank_name', '')
        teacher.account_name = request.POST.get('account_name', '')
        teacher.account_number = request.POST.get('account_number', '')

        # ==========================
        # SCHOOL RESPONSIBILITY
        # ==========================

        teacher.is_class_teacher = (
            request.POST.get('is_class_teacher') == 'on'
        )

        assigned_class_id = request.POST.get('assigned_class')

        if assigned_class_id:
            assigned_class = get_object_or_404(
                SchoolClass,
                id=assigned_class_id,
                school=request.user.school,
            )

            teacher.assigned_class = assigned_class

        else:
            teacher.assigned_class = None

        teacher.is_active = (
            request.POST.get('is_active') == 'on'
        )

        # ==========================
        # FILE UPLOADS
        # ==========================

        if request.FILES.get('passport'):
            teacher.passport = request.FILES['passport']

        if request.FILES.get('certificate'):
            teacher.certificate = request.FILES['certificate']

        teacher.save()

        return redirect('teacher_list')

    classes = SchoolClass.objects.filter(school=request.user.school)

    return render(
        request,
        'teachers/edit_teacher.html',
        {
            'teacher': teacher,
            'classes': classes,
            'nigerian_states': NIGERIAN_STATES,
            'nigerian_lgas': NIGERIAN_LGAS,
            'nationality_choices': NATIONALITY_CHOICES,
            'religion_choices': RELIGION_CHOICES,
        }
    )
    
@staff_required
@school_permission_required("teachers.view")
@login_required
def teacher_profile(request, teacher_id):

    teacher = get_object_or_404(
        Teacher,
        id=teacher_id,
        user__school=request.user.school,
    )

    return render(
        request,
        "teachers/teacher_profile.html",
        {
            "teacher": teacher,
        },
    )
    
@management_required
@school_permission_required("teachers.change")
@login_required
def deactivate_teacher(request, teacher_id):

    teacher = get_object_or_404(
        Teacher,
        id=teacher_id,
        user__school=request.user.school,
    )

    teacher.is_active = False
    teacher.save()

    return redirect("teacher_list")


@management_required
@school_permission_required("teachers.change")
@login_required
def activate_teacher(request, teacher_id):

    teacher = get_object_or_404(
        Teacher,
        id=teacher_id,
        user__school=request.user.school,
    )

    teacher.is_active = True
    teacher.save()

    return redirect("teacher_list")

@staff_required
@school_permission_required("teachers.view")
@login_required
def print_teacher_profile(request, teacher_id):

    teacher = get_object_or_404(
        Teacher,
        id=teacher_id,
        user__school=request.user.school,
    )

    return render(
        request,
        "teachers/print_teacher_profile.html",
        {
            "teacher": teacher,
        },
    )

@staff_required
@school_permission_required("teachers.view")
@login_required
def teacher_payment_accounts(request):

    teachers = Teacher.objects.filter(
        user__school=request.user.school
    ).select_related("user")

    return render(
        request,
        "teachers/teacher_payment_accounts.html",
        {
            "teachers": teachers,
        },
    )

@staff_required
@school_permission_required("teachers.view")
@login_required
def print_teacher_payment_accounts(request):

    teachers = Teacher.objects.filter(
        user__school=request.user.school
    ).select_related(
        "user"
    ).order_by(
        "staff_id"
    )

    return render(
        request,
        "teachers/print_teacher_payment_accounts.html",
        {
            "teachers": teachers,
        },
    )