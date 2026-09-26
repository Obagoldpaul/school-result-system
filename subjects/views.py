from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required

from accounts.permissions import school_permission_required
from students.models import Student, SchoolClass, Department
from .forms import (
    SubjectForm,
    ClassSubjectForm,
    BulkClassSubjectForm,
)
from .models import Subject, ClassSubject
from accounts.decorators import staff_required

from django.contrib import messages



@staff_required
@login_required
@school_permission_required("subjects.manage")
def add_subject(request):

    if request.method == 'POST':
        form = SubjectForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            form.save()
            return redirect('subject_list')

    else:
        form = SubjectForm(
            user=request.user,
        )

    return render(
        request,
        'subjects/add_subject.html',
        {
            'form': form,
            'subject_list_url': '/subjects/',
        }
    )

@staff_required
@login_required
@school_permission_required("subjects.manage")
def edit_subject(request, subject_id):

    subject = get_object_or_404(
        Subject,
        id=subject_id,
        school=request.user.school,
    )

    # Preserve the subject-level filter through the edit process.
    selected_level = request.GET.get("level") or request.POST.get("level")

    if request.method == 'POST':
        form = SubjectForm(
            request.POST,
            instance=subject,
            user=request.user,
        )

        if form.is_valid():
            form.save()

            if selected_level:
                return redirect(
                    f"{reverse('subject_list')}?level={selected_level}"
                )

            return redirect('subject_list')

    else:
        form = SubjectForm(
            instance=subject,
            user=request.user,
        )

    return render(
        request,
        'subjects/edit_subject.html',
        {
            'form': form,
            'subject': subject,
            'subject_list_url': (
                f"{reverse('subject_list')}?level={selected_level}"
                if selected_level
                else reverse('subject_list')
            ),
            'selected_level': selected_level,
        }
    )

@staff_required
@login_required
@school_permission_required("subjects.manage")
def deactivate_subject(request, subject_id):

    subject = get_object_or_404(
        Subject,
        id=subject_id,
        school=request.user.school,
    )

    if request.method == 'POST':
        subject.is_active = False
        subject.save(update_fields=['is_active'])

    return redirect('subject_list')


@staff_required
@login_required
@school_permission_required("subjects.manage")
def activate_subject(request, subject_id):

    subject = get_object_or_404(
        Subject,
        id=subject_id,
        school=request.user.school,
    )

    if request.method == 'POST':
        subject.is_active = True
        subject.save(update_fields=['is_active'])

    return redirect('subject_list')


@staff_required
@login_required
@school_permission_required("subjects.view")
def subject_list(request):

    school = request.user.school

    subjects = Subject.objects.filter(
        school=school,
        is_active=True,
    )

    # --------------------------------------------------
    # FILTER BY SUBJECT LEVEL
    # --------------------------------------------------

    selected_level = request.GET.get("level")

    if selected_level in [
        Subject.SubjectLevel.PRIMARY,
        Subject.SubjectLevel.SECONDARY,
    ]:
        subjects = subjects.filter(
            level=selected_level
        )
        
    
    # --------------------------------------------------
    # FILTER BY SUBJECT TYPE
    # --------------------------------------------------

    selected_type = request.GET.get("type")

    if selected_type in ["ELECTIVE", "COMPULSORY"]:
        if selected_type == "ELECTIVE":
            subjects = subjects.filter(is_elective=True)
        else:
            subjects = subjects.filter(is_elective=False)

    # --------------------------------------------------
    # AVAILABLE LEVELS FOR THIS SCHOOL
    # --------------------------------------------------

    if school.school_type == school.SchoolType.PRIMARY:

        available_levels = [
            Subject.SubjectLevel.PRIMARY
        ]

    elif school.school_type == school.SchoolType.SECONDARY:

        available_levels = [
            Subject.SubjectLevel.SECONDARY
        ]

    else:

        available_levels = [
            Subject.SubjectLevel.PRIMARY,
            Subject.SubjectLevel.SECONDARY,
        ]

    return render(
        request,
        'subjects/subject_list.html',
        {
            'subjects': subjects,
            'available_levels': available_levels,
            'selected_level': selected_level,
            'selected_type': selected_type,
        }
    )


