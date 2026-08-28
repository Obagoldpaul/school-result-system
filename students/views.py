from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import StudentRegistrationForm, SchoolClassForm
from .models import Student, SchoolClass, Department
from accounts.decorators import staff_required, management_required
from accounts.permissions import school_permission_required
from django.db import models
from subjects.models import Subject
from django.core.mail import send_mail

@school_permission_required("students.add")
@login_required
def register_student(request):
    if request.method == "POST":
        form = StudentRegistrationForm(
            request.POST,
            request.FILES,
            user=request.user,
        )

        if form.is_valid():
            password = form.cleaned_data["password"]

            student = form.save()

            if student.user.email:
                send_mail(
                    subject="Your Paul SchoolHub Login Details",
                    message=(
                        f"Hello {student.user.get_full_name()},\n\n"
                        f"Your student account has been created on "
                        f"Paul SchoolHub for {request.user.school.name}.\n\n"
                        f"Username: {student.user.username}\n"
                        f"Password: {password}\n\n"
                        f"You can now log in to your school portal using "
                        f"these credentials.\n\n"
                        f"Please keep your login details secure.\n\n"
                        f"Regards,\n"
                        f"{request.user.school.name}\n"
                        f"Powered by Paul SchoolHub"
                    ),
                    from_email=None,
                    recipient_list=[student.user.email],
                    fail_silently=True,
                )

            return redirect("student_list")

    else:
        form = StudentRegistrationForm(
            user=request.user,
        )

    print(form)
    print(form["lin"])

    return render(
        request,
        "students/register_student.html",
        {
            "form": form,
            "student_list_url": "/students/",
        },
    )

@school_permission_required("students.view")
@login_required
def student_list(request):

    status = request.GET.get("status", "ACTIVE")

    students = Student.objects.filter(
        user__school=request.user.school,
        admission_status=status
    ).select_related(
        "user",
        "school_class",
        "department"
    )

    class_id = request.GET.get("class")

    if class_id:
        students = students.filter(
            school_class_id=class_id
        )

    search = request.GET.get("search", "")

    if search:
        students = students.filter(
            models.Q(user__first_name__icontains=search) |
            models.Q(user__last_name__icontains=search) |
            models.Q(admission_number__icontains=search) |
            models.Q(lin__icontains=search)
        )

    classes = SchoolClass.objects.filter(
        school=request.user.school
    )

    section_order = [
        SchoolClass.Section.PRE_PRIMARY,
        SchoolClass.Section.PRIMARY,
        SchoolClass.Section.JUNIOR_SECONDARY,
        SchoolClass.Section.SENIOR_SECONDARY,
    ]

    section_labels = dict(
        SchoolClass.Section.choices
    )

    grouped_classes = []

    for section in section_order:

        section_classes = classes.filter(
            section=section
        ).order_by("name")

        if section_classes.exists():

            grouped_classes.append({
                "label": section_labels[section],
                "classes": section_classes,
            })

    status_choices = Student._meta.get_field(
        "admission_status"
    ).choices

    return render(
        request,
        "students/student_list.html",
        {
            "students": students,
            "classes": classes,
            "grouped_classes": grouped_classes,
            "selected_class": int(class_id) if class_id else None,
            "search": search,
            "selected_status": status,
            "status_choices": status_choices,
        },
    )
    
@school_permission_required("classes.view")
@login_required
def class_management(request):

    classes = (
        SchoolClass.objects
        .filter(
            school=request.user.school
        )
        .annotate(
            student_count=models.Count(
                "student"
            )
        )
        .order_by(
            "section",
            "name",
        )
    )

    sections = [
        (
            SchoolClass.Section.PRE_PRIMARY,
            "Pre-Primary",
        ),
        (
            SchoolClass.Section.PRIMARY,
            "Primary",
        ),
        (
            SchoolClass.Section.JUNIOR_SECONDARY,
            "Junior Secondary",
        ),
        (
            SchoolClass.Section.SENIOR_SECONDARY,
            "Senior Secondary",
        ),
    ]

    section_classes = []

    for section_value, section_label in sections:

        section_class_list = [
            school_class
            for school_class in classes
            if school_class.section == section_value
        ]

        section_classes.append({
            "value": section_value,
            "label": section_label,
            "classes": section_class_list,
        })

    return render(
        request,
        "students/class_management.html",
        {
            "section_classes": section_classes,
            "class_count": classes.count(),
        },
    )
    
