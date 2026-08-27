from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.permissions import school_permission_required

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

    if request.method == 'POST':
        form = SubjectForm(
            request.POST,
            instance=subject,
            user=request.user,
        )

        if form.is_valid():
            form.save()
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
            'subject_list_url': '/subjects/',
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

    subjects = Subject.objects.filter(
        school=request.user.school,
        is_active=True,
    )

    return render(
        request,
        'subjects/subject_list.html',
        {
            'subjects': subjects
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
        .order_by(
            'school_class__section',
            'school_class__name',
            'subject__name',
        )
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
        return redirect('class_subject_list')

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
        }
    )