@staff_required
@login_required
@school_permission_required("subjects.assign")
def assign_subject_to_class(request):

    if request.method == 'POST':
        form = ClassSubjectForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            form.save()
            return redirect('class_subject_list')

    else:
        form = ClassSubjectForm(
            user=request.user,
        )

    return render(
        request,
        'subjects/assign_subject.html',
        {
            'form': form
        }
    )


@staff_required
@login_required
@school_permission_required("subjects.view")
def class_subject_list(request):

    school = request.user.school

    selected_section = request.GET.get("section")
    selected_class = request.GET.get("class")

    class_subjects = (
        ClassSubject.objects
        .filter(
            school_class__school=school
        )
        .select_related(
            'school_class',
            'subject',
            'subject__parent',
        )
    )

    if selected_section:
        class_subjects = class_subjects.filter(
            school_class__section=selected_section
        )

    if selected_class:
        class_subjects = class_subjects.filter(
            school_class_id=selected_class
        )

    class_subjects = class_subjects.order_by(
        'school_class__section',
        'school_class__name',
        'subject__name',
    )

    # --------------------------------------------------
    # SECTION ORDER
    # --------------------------------------------------

    section_order = [
        (
            'PRE_PRIMARY',
            'Pre-Primary',
        ),
        (
            'PRIMARY',
            'Primary',
        ),
        (
            'JUNIOR_SECONDARY',
            'Junior Secondary',
        ),
        (
            'SENIOR_SECONDARY',
            'Senior Secondary',
        ),
    ]

    # --------------------------------------------------
    # GROUP BY SECTION → CLASS
    # --------------------------------------------------

    grouped_sections = []

    for section_value, section_label in section_order:

        section_assignments = [
            cs
            for cs in class_subjects
            if cs.school_class.section == section_value
        ]

        classes = []

        class_ids = []
        for cs in section_assignments:
            if cs.school_class_id not in class_ids:
                class_ids.append(cs.school_class_id)

        for class_id in class_ids:

            class_obj = next(
                cs.school_class
                for cs in section_assignments
                if cs.school_class_id == class_id
            )

            assignments = [
                cs
                for cs in section_assignments
                if cs.school_class_id == class_id
            ]

            classes.append({
                'school_class': class_obj,
                'assignments': assignments,
            })

        grouped_sections.append({
            'value': section_value,
            'label': section_label,
            'classes': classes,
        })

    return render(
        request,
        'subjects/class_subject_list.html',
        {
            'grouped_sections': grouped_sections,
            'selected_section': selected_section,
            'selected_class': selected_class,
            'classes': SchoolClass.objects.filter(
                school=school,
                is_active=True,
            ).order_by(
                'section',
                'name',
            ),
        }
    )

@staff_required
@login_required
@school_permission_required("subjects.assign")
def unassign_subject_from_class(request, assignment_id):

    assignment = get_object_or_404(
        ClassSubject,
        id=assignment_id,
        school_class__school=request.user.school,
    )

    if request.method == 'POST':
        assignment.delete()

        selected_section = request.POST.get('section')
        selected_class = request.POST.get('class')

        redirect_url = reverse('class_subject_list')

        query_params = []

        if selected_section:
            query_params.append(f"section={selected_section}")

        if selected_class:
            query_params.append(f"class={selected_class}")

        if query_params:
            redirect_url += "?" + "&".join(query_params)

        return redirect(redirect_url)

    return render(
        request,
        'subjects/confirm_unassign.html',
        {
            'assignment': assignment,
        }
    )

@staff_required
@login_required
@school_permission_required("subjects.view")
def inactive_subject_list(request):

    subjects = Subject.objects.filter(
        school=request.user.school,
        is_active=False,
    )

    return render(
        request,
        'subjects/inactive_subject_list.html',
        {
            'subjects': subjects,
        }
    )
    
