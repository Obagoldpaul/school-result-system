from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from students.models import SchoolClass
from .forms import TeacherRegistrationForm
from .models import Teacher
from accounts.decorators import staff_required, management_required

@management_required
@login_required
def register_teacher(request):

    if request.method == "POST":

        form = TeacherRegistrationForm(
            request.POST,
            request.FILES,
            user=request.user,
        )

        if form.is_valid():

            form.save(
                user=request.user
            )

            return redirect(
                "teacher_list"
            )

    else:

        form = TeacherRegistrationForm(user=request.user,)


    return render(
        request,
        "teachers/register_teacher.html",
        {
            "form": form,
        },
    )




@staff_required
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
        }
    )
    
@staff_required
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