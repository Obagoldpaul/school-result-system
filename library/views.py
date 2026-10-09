from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Max
from django.shortcuts import redirect, render

from accounts.utils import get_teacher
from library.forms import LessonNoteForm
from library.models import Curriculum, LessonNote


@login_required
def lesson_note_create(request):
    teacher = get_teacher(request.user)

    if not teacher or not request.user.school:
        raise PermissionDenied

    if request.method == "POST":
        form = LessonNoteForm(request.POST, user=request.user)

        if form.is_valid():
            lesson_note = form.save(commit=False)

            lesson_note.teacher = teacher
            lesson_note.status = LessonNote.Status.DRAFT
            lesson_note.is_active = True

            last_lesson_number = (
                LessonNote.objects.filter(
                    scheme_item=lesson_note.scheme_item,
                    is_active=True,
                ).aggregate(
                    max_lesson_number=Max("lesson_number")
                )["max_lesson_number"]
            )

            lesson_note.lesson_number = (
                last_lesson_number + 1
                if last_lesson_number is not None
                else 1
            )

            lesson_note.save()

            return redirect("lesson_note_create")

    else:
        form = LessonNoteForm(user=request.user)

    return render(
        request,
        "library/lesson_note_form.html",
        {"form": form},
    )
    
    
@login_required
def curriculum_list(request):
    if not request.user.school:
        raise PermissionDenied

    curriculums = (
        Curriculum.objects.filter(
            Q(
                is_system=True,
                school__isnull=True,
            )
            | Q(
                school=request.user.school,
            ),
            is_active=True,
        )
        .order_by("name")
    )

    return render(
        request,
        "library/curriculum_list.html",
        {"curriculums": curriculums},
    )