@staff_required
@login_required
@school_permission_required("subjects.assign")
def bulk_assign_subjects(request):

    school = request.user.school

    if request.method == 'POST':

        form = BulkClassSubjectForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():

            school_class = form.cleaned_data["school_class"]
            subjects = form.cleaned_data["subjects"]

            created_count = 0

            for subject in subjects:

                _, created = ClassSubject.objects.get_or_create(
                    school_class=school_class,
                    subject=subject,
                )

                if created:
                    created_count += 1

            messages.success(
                request,
                f"{created_count} subject(s) assigned to {school_class}."
            )

            return redirect(
                'class_subject_list'
            )

    else:

        form = BulkClassSubjectForm(
            user=request.user,
        )

    return render(
        request,
        'subjects/bulk_assign_subjects.html',
        {
            'form': form,
            'subject_levels': {
                str(subject.id): subject.level
                for subject in form.fields["subjects"].queryset
            },
        }
    )


@staff_required
@login_required
@school_permission_required("subjects.assign")
def assign_electives_to_student(request, student_id):

    student = get_object_or_404(
        Student,
        id=student_id,
        user__school=request.user.school,
    )

    available_electives = (
        Subject.objects
        .filter(
            school=request.user.school,
            is_elective=True,
            is_active=True,
            classsubject__school_class=student.school_class,
        )
        .distinct()
        .order_by("name")
    )

    if request.method == "POST":

        elective_ids = request.POST.getlist("electives")

        valid_electives = available_electives.filter(
            id__in=elective_ids
        )

        student.elective_subjects.set(valid_electives)

        messages.success(
            request,
            f"Elective subjects updated for {student.user.get_full_name() or student.user.username}."
        )

        selected_class = request.GET.get("class")
        selected_department = request.GET.get("department")

        redirect_url = reverse("elective_assignment_list")

        query_params = []

        if selected_class:
            query_params.append(f"class={selected_class}")

        if selected_department:
            query_params.append(f"department={selected_department}")

        if query_params:
            redirect_url += "?" + "&".join(query_params)

        return redirect(redirect_url)

    selected_electives = student.elective_subjects.filter(
        id__in=available_electives.values("id")
    )

    return render(
        request,
        "subjects/assign_electives_to_student.html",
        {
            "student": student,
            "available_electives": available_electives,
            "selected_electives": selected_electives,
        },
    )
    
@staff_required
@login_required
@school_permission_required("subjects.assign")
def elective_assignment_list(request):

    school = request.user.school

    students = (
        Student.objects
        .filter(
            user__school=school,
            is_active=True,
            admission_status="ACTIVE",
        )
        .select_related(
            "user",
            "school_class",
            "department",
        )
        .prefetch_related("elective_subjects")
        .order_by(
            "school_class__section",
            "school_class__name",
            "user__last_name",
            "user__first_name",
        )
    )

    classes = SchoolClass.objects.filter(
        school=school,
        is_active=True,
    ).order_by(
        "section",
        "name",
    )

    departments = Department.objects.filter(
        school=school,
    ).order_by("name")

    selected_class = request.GET.get("class")
    selected_department = request.GET.get("department")

    if selected_class:
        students = students.filter(
            school_class_id=selected_class
        )

    if selected_department:
        students = students.filter(
            department_id=selected_department
        )

    if request.method == "POST":

        if not selected_department:
            messages.error(
                request,
                "Select a department before applying department defaults."
            )
            return redirect("elective_assignment_list")

        department = get_object_or_404(
            Department,
            id=selected_department,
            school=school,
        )

        default_electives = department.default_electives.filter(
            school=school,
            is_elective=True,
            is_active=True,
        )

        updated_count = 0

        for student in students:

            student_electives = default_electives.filter(
                classsubject__school_class=student.school_class,
            ).distinct()

            if student_electives.exists():
                student.elective_subjects.add(
                    *student_electives
                )
                updated_count += 1

        messages.success(
            request,
            f"Department defaults applied to "
            f"{updated_count} student(s). Existing elective assignments "
            f"were preserved."
        )

        return redirect(
            f"{reverse('elective_assignment_list')}"
            f"?department={selected_department}"
            + (
                f"&class={selected_class}"
                if selected_class
                else ""
            )
        )

    return render(
        request,
        "subjects/elective_assignment_list.html",
        {
            "students": students,
            "classes": classes,
            "departments": departments,
            "selected_class": selected_class,
            "selected_department": selected_department,
        },
    )