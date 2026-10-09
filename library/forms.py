from django import forms
from django.db.models import Q

from accounts.utils import get_teacher
from allocations.models import SubjectAllocation
from library.models import LessonNote, SchemeOfWorkItem


class LessonNoteForm(forms.ModelForm):
    class Meta:
        model = LessonNote
        fields = [
            "scheme_item",
            "title",
            "objectives",
            "content",
            "activities",
            "resources",
            "assessment",
            "notes",
        ]
        widgets = {
            "objectives": forms.Textarea(attrs={"rows": 4}),
            "content": forms.Textarea(attrs={"rows": 8}),
            "activities": forms.Textarea(attrs={"rows": 6}),
            "resources": forms.Textarea(attrs={"rows": 4}),
            "assessment": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["scheme_item"].queryset = SchemeOfWorkItem.objects.none()

        teacher = get_teacher(user) if user else None

        if not teacher or not user.school:
            return

        teacher_allocations = SubjectAllocation.objects.filter(
            teacher=teacher,
            subject__school=user.school,
            school_class__school=user.school,
            term__session__school=user.school,
        ).values(
            "subject_id",
            "school_class_id",
            "term_id",
        )

        allocation_filter = Q()

        for allocation in teacher_allocations:
            allocation_filter |= Q(
                scheme_of_work__subject_id=allocation["subject_id"],
                scheme_of_work__school_class_id=allocation["school_class_id"],
                scheme_of_work__term_id=allocation["term_id"],
            )

        allocated_items = (
            SchemeOfWorkItem.objects.filter(
                allocation_filter,
                scheme_of_work__school=user.school,
                scheme_of_work__is_active=True,
                is_active=True,
            )
            .select_related(
                "scheme_of_work",
                "scheme_of_work__subject",
                "scheme_of_work__school_class",
                "scheme_of_work__term",
            )
            .order_by(
                "scheme_of_work__term__session__name",
                "scheme_of_work__term__name",
                "scheme_of_work__school_class__name",
                "scheme_of_work__subject__name",
                "week_number",
                "sequence",
                "title",
            )
            .distinct()
        )
        
        self.fields["scheme_item"].queryset = allocated_items