@school_permission_required("classes.manage")
@login_required
def add_class(request):
    if request.method == "POST":
        form = SchoolClassForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():
            school_class = form.save(commit=False)
            school_class.school = request.user.school
            school_class.save()

            messages.success(
                request,
                f"{school_class.name} was created successfully."
            )

            return redirect("class_management")

    else:
        form = SchoolClassForm(user=request.user)

    return render(
        request,
        "students/class_form.html",
        {
            "form": form,
            "page_title": "Add Class",
        }
    )


@school_permission_required("classes.manage")
@login_required
def edit_class(request, class_id):
    school_class = get_object_or_404(
        SchoolClass,
        id=class_id,
        school=request.user.school
    )

    if request.method == "POST":
        form = SchoolClassForm(
            request.POST,
            instance=school_class,
            user=request.user
        )

        if form.is_valid():
            school_class = form.save()

            messages.success(
                request,
                f"{school_class.name} was updated successfully."
            )

            return redirect("class_management")

    else:
        form = SchoolClassForm(
            instance=school_class,
            user=request.user
        )

    return render(
        request,
        "students/class_form.html",
        {
            "form": form,
            "page_title": "Edit Class",
            "school_class": school_class,
        }
    )

@school_permission_required("students.change")
@login_required
def edit_student(request, student_id):
    student = get_object_or_404(
        Student,
        id=student_id,
        user__school=request.user.school,
    )

    if request.method == 'POST':

        # -------------------------
        # USER INFORMATION
        # -------------------------

        student.user.first_name = request.POST.get('first_name', '').strip()
        student.user.other_name = request.POST.get('other_name', '').strip()
        student.user.last_name = request.POST.get('last_name', '').strip()
        student.user.email = request.POST.get('email', '').strip()
        student.user.phone_number = request.POST.get('phone_number', '').strip()

        student.user.save()

        # -------------------------
        # ACADEMIC INFORMATION
        # -------------------------

        school_class_id = request.POST.get('school_class')

        school_class = get_object_or_404(
            SchoolClass,
            id=school_class_id,
            school=request.user.school,
        )

        student.school_class = school_class

        department_id = request.POST.get('department')

        if department_id:
            department = get_object_or_404(
                Department,
                id=department_id,
                school=request.user.school,
            )
            student.department = department
        else:
            student.department = None

        student.admission_number = request.POST.get(
            'admission_number', ''
        ).strip()

        student.lin = request.POST.get('lin', '').strip() or None

        # -------------------------
        # PERSONAL INFORMATION
        # -------------------------

        student.date_of_birth = (
            request.POST.get('date_of_birth')
            or None
        )

        student.gender = request.POST.get('gender', '')

        student.state_of_origin = request.POST.get(
            'state_of_origin', ''
        ).strip()

        student.local_government = request.POST.get(
            'local_government', ''
        ).strip()

        student.nationality = request.POST.get(
            'nationality', 'Nigerian'
        ).strip()

        student.religion = request.POST.get(
            'religion', ''
        ).strip()

        student.home_address = request.POST.get(
            'home_address', ''
        ).strip()

        # -------------------------
        # HEALTH INFORMATION
        # -------------------------

        student.blood_group = request.POST.get(
            'blood_group', ''
        )

        student.genotype = request.POST.get(
            'genotype', ''
        ).strip()

        student.medical_condition = request.POST.get(
            'medical_condition', ''
        ).strip()

        # -------------------------
        # GUARDIAN INFORMATION
        # -------------------------

        student.guardian_name = request.POST.get(
            'guardian_name', ''
        ).strip()

        student.guardian_relationship = request.POST.get(
            'guardian_relationship', ''
        ).strip()

        student.guardian_phone = request.POST.get(
            'guardian_phone', ''
        ).strip()

        student.guardian_email = request.POST.get(
            'guardian_email', ''
        ).strip()

        # -------------------------
        # EMERGENCY CONTACT
        # -------------------------

        student.emergency_contact_name = request.POST.get(
            'emergency_contact_name', ''
        ).strip()

        student.emergency_contact_phone = request.POST.get(
            'emergency_contact_phone', ''
        ).strip()

        # -------------------------
        # ADMISSION INFORMATION
        # -------------------------

        student.admission_date = (
            request.POST.get('admission_date')
            or None
        )

        student.previous_school = request.POST.get(
            'previous_school', ''
        ).strip()

        student.admission_status = request.POST.get(
            'admission_status',
            'ACTIVE'
        )

        student.is_active = (
            request.POST.get('is_active') == 'on'
        )

        # -------------------------
        # PASSPORT
        # -------------------------

        if request.FILES.get('passport'):
            student.passport = request.FILES['passport']

        student.save()

        # -------------------------
        # ELECTIVE SUBJECTS
        # -------------------------

        elective_ids = request.POST.getlist('electives')

        valid_electives = Subject.objects.filter(
            id__in=elective_ids,
            school=request.user.school,
            is_elective=True,
            is_active=True,
        )

        student.elective_subjects.set(valid_electives)

        return redirect('student_list')


    classes = SchoolClass.objects.filter(
        school=request.user.school
    )

    departments = Department.objects.filter(
        school=request.user.school
    )
    electives = Subject.objects.filter(
        school=request.user.school,
        is_elective=True,
        is_active=True,
    )

    return render(
        request,
        'students/edit_student.html',
        {
            'student': student,
            'classes': classes,
            'departments': departments,
            'electives': electives,
            'blood_groups': Student.BLOOD_GROUPS,
        }
    )
    
