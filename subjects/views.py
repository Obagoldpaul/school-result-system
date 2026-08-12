from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .forms import SubjectForm, ClassSubjectForm
from .models import Subject, ClassSubject
from accounts.decorators import staff_required



@staff_required
@login_required
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
def class_subject_list(request):

    class_subjects = (
        ClassSubject.objects
        .filter(
            school_class__school=request.user.school
        )
        .select_related(
            'school_class',
            'subject',
        )
    )

    return render(
        request,
        'subjects/class_subject_list.html',
        {
            'class_subjects': class_subjects
        }
    )

@staff_required
@login_required
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
