from datetime import time
from django.utils import timezone
from .availability import teacher_is_available
from .generator import TimetableGenerationError, generate_timetable

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from .services import sync_timetable_requirements

from academics.models import AcademicSession, Term
from allocations.models import SubjectAllocation
from schools.models import (
    School,
    SchoolRole,
    Permission,
    SchoolSubscription, 
    SubscriptionPackage,
)
from students.models import SchoolClass
from subjects.models import Subject
from teachers.models import Teacher

from .models import (
    Timetable,
    TimetableEntry,
    TimetablePeriod,
    TimetableRequirement,
    TeacherAvailability,
)
from .forms import TimetableForm, TimetablePeriodForm, TimetableRequirementForm


User = get_user_model()


class TimetableModelValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            name="Timetable Test School",
            code="TTS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.other_school = School.objects.create(
            name="Other Test School",
            code="OTS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.user = User.objects.create_user(
            username="timetable_test_user",
            password="testpass123",
        )
        cls.user.school = cls.school
        cls.user.save()

        cls.other_user = User.objects.create_user(
            username="other_timetable_user",
            password="testpass123",
        )
        cls.other_user.school = cls.other_school
        cls.other_user.save()

        cls.session = AcademicSession.objects.create(
            school=cls.school,
            name="2026/2027",
            is_current=True,
        )

        cls.other_session = AcademicSession.objects.create(
            school=cls.other_school,
            name="2026/2027",
            is_current=True,
        )

        cls.term = Term.objects.create(
            session=cls.session,
            name=Term.TermName.FIRST,
        )
        
        cls.other_term_same_school = Term.objects.create(
            session=cls.session,
            name=Term.TermName.SECOND,
        )

        cls.other_term = Term.objects.create(
            session=cls.other_session,
            name=Term.TermName.FIRST,
        )

        cls.school_class = SchoolClass.objects.create(
            school=cls.school,
            name="JSS 1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
        )

        cls.other_class = SchoolClass.objects.create(
            school=cls.other_school,
            name="JSS 1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
        )

        cls.subject = Subject.objects.create(
            school=cls.school,
            name="Mathematics",
            code="MATH",
            level=Subject.SubjectLevel.SECONDARY,
        )

        cls.other_subject = Subject.objects.create(
            school=cls.other_school,
            name="Mathematics",
            code="MATH",
            level=Subject.SubjectLevel.SECONDARY,
        )

        cls.teacher_user = User.objects.create_user(
            username="timetable_teacher",
            password="testpass123",
        )
        cls.teacher_user.school = cls.school
        cls.teacher_user.save()

        cls.teacher = Teacher.objects.create(
            user=cls.teacher_user,
        )

        cls.other_teacher_user = User.objects.create_user(
            username="other_timetable_teacher",
            password="testpass123",
        )
        cls.other_teacher_user.school = cls.other_school
        cls.other_teacher_user.save()

        cls.other_teacher = Teacher.objects.create(
            user=cls.other_teacher_user,
        )

        cls.allocation = SubjectAllocation.objects.create(
            teacher=cls.teacher,
            subject=cls.subject,
            school_class=cls.school_class,
            term=cls.term,
        )

        cls.other_allocation = SubjectAllocation.objects.create(
            teacher=cls.other_teacher,
            subject=cls.other_subject,
            school_class=cls.other_class,
            term=cls.other_term,
        )

        cls.timetable = Timetable.objects.create(
            school=cls.school,
            term=cls.term,
            name="First Term Timetable",
            days=[
                TimetableEntry.Day.MONDAY,
                TimetableEntry.Day.TUESDAY,
                TimetableEntry.Day.WEDNESDAY,
                TimetableEntry.Day.THURSDAY,
                TimetableEntry.Day.FRIDAY,
                TimetableEntry.Day.SATURDAY,
            ],
            created_by=cls.user,
        )

        cls.other_timetable = Timetable.objects.create(
            school=cls.other_school,
            term=cls.other_term,
            name="Other School Timetable",
            days=[
                TimetableEntry.Day.MONDAY,
                TimetableEntry.Day.TUESDAY,
                TimetableEntry.Day.WEDNESDAY,
                TimetableEntry.Day.THURSDAY,
                TimetableEntry.Day.FRIDAY,
                TimetableEntry.Day.SATURDAY,
            ],
            created_by=cls.other_user,
        )

    def test_timetable_rejects_term_from_another_school(self):
        timetable = Timetable(
            school=self.school,
            term=self.other_term,
            name="Invalid Timetable",
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            timetable.full_clean()

    def test_requirement_rejects_allocation_from_another_school(self):
        requirement = TimetableRequirement(
            timetable=self.timetable,
            allocation=self.other_allocation,
            lessons_per_week=3,
        )

        with self.assertRaises(ValidationError):
            requirement.full_clean()

    def test_requirement_rejects_allocation_from_another_term(self):
        other_term_same_school_allocation = SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
            term=self.other_term_same_school,
        )

        requirement = TimetableRequirement(
            timetable=self.timetable,
            allocation=other_term_same_school_allocation,
            lessons_per_week=3,
        )

        with self.assertRaises(ValidationError):
            requirement.full_clean()

    def test_period_rejects_end_time_before_start_time(self):
        period = TimetablePeriod(
            timetable=self.timetable,
            name="Period 1",
            period_number=1,
            start_time=time(10, 00),
            end_time=time(9, 00),
        )

        with self.assertRaises(ValidationError):
            period.full_clean()

    def test_period_rejects_equal_start_and_end_time(self):
        period = TimetablePeriod(
            timetable=self.timetable,
            name="Period 1",
            period_number=1,
            start_time=time(10, 00),
            end_time=time(10, 00),
        )

        with self.assertRaises(ValidationError):
            period.full_clean()

    def test_entry_rejects_break_period(self):
        period = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Break",
            period_number=1,
            start_time=time(10, 00),
            end_time=time(10, 30),
            is_break=True,
        )

        requirement = TimetableRequirement.objects.create(
            timetable=self.timetable,
            allocation=self.allocation,
            lessons_per_week=3,
        )

        entry = TimetableEntry(
            timetable=self.timetable,
            requirement=requirement,
            day=TimetableEntry.Day.MONDAY,
            period=period,
        )

        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_entry_rejects_inactive_period(self):
        period = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Inactive Period",
            period_number=1,
            start_time=time(10, 00),
            end_time=time(10, 30),
            is_active=False,
        )

        requirement = TimetableRequirement.objects.create(
            timetable=self.timetable,
            allocation=self.allocation,
            lessons_per_week=3,
        )

        entry = TimetableEntry(
            timetable=self.timetable,
            requirement=requirement,
            day=TimetableEntry.Day.MONDAY,
            period=period,
        )

        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_entry_rejects_requirement_from_another_timetable(self):
        period = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Period 1",
            period_number=1,
            start_time=time(8, 00),
            end_time=time(9, 00),
        )

        requirement = TimetableRequirement.objects.create(
            timetable=self.other_timetable,
            allocation=self.other_allocation,
            lessons_per_week=3,
        )

        entry = TimetableEntry(
            timetable=self.timetable,
            requirement=requirement,
            day=TimetableEntry.Day.MONDAY,
            period=period,
        )

        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_entry_rejects_period_from_another_timetable(self):
        requirement = TimetableRequirement.objects.create(
            timetable=self.timetable,
            allocation=self.allocation,
            lessons_per_week=3,
        )

        period = TimetablePeriod.objects.create(
            timetable=self.other_timetable,
            name="Period 1",
            period_number=1,
            start_time=time(8, 00),
            end_time=time(9, 00),
        )

        entry = TimetableEntry(
            timetable=self.timetable,
            requirement=requirement,
            day=TimetableEntry.Day.MONDAY,
            period=period,
        )

        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_requirement_rejects_too_many_double_periods(self):
        requirement = TimetableRequirement(
            timetable=self.timetable,
            allocation=self.allocation,
            lessons_per_week=3,
            double_periods=2,
        )

        with self.assertRaises(ValidationError):
            requirement.full_clean()

    def test_requirement_accepts_valid_double_period_configuration(self):
        requirement = TimetableRequirement(
            timetable=self.timetable,
            allocation=self.allocation,
            lessons_per_week=4,
            double_periods=2,
        )

        requirement.full_clean()

    def test_valid_timetable_requirement_passes_validation(self):
        requirement = TimetableRequirement(
            timetable=self.timetable,
            allocation=self.allocation,
            lessons_per_week=4,
            double_periods=1,
        )

        requirement.full_clean()

    def test_valid_timetable_entry_passes_validation(self):
        period = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Period 1",
            period_number=1,
            start_time=time(8, 00),
            end_time=time(9, 00),
        )

        requirement = TimetableRequirement.objects.create(
            timetable=self.timetable,
            allocation=self.allocation,
            lessons_per_week=3,
        )

        entry = TimetableEntry(
            timetable=self.timetable,
            requirement=requirement,
            day=TimetableEntry.Day.MONDAY,
            period=period,
        )

        entry.full_clean()
        

class TimetableRequirementSyncTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            name="Requirement Sync School",
            code="RSS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.user = User.objects.create_user(
            username="requirement_sync_user",
            password="testpass123",
        )
        cls.user.school = cls.school
        cls.user.save()

        cls.session = AcademicSession.objects.create(
            school=cls.school,
            name="2026/2027",
            is_current=True,
        )

        cls.term = Term.objects.create(
            session=cls.session,
            name=Term.TermName.FIRST,
        )

        cls.school_class = SchoolClass.objects.create(
            school=cls.school,
            name="JSS 1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=True,
        )

        cls.subject = Subject.objects.create(
            school=cls.school,
            name="Mathematics",
            code="RSMATH",
            level=Subject.SubjectLevel.SECONDARY,
        )

        cls.teacher_user = User.objects.create_user(
            username="requirement_sync_teacher",
            password="testpass123",
        )
        cls.teacher_user.school = cls.school
        cls.teacher_user.save()

        cls.teacher = Teacher.objects.create(
            user=cls.teacher_user,
        )

        cls.timetable = Timetable.objects.create(
            school=cls.school,
            term=cls.term,
            name="Requirement Sync Timetable",
            days=[
                TimetableEntry.Day.MONDAY,
                TimetableEntry.Day.TUESDAY,
                TimetableEntry.Day.WEDNESDAY,
                TimetableEntry.Day.THURSDAY,
                TimetableEntry.Day.FRIDAY,
            ],
            created_by=cls.user,
        )

    def test_sync_creates_missing_requirement_with_defaults(self):
        allocation = SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
            term=self.term,
        )

        created_count = sync_timetable_requirements(self.timetable)

        self.assertEqual(created_count, 1)

        requirement = TimetableRequirement.objects.get(
            timetable=self.timetable,
            allocation=allocation,
        )

        self.assertEqual(requirement.lessons_per_week, 1)
        self.assertEqual(requirement.double_periods, 0)

    def test_sync_does_not_modify_existing_requirement(self):
        allocation = SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
            term=self.term,
        )

        requirement = TimetableRequirement.objects.create(
            timetable=self.timetable,
            allocation=allocation,
            lessons_per_week=4,
            double_periods=1,
        )

        created_count = sync_timetable_requirements(self.timetable)

        requirement.refresh_from_db()

        self.assertEqual(created_count, 0)
        self.assertEqual(requirement.lessons_per_week, 4)
        self.assertEqual(requirement.double_periods, 1)

    def test_sync_excludes_inactive_classes(self):
        inactive_class = SchoolClass.objects.create(
            school=self.school,
            name="JSS 2",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=False,
        )

        allocation = SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            school_class=inactive_class,
            term=self.term,
        )

        created_count = sync_timetable_requirements(self.timetable)

        self.assertEqual(created_count, 0)

        self.assertFalse(
            TimetableRequirement.objects.filter(
                timetable=self.timetable,
                allocation=allocation,
            ).exists()
        )

    def test_sync_only_creates_requirements_for_matching_school_and_term(self):
        other_session = AcademicSession.objects.create(
            school=self.school,
            name="2027/2028",
            is_current=False,
        )

        other_term = Term.objects.create(
            session=other_session,
            name=Term.TermName.FIRST,
        )

        allocation = SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
            term=other_term,
        )

        created_count = sync_timetable_requirements(self.timetable)

        self.assertEqual(created_count, 0)

        self.assertFalse(
            TimetableRequirement.objects.filter(
                timetable=self.timetable,
                allocation=allocation,
            ).exists()
        )

    def test_sync_creates_multiple_missing_requirements(self):
        second_subject = Subject.objects.create(
            school=self.school,
            name="English",
            code="RSENG",
            level=Subject.SubjectLevel.SECONDARY,
        )

        first_allocation = SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
            term=self.term,
        )

        second_allocation = SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=second_subject,
            school_class=self.school_class,
            term=self.term,
        )

        created_count = sync_timetable_requirements(self.timetable)

        self.assertEqual(created_count, 2)

        self.assertTrue(
            TimetableRequirement.objects.filter(
                timetable=self.timetable,
                allocation=first_allocation,
            ).exists()
        )

        self.assertTrue(
            TimetableRequirement.objects.filter(
                timetable=self.timetable,
                allocation=second_allocation,
            ).exists()
        )

class TimetableFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            name="Form Test School",
            code="FTS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.other_school = School.objects.create(
            name="Other Form School",
            code="OFS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.user = User.objects.create_user(
            username="form_test_user",
            password="testpass123",
        )
        cls.user.school = cls.school
        cls.user.save()

        cls.session = AcademicSession.objects.create(
            school=cls.school,
            name="2026/2027",
            is_current=True,
        )

        cls.other_session = AcademicSession.objects.create(
            school=cls.other_school,
            name="2026/2027",
            is_current=True,
        )

        cls.term = Term.objects.create(
            session=cls.session,
            name=Term.TermName.FIRST,
        )

        cls.other_term = Term.objects.create(
            session=cls.other_session,
            name=Term.TermName.FIRST,
        )

        cls.school_class = SchoolClass.objects.create(
            school=cls.school,
            name="JSS 1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
        )

        cls.other_class = SchoolClass.objects.create(
            school=cls.other_school,
            name="JSS 1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
        )

        cls.subject = Subject.objects.create(
            school=cls.school,
            name="Mathematics",
            code="MATH",
            level=Subject.SubjectLevel.SECONDARY,
        )

        cls.other_subject = Subject.objects.create(
            school=cls.other_school,
            name="Mathematics",
            code="MATH",
            level=Subject.SubjectLevel.SECONDARY,
        )

        cls.teacher_user = User.objects.create_user(
            username="form_test_teacher",
            password="testpass123",
        )
        cls.teacher_user.school = cls.school
        cls.teacher_user.save()

        cls.teacher = Teacher.objects.create(
            user=cls.teacher_user,
        )

        cls.other_teacher_user = User.objects.create_user(
            username="other_form_teacher",
            password="testpass123",
        )
        cls.other_teacher_user.school = cls.other_school
        cls.other_teacher_user.save()

        cls.other_teacher = Teacher.objects.create(
            user=cls.other_teacher_user,
        )

        cls.allocation = SubjectAllocation.objects.create(
            teacher=cls.teacher,
            subject=cls.subject,
            school_class=cls.school_class,
            term=cls.term,
        )

        cls.other_allocation = SubjectAllocation.objects.create(
            teacher=cls.other_teacher,
            subject=cls.other_subject,
            school_class=cls.other_class,
            term=cls.other_term,
        )

        cls.timetable = Timetable.objects.create(
            school=cls.school,
            term=cls.term,
            name="First Term Timetable",
            days=[
                TimetableEntry.Day.MONDAY,
                TimetableEntry.Day.TUESDAY,
                TimetableEntry.Day.WEDNESDAY,
                TimetableEntry.Day.THURSDAY,
                TimetableEntry.Day.FRIDAY,
                TimetableEntry.Day.SATURDAY,
            ],
            created_by=cls.user,
        )

    def test_timetable_form_only_exposes_name(self):
        form = TimetableForm()

        self.assertEqual(
            list(form.fields.keys()),
            ["name", "days", "session", "term"],
        )

    def test_requirement_form_without_timetable_has_no_allocations(self):
        form = TimetableRequirementForm()

        self.assertEqual(
            form.fields["allocation"].queryset.count(),
            0,
        )

    def test_requirement_form_only_shows_allocations_for_timetable_school_and_term(
        self,
    ):
        form = TimetableRequirementForm(timetable=self.timetable)

        allocation_ids = set(
            form.fields["allocation"].queryset.values_list(
                "id",
                flat=True,
            )
        )

        self.assertIn(self.allocation.id, allocation_ids)
        self.assertNotIn(self.other_allocation.id, allocation_ids)

    def test_requirement_form_accepts_valid_allocation(self):
        form = TimetableRequirementForm(
            data={
                "allocation": self.allocation.id,
                "lessons_per_week": 4,
                "double_periods": 1,
            },
            timetable=self.timetable,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_requirement_form_rejects_allocation_from_another_school(
        self,
    ):
        form = TimetableRequirementForm(
            data={
                "allocation": self.other_allocation.id,
                "lessons_per_week": 4,
                "double_periods": 1,
            },
            timetable=self.timetable,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("allocation", form.errors)

    def test_requirement_form_rejects_allocation_without_timetable(
        self,
    ):
        form = TimetableRequirementForm(
            data={
                "allocation": self.allocation.id,
                "lessons_per_week": 4,
                "double_periods": 1,
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn("allocation", form.errors)

    def test_period_form_rejects_invalid_time_range(self):
        form = TimetablePeriodForm(
            data={
                "name": "Period 1",
                "period_number": 1,
                "start_time": "10:00",
                "end_time": "09:00",
                "is_break": False,
                "is_active": True,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_period_form_accepts_valid_period(self):
        form = TimetablePeriodForm(
            data={
                "name": "Period 1",
                "period_number": 1,
                "start_time": "08:00",
                "end_time": "09:00",
                "is_break": False,
                "is_active": True,
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_requirement_form_rejects_too_many_double_periods(
        self,
    ):
        form = TimetableRequirementForm(
            data={
                "allocation": self.allocation.id,
                "lessons_per_week": 3,
                "double_periods": 2,
            },
            timetable=self.timetable,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("double_periods", form.errors)
        
class TeacherAvailabilityModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            name="Availability Test School",
            code="ATS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.user = User.objects.create_user(
            username="availability_test_user",
            password="testpass123",
        )
        cls.user.school = cls.school
        cls.user.save()

        cls.teacher_user = User.objects.create_user(
            username="availability_teacher",
            password="testpass123",
        )
        cls.teacher_user.school = cls.school
        cls.teacher_user.save()

        cls.teacher = Teacher.objects.create(
            user=cls.teacher_user,
        )

    def test_valid_teacher_availability_can_be_created(self):
        availability = TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(8, 0),
            end_time=time(14, 0),
        )

        self.assertEqual(availability.teacher, self.teacher)
        self.assertEqual(
            availability.day,
            TeacherAvailability.Day.TUESDAY,
        )
        self.assertEqual(availability.start_time, time(8, 0))
        self.assertEqual(availability.end_time, time(14, 0))

    def test_availability_rejects_end_time_before_start_time(self):
        availability = TeacherAvailability(
            teacher=self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(14, 0),
            end_time=time(8, 0),
        )

        with self.assertRaises(ValidationError):
            availability.full_clean()

    def test_availability_rejects_equal_start_and_end_time(self):
        availability = TeacherAvailability(
            teacher=self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(8, 0),
            end_time=time(8, 0),
        )

        with self.assertRaises(ValidationError):
            availability.full_clean()

    def test_teacher_can_have_availability_on_different_days(self):
        monday = TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.MONDAY,
            start_time=time(8, 0),
            end_time=time(12, 0),
        )

        tuesday = TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(8, 0),
            end_time=time(14, 0),
        )

        self.assertEqual(
            TeacherAvailability.objects.filter(
                teacher=self.teacher
            ).count(),
            2,
        )
        self.assertNotEqual(monday.day, tuesday.day)

    def test_teacher_can_have_multiple_windows_on_same_day(self):
        morning = TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.MONDAY,
            start_time=time(8, 0),
            end_time=time(12, 0),
        )

        afternoon = TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.MONDAY,
            start_time=time(13, 0),
            end_time=time(16, 0),
        )

        self.assertEqual(
            TeacherAvailability.objects.filter(
                teacher=self.teacher,
                day=TeacherAvailability.Day.MONDAY,
            ).count(),
            2,
        )

        self.assertNotEqual(
            morning.start_time,
            afternoon.start_time,
        )

    def test_duplicate_availability_window_is_rejected(self):
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(8, 0),
            end_time=time(14, 0),
        )

        duplicate = TeacherAvailability(
            teacher=self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(8, 0),
            end_time=time(14, 0),
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_availability_is_associated_with_correct_teacher(self):
        other_teacher_user = User.objects.create_user(
            username="availability_other_teacher",
            password="testpass123",
        )
        other_teacher_user.school = self.school
        other_teacher_user.save()

        other_teacher = Teacher.objects.create(
            user=other_teacher_user,
        )

        availability = TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.WEDNESDAY,
            start_time=time(8, 0),
            end_time=time(14, 0),
        )

        other_availability = TeacherAvailability.objects.create(
            teacher=other_teacher,
            day=TeacherAvailability.Day.WEDNESDAY,
            start_time=time(8, 0),
            end_time=time(14, 0),
        )

        self.assertEqual(
            availability.teacher_id,
            self.teacher.id,
        )
        self.assertEqual(
            other_availability.teacher_id,
            other_teacher.id,
        )
        self.assertNotEqual(
            availability.teacher_id,
            other_availability.teacher_id,
        )
        
class TeacherAvailabilityHelperTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            name="Availability Helper School",
            code="AHS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.teacher_user = User.objects.create_user(
            username="availability_helper_teacher",
            password="testpass123",
        )
        cls.teacher_user.school = cls.school
        cls.teacher_user.save()

        cls.teacher = Teacher.objects.create(
            user=cls.teacher_user,
        )

    def test_period_fully_inside_availability_is_allowed(self):
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(8, 0),
            end_time=time(14, 0),
        )

        self.assertTrue(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.TUESDAY,
                time(8, 0),
                time(8, 40),
            )
        )

    def test_period_starting_inside_but_ending_after_availability_is_rejected(self):
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(8, 0),
            end_time=time(14, 0),
        )

        self.assertFalse(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.TUESDAY,
                time(13, 40),
                time(14, 20),
            )
        )

    def test_period_starting_at_availability_end_is_rejected(self):
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(8, 0),
            end_time=time(14, 0),
        )

        self.assertFalse(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.TUESDAY,
                time(14, 0),
                time(14, 40),
            )
        )

    def test_period_on_wrong_day_is_rejected(self):
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(8, 0),
            end_time=time(14, 0),
        )

        self.assertFalse(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.WEDNESDAY,
                time(8, 0),
                time(8, 40),
            )
        )

    def test_multiple_windows_on_same_day_are_supported(self):
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.MONDAY,
            start_time=time(8, 0),
            end_time=time(12, 0),
        )

        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.MONDAY,
            start_time=time(13, 0),
            end_time=time(16, 0),
        )

        self.assertTrue(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.MONDAY,
                time(13, 20),
                time(14, 0),
            )
        )

    def test_period_between_availability_windows_is_rejected(self):
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.MONDAY,
            start_time=time(8, 0),
            end_time=time(12, 0),
        )

        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.MONDAY,
            start_time=time(13, 0),
            end_time=time(16, 0),
        )

        self.assertFalse(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.MONDAY,
                time(12, 20),
                time(13, 0),
            )
        )

    def test_invalid_requested_period_is_rejected(self):
        self.assertFalse(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.TUESDAY,
                time(14, 0),
                time(8, 0),
            )
        )

        self.assertFalse(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.TUESDAY,
                time(8, 0),
                time(8, 0),
            )
        )

    def test_different_teacher_availability_does_not_match(self):
        other_teacher_user = User.objects.create_user(
            username="availability_helper_other",
            password="testpass123",
        )
        other_teacher_user.school = self.school
        other_teacher_user.save()

        other_teacher = Teacher.objects.create(
            user=other_teacher_user,
        )

        TeacherAvailability.objects.create(
            teacher=other_teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(8, 0),
            end_time=time(14, 0),
        )

        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.MONDAY,
            start_time=time(8, 0),
            end_time=time(14, 0),
        )

        self.assertFalse(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.TUESDAY,
                time(8, 0),
                time(8, 40),
            )
        )
        
    def test_teacher_without_availability_is_treated_as_full_time(self):
        self.assertTrue(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.MONDAY,
                time(8, 0),
                time(8, 40),
            )
        )


    def test_teacher_with_availability_must_fit_inside_window(self):
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(8, 0),
            end_time=time(12, 0),
        )

        self.assertTrue(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.TUESDAY,
                time(9, 0),
                time(9, 40),
            )
        )

        self.assertFalse(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.TUESDAY,
                time(12, 0),
                time(12, 40),
            )
        )

        self.assertFalse(
            teacher_is_available(
                self.teacher,
                TeacherAvailability.Day.MONDAY,
                time(8, 0),
                time(8, 40),
            )
        )
        
class TimetableGeneratorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            name="Generator Test School",
            code="GTS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.other_school = School.objects.create(
            name="Other Generator School",
            code="OGS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.user = User.objects.create_user(
            username="generator_test_user",
            password="testpass123",
        )
        cls.user.school = cls.school
        cls.user.save()

        cls.other_user = User.objects.create_user(
            username="other_generator_user",
            password="testpass123",
        )
        cls.other_user.school = cls.other_school
        cls.other_user.save()

        cls.session = AcademicSession.objects.create(
            school=cls.school,
            name="2026/2027",
            is_current=True,
        )

        cls.other_session = AcademicSession.objects.create(
            school=cls.other_school,
            name="2026/2027",
            is_current=True,
        )

        cls.term = Term.objects.create(
            session=cls.session,
            name=Term.TermName.FIRST,
        )

        cls.other_term = Term.objects.create(
            session=cls.other_session,
            name=Term.TermName.FIRST,
        )

        cls.school_class = SchoolClass.objects.create(
            school=cls.school,
            name="JSS 1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=True,
        )

        cls.second_class = SchoolClass.objects.create(
            school=cls.school,
            name="JSS 2",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=True,
        )

        cls.inactive_class = SchoolClass.objects.create(
            school=cls.school,
            name="JSS 3",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=False,
        )

        cls.other_class = SchoolClass.objects.create(
            school=cls.other_school,
            name="JSS 1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=True,
        )

        cls.subject = Subject.objects.create(
            school=cls.school,
            name="Mathematics",
            code="GMATH",
            level=Subject.SubjectLevel.SECONDARY,
        )

        cls.second_subject = Subject.objects.create(
            school=cls.school,
            name="English",
            code="GEN",
            level=Subject.SubjectLevel.SECONDARY,
        )

        cls.other_subject = Subject.objects.create(
            school=cls.other_school,
            name="Mathematics",
            code="OMATH",
            level=Subject.SubjectLevel.SECONDARY,
        )

        cls.teacher_user = User.objects.create_user(
            username="generator_teacher",
            password="testpass123",
        )
        cls.teacher_user.school = cls.school
        cls.teacher_user.save()

        cls.teacher = Teacher.objects.create(
            user=cls.teacher_user,
        )

        cls.second_teacher_user = User.objects.create_user(
            username="generator_second_teacher",
            password="testpass123",
        )
        cls.second_teacher_user.school = cls.school
        cls.second_teacher_user.save()

        cls.second_teacher = Teacher.objects.create(
            user=cls.second_teacher_user,
        )

        cls.other_teacher_user = User.objects.create_user(
            username="other_generator_teacher",
            password="testpass123",
        )
        cls.other_teacher_user.school = cls.other_school
        cls.other_teacher_user.save()

        cls.other_teacher = Teacher.objects.create(
            user=cls.other_teacher_user,
        )

    def create_timetable(self, name="Generator Timetable"):
        return Timetable.objects.create(
            school=self.school,
            term=self.term,
            name=name,
            days=[
                TimetableEntry.Day.MONDAY,
                TimetableEntry.Day.TUESDAY,
                TimetableEntry.Day.WEDNESDAY,
                TimetableEntry.Day.THURSDAY,
                TimetableEntry.Day.FRIDAY,
                TimetableEntry.Day.SATURDAY,
            ],
            created_by=self.user,
        )

    def create_period(
        self,
        timetable,
        number,
        name,
        start,
        end,
        is_break=False,
        is_active=True,
    ):
        return TimetablePeriod.objects.create(
            timetable=timetable,
            name=name,
            period_number=number,
            start_time=start,
            end_time=end,
            is_break=is_break,
            is_active=is_active,
        )

    def create_standard_periods(self, timetable):
        self.create_period(
            timetable,
            1,
            "Period 1",
            time(8, 0),
            time(8, 40),
        )

        self.create_period(
            timetable,
            2,
            "Break",
            time(8, 40),
            time(9, 0),
            is_break=True,
        )

        self.create_period(
            timetable,
            3,
            "Period 2",
            time(9, 0),
            time(9, 40),
        )

        self.create_period(
            timetable,
            4,
            "Period 3",
            time(9, 40),
            time(10, 20),
        )

    def create_availability(
        self,
        teacher,
        day=TeacherAvailability.Day.MONDAY,
        start=time(8, 0),
        end=time(14, 0),
    ):
        return TeacherAvailability.objects.create(
            teacher=teacher,
            day=day,
            start_time=start,
            end_time=end,
        )

    def create_allocation(
        self,
        teacher=None,
        subject=None,
        school_class=None,
        term=None,
    ):
        return SubjectAllocation.objects.create(
            teacher=teacher or self.teacher,
            subject=subject or self.subject,
            school_class=school_class or self.school_class,
            term=term or self.term,
        )

    def create_requirement(
        self,
        timetable,
        allocation=None,
        lessons_per_week=1,
        double_periods=0,
    ):
        return TimetableRequirement.objects.create(
            timetable=timetable,
            allocation=allocation or self.create_allocation(),
            lessons_per_week=lessons_per_week,
            double_periods=double_periods,
        )

    def test_generates_a_valid_timetable(self):
        timetable = self.create_timetable()
        self.create_standard_periods(timetable)
        self.create_availability(self.teacher)

        requirement = self.create_requirement(
            timetable,
            lessons_per_week=1,
        )

        entries = generate_timetable(
            timetable,
            self.school,
        )

        self.assertEqual(len(entries), 1)

        self.assertEqual(
            TimetableEntry.objects.filter(
                timetable=timetable,
                requirement=requirement,
            ).count(),
            1,
        )
        
    def test_generator_uses_only_configured_timetable_days(self):
        timetable = self.create_timetable()
        timetable.days = [
            TimetableEntry.Day.MONDAY,
            TimetableEntry.Day.TUESDAY,
        ]
        timetable.save()

        self.create_standard_periods(timetable)
        self.create_availability(
            self.teacher,
            day=TeacherAvailability.Day.MONDAY,
        )
        self.create_availability(
            self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
        )

        requirement = self.create_requirement(
            timetable,
            lessons_per_week=2,
        )

        generate_timetable(
            timetable,
            self.school,
        )

        entries = TimetableEntry.objects.filter(
            timetable=timetable,
            requirement=requirement,
        )

        self.assertEqual(entries.count(), 2)

        configured_days = {
            TimetableEntry.Day.MONDAY,
            TimetableEntry.Day.TUESDAY,
        }

        for entry in entries:
            self.assertIn(entry.day, configured_days)

    def test_generated_entry_count_matches_required_lesson_frequency(self):
        timetable = self.create_timetable()
        self.create_standard_periods(timetable)
        self.create_availability(self.teacher)
        self.create_availability(
            self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
        )

        requirement = self.create_requirement(
            timetable,
            lessons_per_week=4,
        )

        entries = generate_timetable(
            timetable,
            self.school,
        )

        self.assertEqual(len(entries), 4)

        self.assertEqual(
            TimetableEntry.objects.filter(
                timetable=timetable,
                requirement=requirement,
            ).count(),
            requirement.lessons_per_week,
        )

    def test_double_period_generates_two_consecutive_entries(self):
        timetable = self.create_timetable()
        self.create_standard_periods(timetable)
        self.create_availability(self.teacher)

        requirement = self.create_requirement(
            timetable,
            lessons_per_week=2,
            double_periods=1,
        )

        generate_timetable(
            timetable,
            self.school,
        )

        entries = list(
            TimetableEntry.objects.filter(
                timetable=timetable,
                requirement=requirement,
            ).select_related("period")
        )

        self.assertEqual(len(entries), 2)

        self.assertEqual(
            entries[0].day,
            entries[1].day,
        )

        period_numbers = sorted(
            entry.period.period_number
            for entry in entries
        )

        self.assertEqual(
            period_numbers[1],
            period_numbers[0] + 1,
        )

    def test_break_period_is_never_used(self):
        timetable = self.create_timetable()
        self.create_standard_periods(timetable)
        self.create_availability(self.teacher)

        requirement = self.create_requirement(
            timetable,
            lessons_per_week=3,
        )

        generate_timetable(
            timetable,
            self.school,
        )

        entries = TimetableEntry.objects.filter(
            timetable=timetable,
            requirement=requirement,
        ).select_related("period")

        self.assertEqual(entries.count(), 3)

        self.assertFalse(
            entries.filter(period__is_break=True).exists()
        )

    def test_teacher_availability_is_respected(self):
        timetable = self.create_timetable()

        self.create_period(
            timetable,
            1,
            "Period 1",
            time(8, 0),
            time(8, 40),
        )

        self.create_availability(
            self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start=time(8, 0),
            end=time(14, 0),
        )

        requirement = self.create_requirement(
            timetable,
            lessons_per_week=1,
        )

        generate_timetable(
            timetable,
            self.school,
        )

        entry = TimetableEntry.objects.get(
            timetable=timetable,
            requirement=requirement,
        )

        self.assertEqual(
            entry.day,
            TeacherAvailability.Day.TUESDAY,
        )

    def test_unavailable_teacher_causes_generation_to_fail(self):
        timetable = self.create_timetable()

        self.create_period(
            timetable,
            1,
            "Period 1",
            time(8, 0),
            time(8, 40),
        )

        self.create_requirement(
            timetable,
            lessons_per_week=1,
        )
        
        TeacherAvailability.objects.create(
            teacher=self.teacher,
            day=TeacherAvailability.Day.TUESDAY,
            start_time=time(9, 0),
            end_time=time(14, 0),
        )

        with self.assertRaises(TimetableGenerationError):
            generate_timetable(
                timetable,
                self.school,
            )

        self.assertEqual(
            timetable.entries.count(),
            0,
        )

    def test_class_conflict_is_prevented(self):
        timetable = self.create_timetable()

        self.create_period(
            timetable,
            1,
            "Period 1",
            time(8, 0),
            time(8, 40),
        )

        self.create_availability(self.teacher)
        self.create_availability(self.second_teacher)

        allocation_one = self.create_allocation(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
        )

        allocation_two = self.create_allocation(
            teacher=self.second_teacher,
            subject=self.second_subject,
            school_class=self.school_class,
        )

        requirement_one = self.create_requirement(
            timetable,
            allocation=allocation_one,
            lessons_per_week=1,
        )

        requirement_two = self.create_requirement(
            timetable,
            allocation=allocation_two,
            lessons_per_week=1,
        )

        with self.assertRaises(TimetableGenerationError):
            generate_timetable(
                timetable,
                self.school,
            )

        self.assertEqual(
            TimetableEntry.objects.filter(
                timetable=timetable,
            ).count(),
            0,
        )

        self.assertEqual(
            requirement_one.entries.count(),
            0,
        )

        self.assertEqual(
            requirement_two.entries.count(),
            0,
        )

    def test_teacher_conflict_is_prevented(self):
        timetable = self.create_timetable()

        self.create_period(
            timetable,
            1,
            "Period 1",
            time(8, 0),
            time(8, 40),
        )

        self.create_availability(self.teacher)

        allocation_one = self.create_allocation(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
        )

        allocation_two = self.create_allocation(
            teacher=self.teacher,
            subject=self.second_subject,
            school_class=self.second_class,
        )

        requirement_one = self.create_requirement(
            timetable,
            allocation=allocation_one,
            lessons_per_week=1,
        )

        requirement_two = self.create_requirement(
            timetable,
            allocation=allocation_two,
            lessons_per_week=1,
        )

        with self.assertRaises(TimetableGenerationError):
            generate_timetable(
                timetable,
                self.school,
            )

        self.assertEqual(
            TimetableEntry.objects.filter(
                timetable=timetable,
            ).count(),
            0,
        )

        self.assertEqual(
            requirement_one.entries.count(),
            0,
        )

        self.assertEqual(
            requirement_two.entries.count(),
            0,
        )

    def test_inactive_class_is_excluded_from_generation(self):
        timetable = self.create_timetable()
        self.create_standard_periods(timetable)
        self.create_availability(self.teacher)

        inactive_allocation = self.create_allocation(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.inactive_class,
        )

        inactive_requirement = self.create_requirement(
            timetable,
            allocation=inactive_allocation,
            lessons_per_week=2,
        )

        generate_timetable(
            timetable,
            self.school,
        )

        self.assertEqual(
            inactive_requirement.entries.count(),
            0,
        )

        self.assertEqual(
            timetable.entries.count(),
            0,
        )

    def test_wrong_school_requirement_is_rejected(self):
        timetable = self.create_timetable()
        self.create_standard_periods(timetable)

        other_allocation = self.create_allocation(
            teacher=self.other_teacher,
            subject=self.other_subject,
            school_class=self.other_class,
            term=self.other_term,
        )

        TimetableRequirement.objects.bulk_create(
            [
                TimetableRequirement(
                    timetable=timetable,
                    allocation=other_allocation,
                    lessons_per_week=1,
                )
            ]
        )

        with self.assertRaises(TimetableGenerationError):
            generate_timetable(
                timetable,
                self.school,
            )

        self.assertEqual(
            timetable.entries.count(),
            0,
        )

    def test_wrong_term_requirement_is_rejected(self):
        timetable = self.create_timetable()
        self.create_standard_periods(timetable)
        self.create_availability(self.teacher)

        second_term = Term.objects.create(
            session=self.session,
            name=Term.TermName.SECOND,
        )

        other_term_allocation = self.create_allocation(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
            term=second_term,
        )

        TimetableRequirement.objects.bulk_create(
            [
                TimetableRequirement(
                    timetable=timetable,
                    allocation=other_term_allocation,
                    lessons_per_week=1,
                )
            ]
        )

        with self.assertRaises(TimetableGenerationError):
            generate_timetable(
                timetable,
                self.school,
            )

        self.assertEqual(
            timetable.entries.count(),
            0,
        )

    def test_impossible_schedule_fails_without_partial_entries(self):
        timetable = self.create_timetable()

        self.create_period(
            timetable,
            1,
            "Period 1",
            time(8, 0),
            time(8, 40),
        )

        self.create_availability(self.teacher)
        self.create_availability(self.second_teacher)

        allocation_one = self.create_allocation(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
        )

        allocation_two = self.create_allocation(
            teacher=self.second_teacher,
            subject=self.second_subject,
            school_class=self.school_class,
        )

        self.create_requirement(
            timetable,
            allocation=allocation_one,
            lessons_per_week=1,
        )

        self.create_requirement(
            timetable,
            allocation=allocation_two,
            lessons_per_week=1,
        )

        with self.assertRaises(TimetableGenerationError):
            generate_timetable(
                timetable,
                self.school,
            )

        self.assertEqual(
            timetable.entries.count(),
            0,
        )

    def test_existing_entries_prevent_accidental_overwrite(self):
        timetable = self.create_timetable()

        period = self.create_period(
            timetable,
            1,
            "Period 1",
            time(8, 0),
            time(8, 40),
        )

        self.create_availability(self.teacher)

        requirement = self.create_requirement(
            timetable,
            lessons_per_week=1,
        )

        TimetableEntry.objects.create(
            timetable=timetable,
            requirement=requirement,
            day=TimetableEntry.Day.MONDAY,
            period=period,
        )

        with self.assertRaises(TimetableGenerationError):
            generate_timetable(
                timetable,
                self.school,
            )

        self.assertEqual(
            timetable.entries.count(),
            1,
        )

class TimetableViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            name="Timetable View Test School",
            code="TVTS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )
        
        cls.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.BASIC,
        )

        SchoolSubscription.objects.create(
            school=cls.school,
            package=cls.package,
            start_date=timezone.now().date(),
        )

        cls.user = User.objects.create_superuser(
            username="timetable_view_user",
            password="testpass123",
            email="timetableview@example.com",
        )
        
        cls.user.school = cls.school
        cls.user.save()

        cls.role = SchoolRole.objects.create(
            school=cls.school,
            name="Timetable Test Administrator",
            base_role=SchoolRole.BaseRole.ADMIN,
        )

        cls.permission = Permission.objects.create(
            code="timetable.view",
            name="View Timetable",
            description="View school timetables.",
            module="Timetable",
            is_active=True,
        )

        cls.role.permissions.add(cls.permission)

        cls.user.school_role = cls.role
        cls.user.save()

        cls.session = AcademicSession.objects.create(
            school=cls.school,
            name="2026/2027",
            is_current=True,
        )

        cls.term = Term.objects.create(
            session=cls.session,
            name=Term.TermName.FIRST,
        )

        cls.school_class = SchoolClass.objects.create(
            school=cls.school,
            name="JSS 1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
        )

        cls.subject = Subject.objects.create(
            school=cls.school,
            name="Mathematics",
            code="MATH",
            level=Subject.SubjectLevel.SECONDARY,
        )

        cls.teacher_user = User.objects.create_user(
            username="timetable_view_teacher",
            password="testpass123",
        )
        cls.teacher_user.school = cls.school
        cls.teacher_user.save()

        cls.teacher = Teacher.objects.create(
            user=cls.teacher_user,
        )

        cls.allocation = SubjectAllocation.objects.create(
            teacher=cls.teacher,
            subject=cls.subject,
            school_class=cls.school_class,
            term=cls.term,
        )

        cls.timetable = Timetable.objects.create(
            school=cls.school,
            term=cls.term,
            name="View Test Timetable",
            days=[
                TimetableEntry.Day.MONDAY,
                TimetableEntry.Day.TUESDAY,
            ],
            created_by=cls.user,
        )

    def test_timetable_view_uses_days_as_rows_and_periods_as_columns(self):
        self.client.force_login(self.user)

        period_one = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Period 1",
            period_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        period_two = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Period 2",
            period_number=2,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        requirement = TimetableRequirement.objects.create(
            timetable=self.timetable,
            allocation=self.allocation,
            lessons_per_week=1,
        )

        monday_entry = TimetableEntry.objects.create(
            timetable=self.timetable,
            requirement=requirement,
            day=TimetableEntry.Day.MONDAY,
            period=period_one,
        )

        response = self.client.get(
            reverse(
                "timetable_view",
                args=[self.timetable.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.context["grid"][0]["day"],
            TimetableEntry.Day.MONDAY,
        )

        self.assertEqual(
            response.context["grid"][1]["day"],
            TimetableEntry.Day.TUESDAY,
        )

        self.assertEqual(
            response.context["grid"][0]["cells"][0]["period"],
            period_one,
        )

        self.assertEqual(
            response.context["grid"][0]["cells"][1]["period"],
            period_two,
        )

        self.assertEqual(
            response.context["grid"][0]["cells"][0]["entry"],
            [monday_entry],
        )

        self.assertIsNone(
            response.context["grid"][1]["cells"][0]["entry"],
        )

        self.assertEqual(
            len(response.context["grid"]),
            2,
        )

        self.assertEqual(
            len(response.context["grid"][0]["cells"]),
            2,
        )
        
    def test_timetable_view_filters_by_section_and_class(self):
        self.client.force_login(self.user)

        period = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Period 1",
            period_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        second_class = SchoolClass.objects.create(
            school=self.school,
            name="SS 1",
            section=SchoolClass.Section.SENIOR_SECONDARY,
        )

        second_subject = Subject.objects.create(
            school=self.school,
            name="English",
            code="ENG",
            level=Subject.SubjectLevel.SECONDARY,
        )

        second_allocation = SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=second_subject,
            school_class=second_class,
            term=self.term,
        )

        first_requirement = TimetableRequirement.objects.create(
            timetable=self.timetable,
            allocation=self.allocation,
            lessons_per_week=1,
        )

        second_requirement = TimetableRequirement.objects.create(
            timetable=self.timetable,
            allocation=second_allocation,
            lessons_per_week=1,
        )

        first_entry = TimetableEntry.objects.create(
            timetable=self.timetable,
            requirement=first_requirement,
            day=TimetableEntry.Day.MONDAY,
            period=period,
        )

        second_entry = TimetableEntry.objects.create(
            timetable=self.timetable,
            requirement=second_requirement,
            day=TimetableEntry.Day.TUESDAY,
            period=period,
        )

        response = self.client.get(
            reverse(
                "timetable_view",
                args=[self.timetable.id],
            ),
            {
                "section": SchoolClass.Section.JUNIOR_SECONDARY,
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.context["grid"][0]["cells"][0]["entry"],
            [first_entry],
        )

        self.assertIsNone(
            response.context["grid"][1]["cells"][0]["entry"],
        )

        response = self.client.get(
            reverse(
                "timetable_view",
                args=[self.timetable.id],
            ),
            {
                "section": SchoolClass.Section.SENIOR_SECONDARY,
                "class": second_class.id,
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertIsNone(
            response.context["grid"][0]["cells"][0]["entry"],
        )

        self.assertEqual(
            response.context["grid"][1]["cells"][0]["entry"],
            [second_entry],
        )