@school_permission_required("classes.promote")
@login_required
def promote_class(request):

    classes = SchoolClass.objects.filter(
        school=request.user.school
    )

    if request.method == 'POST':

        from_class_id = request.POST.get('from_class')
        to_class_id = request.POST.get('to_class')
        action = request.POST.get('action')

        from_class = get_object_or_404(
            SchoolClass,
            id=from_class_id,
            school=request.user.school,
        )

        to_class = None

        if to_class_id:
            to_class = get_object_or_404(
                SchoolClass,
                id=to_class_id,
                school=request.user.school,
            )

        students = Student.objects.filter(
            school_class_id=from_class_id,
            user__school=request.user.school,
            is_active=True
        )

        if action == "promote":

            if from_class_id and to_class_id and from_class_id != to_class_id:

                count = students.update(
                    school_class=to_class,
                    admission_status="ACTIVE",
                    is_active=True
                )

                return render(
                    request,
                    'students/promote_result.html',
                    {
                        'count': count,
                        'action': 'Promoted',
                        'from_class': from_class,
                        'to_class': to_class,
                    }
                )


        elif action == "graduate":

            count = students.update(
                admission_status="GRADUATED",
                is_active=False
            )

            return render(
                request,
                'students/promote_result.html',
                {
                    'count': count,
                    'action': 'Graduated',
                    'from_class': from_class,
                }
            )


    return render(
        request,
        'students/promote_class.html',
        {
            'classes': classes
        }
    )

@school_permission_required("students.view")
@login_required
def student_profile(request, student_id):

    student = get_object_or_404(
        Student.objects.select_related(
            "user",
            "school_class",
            "department",
        ),
        id=student_id,
        user__school=request.user.school,
    )

    return render(
        request,
        "students/student_profile.html",
        {
            "student": student,
        },
    )