from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import SubjectForm, ClassSubjectForm
from .models import Subject, ClassSubject
from accounts.decorators import staff_required

@staff_required
@login_required
def add_subject(request):
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('subject_list')
    else:
        form = SubjectForm()
    return render(request, 'subjects/add_subject.html', {
        'form': form,
        'subject_list_url': '/subjects/',
    })

@staff_required
@login_required
def subject_list(request):
    subjects = Subject.objects.filter(is_active=True)
    return render(request, 'subjects/subject_list.html', {'subjects': subjects})

@staff_required
@login_required
def assign_subject_to_class(request):
    if request.method == 'POST':
        form = ClassSubjectForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('class_subject_list')
    else:
        form = ClassSubjectForm()
    return render(request, 'subjects/assign_subject.html', {'form': form})

@staff_required
@login_required
def class_subject_list(request):
    class_subjects = ClassSubject.objects.select_related('school_class', 'subject').all()
    return render(request, 'subjects/class_subject_list.html', {'class_subjects': class_subjects})