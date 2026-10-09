from django.core.exceptions import ValidationError
from django.db import models


class Curriculum(models.Model):
    name = models.CharField(
        max_length=200,
    )

    provider = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    version = models.CharField(
        max_length=50,
        blank=True,
    )

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='curriculums',
    )

    is_system = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.name

class CurriculumLevel(models.Model):
    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE,
        related_name='levels',
    )

    name = models.CharField(
        max_length=100,
    )

    code = models.CharField(
        max_length=30,
        blank=True,
    )

    sequence = models.PositiveIntegerField(
        default=0,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.name

class CurriculumSubject(models.Model):
    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE,
        related_name='subjects',
    )

    curriculum_level = models.ForeignKey(
        CurriculumLevel,
        on_delete=models.CASCADE,
        related_name='subjects',
    )

    name = models.CharField(
        max_length=100,
    )

    code = models.CharField(
        max_length=30,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    sequence = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.name

class CurriculumSubjectMapping(models.Model):
    curriculum_subject = models.ForeignKey(
        CurriculumSubject,
        on_delete=models.CASCADE,
        related_name='subject_mappings',
    )

    subject = models.ForeignKey(
        'subjects.Subject',
        on_delete=models.CASCADE,
        related_name='curriculum_mappings',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'curriculum_subject',
                    'subject',
                ],
                name='unique_curriculum_subject_mapping',
            ),
        ]

    def __str__(self):
        return f"{self.curriculum_subject} → {self.subject}"

class CurriculumTopic(models.Model):
    curriculum_subject = models.ForeignKey(
        CurriculumSubject,
        on_delete=models.CASCADE,
        related_name='topics',
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtopics',
    )

    title = models.CharField(
        max_length=200,
    )

    code = models.CharField(
        max_length=30,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    sequence = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.title

class CurriculumLearningObjective(models.Model):
    curriculum_topic = models.ForeignKey(
        CurriculumTopic,
        on_delete=models.CASCADE,
        related_name='learning_objectives',
    )

    statement = models.TextField()

    code = models.CharField(
        max_length=30,
        blank=True,
    )

    sequence = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.statement

class SchemeOfWork(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.PROTECT,
        related_name='schemes_of_work',
    )

    school_class = models.ForeignKey(
        'students.SchoolClass',
        on_delete=models.PROTECT,
        related_name='schemes_of_work',
    )

    subject = models.ForeignKey(
        'subjects.Subject',
        on_delete=models.PROTECT,
        related_name='schemes_of_work',
    )

    term = models.ForeignKey(
        'academics.Term',
        on_delete=models.PROTECT,
        related_name='schemes_of_work',
    )

    name = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'school',
                    'school_class',
                    'subject',
                    'term',
                ],
                name='unique_scheme_per_class_subject_term',
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if self.school_id and self.school_class_id:
            if self.school_class.school_id != self.school_id:
                errors['school_class'] = (
                    'The selected class does not belong to this school.'
                )

        if self.school_id and self.subject_id:
            if self.subject.school_id != self.school_id:
                errors['subject'] = (
                    'The selected subject does not belong to this school.'
                )

        if self.school_id and self.term_id:
            if self.term.session.school_id != self.school_id:
                errors['term'] = (
                    'The selected term does not belong to this school.'
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name
    

class SchemeOfWorkItem(models.Model):
    scheme_of_work = models.ForeignKey(
        SchemeOfWork,
        on_delete=models.CASCADE,
        related_name='items',
    )

    curriculum_topic = models.ForeignKey(
        CurriculumTopic,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='scheme_of_work_items',
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    week_number = models.PositiveIntegerField(
        default=1,
    )

    sequence = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    def clean(self):
        super().clean()

        if self.curriculum_topic_id and self.scheme_of_work_id:
            is_mapped = CurriculumSubjectMapping.objects.filter(
                curriculum_subject=self.curriculum_topic.curriculum_subject,
                subject=self.scheme_of_work.subject,
            ).exists()

            if not is_mapped:
                raise ValidationError(
                    {
                        'curriculum_topic': (
                            'This curriculum topic is not mapped to the '
                            'subject of this Scheme of Work.'
                        )
                    }
                )

    def __str__(self):
        return self.title
    
    
class LessonNote(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        REVIEWED = 'REVIEWED', 'Reviewed'
        APPROVED = 'APPROVED', 'Approved'
        PUBLISHED = 'PUBLISHED', 'Published'

    scheme_item = models.ForeignKey(
        SchemeOfWorkItem,
        on_delete=models.CASCADE,
        related_name='lesson_notes',
    )

    teacher = models.ForeignKey(
        'teachers.Teacher',
        on_delete=models.PROTECT,
        related_name='lesson_notes',
    )

    lesson_number = models.PositiveIntegerField(
        default=1,
    )

    title = models.CharField(
        max_length=200,
    )

    objectives = models.TextField(
        blank=True,
    )

    content = models.TextField(
        blank=True,
    )

    activities = models.TextField(
        blank=True,
    )

    resources = models.TextField(
        blank=True,
    )

    assessment = models.TextField(
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['scheme_item', 'lesson_number'],
                condition=models.Q(is_active=True),
                name='unique_active_lesson_number_per_scheme_item',
            ),
        ]
    
    def clean(self):
        super().clean()

        if self.scheme_item_id and self.teacher_id:
            scheme_school_id = (
                self.scheme_item.scheme_of_work.school_id
            )
            teacher_school_id = self.teacher.school.id

            if scheme_school_id != teacher_school_id:
                raise ValidationError(
                    {
                        'teacher': (
                            'The selected teacher does not belong to '
                            'the school of this Scheme of Work.'
                        )
                    }
                )

    def __str__(self):
        return self.title