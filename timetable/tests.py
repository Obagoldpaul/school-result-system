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
from students.models import SchoolClass, Student
from allocations.models import SubjectAllocation
from schools.models import (
    Feature,
    School,
    SchoolRole,
    Permission,
    SchoolSubscription, 
    SubscriptionPackage,
)

from subjects.models import Subject
from teachers.models import Teacher

from .models import (
    Timetable,
    TimetableEntry,
    TimetablePeriod,
    TimetablePeriodTemplate,
    TimetablePeriodTemplateBlock,
    TimetablePeriodTemplateDay,
    TimetableRequirement,
    TeacherAvailability,
)
from .forms import (
    TimetableForm,
    TimetablePeriodForm,
    TimetablePeriodTemplateBlockForm,
    TimetablePeriodTemplateDayForm,
    TimetablePeriodTemplateForm,
    TimetableRequirementForm,
    TeacherAvailabilityForm,
)

from .services import (
    sync_timetable_requirements,
    apply_timetable_period_template,
)

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
            day=TimetableEntry.Day.MONDAY,
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
            day=TimetableEntry.Day.MONDAY,
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
            day=TimetableEntry.Day.MONDAY,
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
            day=TimetableEntry.Day.MONDAY,
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
            day=TimetableEntry.Day.MONDAY,
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
        

class TimetablePeriodTemplateModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            name="Template Test School",
            code="TPS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.other_school = School.objects.create(
            name="Other Template School",
            code="OTS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

    def test_multiple_templates_can_exist_for_same_school(self):
        normal = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )
        friday = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Friday Short Day",
        )

        self.assertEqual(
            TimetablePeriodTemplate.objects.filter(
                school=self.school
            ).count(),
            2,
        )
        self.assertNotEqual(normal.pk, friday.pk)

    def test_template_name_must_be_unique_within_same_school(self):
        TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )

        duplicate = TimetablePeriodTemplate(
            school=self.school,
            name="Normal School Day",
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_same_template_name_can_exist_in_different_schools(self):
        first = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )
        second = TimetablePeriodTemplate.objects.create(
            school=self.other_school,
            name="Normal School Day",
        )

        self.assertEqual(first.name, second.name)
        self.assertNotEqual(first.school_id, second.school_id)

    def test_school_cannot_have_two_default_templates(self):
        TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
            is_default=True,
        )

        duplicate_default = TimetablePeriodTemplate(
            school=self.school,
            name="Friday Short Day",
            is_default=True,
        )

        with self.assertRaises(ValidationError):
            duplicate_default.validate_constraints()

    def test_template_can_have_monday_and_friday_structures(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )

        monday = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )
        friday = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.FRIDAY,
        )

        self.assertEqual(template.days.count(), 2)
        self.assertEqual(monday.day, TimetablePeriodTemplateDay.Day.MONDAY)
        self.assertEqual(friday.day, TimetablePeriodTemplateDay.Day.FRIDAY)

    def test_template_cannot_have_duplicate_day(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )

        TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        duplicate = TimetablePeriodTemplateDay(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        with self.assertRaises(ValidationError):
            duplicate.validate_constraints()

    def test_block_numbers_cannot_duplicate_within_same_template_day(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )
        day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Period 1",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        duplicate = TimetablePeriodTemplateBlock(
            day=day,
            name="Another Period",
            block_number=1,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        with self.assertRaises(ValidationError):
            duplicate.validate_constraints()

    def test_activity_block_is_valid(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )
        day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        block = TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Fellowship",
            block_number=4,
            start_time=time(12, 0),
            end_time=time(13, 0),
            block_type=TimetablePeriodTemplateBlock.BlockType.ACTIVITY,
            description="Whole-school Fellowship",
        )

        self.assertEqual(
            block.block_type,
            TimetablePeriodTemplateBlock.BlockType.ACTIVITY,
        )
        self.assertEqual(block.name, "Fellowship")

    def test_block_rejects_invalid_time_range(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )
        day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        block = TimetablePeriodTemplateBlock(
            day=day,
            name="Invalid Period",
            block_number=1,
            start_time=time(10, 0),
            end_time=time(9, 0),
        )

        with self.assertRaises(ValidationError):
            block.full_clean()

    def test_active_blocks_cannot_overlap(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )
        day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Period 1",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        overlapping = TimetablePeriodTemplateBlock(
            day=day,
            name="Period 2",
            block_number=2,
            start_time=time(8, 30),
            end_time=time(9, 30),
        )

        with self.assertRaises(ValidationError):
            overlapping.full_clean()

    def test_non_overlapping_active_blocks_are_valid(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )
        day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Period 1",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        second = TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Period 2",
            block_number=2,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        self.assertIsNotNone(second.pk)

    def test_inactive_overlapping_block_does_not_block_active_block(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )
        day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Inactive Block",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            is_active=False,
        )

        active_block = TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Active Block",
            block_number=2,
            start_time=time(8, 30),
            end_time=time(9, 30),
            is_active=True,
        )

        self.assertTrue(active_block.is_active)

class TimetablePeriodTemplateViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            name="Template View School",
            code="TVS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.other_school = School.objects.create(
            name="Other Template View School",
            code="OTVS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.user = User.objects.create_user(
            username="template_view_user",
            password="testpass123",
        )
        cls.user.school = cls.school
        cls.user.save()

        cls.other_user = User.objects.create_user(
            username="other_template_view_user",
            password="testpass123",
        )
        cls.other_user.school = cls.other_school
        cls.other_user.save()

        cls.role = SchoolRole.objects.create(
            school=cls.school,
            name="Template View Administrator",
            base_role=SchoolRole.BaseRole.ADMIN,
        )

        cls.timetable_feature = Feature.objects.create(
            code="TIMETABLE",
            name="Timetable",
            description="School timetable management.",
            is_active=True,
        )
        
        cls.subscription_package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.BASIC,
        )

        cls.subscription_package.features.add(
            cls.timetable_feature,
        )

        cls.school_subscription = SchoolSubscription.objects.create(
            school=cls.school,
            package=cls.subscription_package,
            start_date=timezone.localdate(),
        )

        cls.create_permission = Permission.objects.create(
            code="timetable.create",
            name="Create Timetables",
            description="Create and manage school timetables.",
            module="Timetable",
            is_active=True,
        )

        cls.role.permissions.add(cls.create_permission)

        cls.user.school_role = cls.role
        cls.user.save()

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_period_templates_page(self):
        response = self.client.get(
            reverse("timetable_period_templates")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "timetable/period_templates.html",
        )

    def test_post_creates_template_for_current_school(self):
        response = self.client.post(
            reverse("timetable_period_templates"),
            {
                "name": "Normal School Day",
            },
        )

        self.assertRedirects(
            response,
            reverse("timetable_period_templates"),
        )

        template = TimetablePeriodTemplate.objects.get(
            name="Normal School Day"
        )

        self.assertEqual(template.school, self.school)

    def test_period_templates_are_isolated_by_school(self):
        own_template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="My School Template",
        )

        other_template = TimetablePeriodTemplate.objects.create(
            school=self.other_school,
            name="Other School Template",
        )

        response = self.client.get(
            reverse("timetable_period_templates")
        )

        self.assertEqual(response.status_code, 200)

        templates = response.context["templates"]

        self.assertIn(own_template, templates)
        self.assertNotIn(other_template, templates)

    def test_unauthenticated_user_cannot_access_period_templates(self):
        self.client.logout()

        response = self.client.get(
            reverse("timetable_period_templates")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
        
    def test_configure_view_creates_day_for_template(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )

        response = self.client.post(
            reverse(
                "timetable_period_template_configure",
                args=[template.id],
            ),
            {
                "action": "add_day",
                "day": TimetablePeriodTemplateDay.Day.MONDAY,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )
        self.assertEqual(
            response.url,
            reverse(
                "timetable_period_template_configure",
                args=[template.id],
            ),
        )

        day = TimetablePeriodTemplateDay.objects.get(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        self.assertEqual(day.template, template)
        
    def test_configure_view_creates_block_for_template_day(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )

        day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        response = self.client.post(
            reverse(
                "timetable_period_template_configure",
                args=[template.id],
            ),
            {
                "action": "add_block",
                "day_id": day.id,
                "name": "Period 1",
                "block_number": 1,
                "start_time": "08:00",
                "end_time": "08:40",
                "block_type": TimetablePeriodTemplateBlock.BlockType.TEACHING,
                "description": "",
                "is_active": "on",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )
        self.assertEqual(
            response.url,
            reverse(
                "timetable_period_template_configure",
                args=[template.id],
            ),
        )

        block = TimetablePeriodTemplateBlock.objects.get(
            day=day,
            block_number=1,
        )

        self.assertEqual(block.day, day)
        self.assertEqual(block.day.template, template)
        
    def test_configure_view_cannot_access_other_school_template(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.other_school,
            name="Other School Template",
        )

        response = self.client.get(
            reverse(
                "timetable_period_template_configure",
                args=[template.id],
            ),
        )

        self.assertEqual(response.status_code, 404)
        
    def test_configure_view_cannot_add_block_to_day_from_other_school(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )

        other_template = TimetablePeriodTemplate.objects.create(
            school=self.other_school,
            name="Other School Day",
        )

        other_day = TimetablePeriodTemplateDay.objects.create(
            template=other_template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        response = self.client.post(
            reverse(
                "timetable_period_template_configure",
                args=[template.id],
            ),
            {
                "action": "add_block",
                "day_id": other_day.id,
                "name": "Period 1",
                "block_number": 1,
                "start_time": "08:00",
                "end_time": "08:40",
                "block_type": TimetablePeriodTemplateBlock.BlockType.TEACHING,
                "description": "",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 404)
        
    def test_configure_view_get_renders_template(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )

        response = self.client.get(
            reverse(
                "timetable_period_template_configure",
                args=[template.id],
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "timetable/period_template_configure.html",
        )
        self.assertEqual(response.context["template"], template)
        
    def test_period_templates_page_links_to_configuration(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )

        response = self.client.get(
            reverse("timetable_period_templates"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse(
                "timetable_period_template_configure",
                args=[template.id],
            ),
        )
        
    def test_edit_period_template_block_updates_block(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )

        day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        block = TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Period 1",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(8, 40),
            block_type=TimetablePeriodTemplateBlock.BlockType.TEACHING,
        )

        response = self.client.post(
            reverse(
                "edit_timetable_period_template_block",
                args=[template.id, block.id],
            ),
            {
                "name": "Period 1 Updated",
                "block_number": 1,
                "start_time": "08:00",
                "end_time": "08:45",
                "block_type": TimetablePeriodTemplateBlock.BlockType.TEACHING,
                "description": "",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)

        block.refresh_from_db()

        self.assertEqual(block.name, "Period 1 Updated")
        self.assertEqual(block.end_time, time(8, 45))
        
    def test_delete_period_template_block_deletes_block(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
        )

        day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        block = TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Period 1",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(8, 40),
            block_type=TimetablePeriodTemplateBlock.BlockType.TEACHING,
        )

        response = self.client.post(
            reverse(
                "delete_timetable_period_template_block",
                args=[template.id, block.id],
            ),
        )

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            TimetablePeriodTemplateBlock.objects.filter(
                pk=block.id
            ).exists()
        )

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
        
        cls.timetable_feature = Feature.objects.create(
            code="TIMETABLE",
            name="Timetable",
            description="School timetable management.",
            is_active=True,
        )

        cls.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.STANDARD,
        )

        cls.package.features.add(cls.timetable_feature)

        SchoolSubscription.objects.create(
            school=cls.school,
            package=cls.package,
            start_date=timezone.now().date(),
        )

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
                "day": TimetableEntry.Day.MONDAY,
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
        
    def test_period_template_form_accepts_valid_template(self):
        form = TimetablePeriodTemplateForm(
            data={
                "name": "Normal School Day",
                "description": "Regular school timetable structure.",
                "is_default": True,
                "is_active": True,
            },
            school=self.school,
        )

        self.assertTrue(form.is_valid(), form.errors)
    
    def test_period_template_form_rejects_duplicate_name_for_same_school(self):
        TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
            description="Existing template.",
            is_default=True,
            is_active=True,
        )

        form = TimetablePeriodTemplateForm(
            data={
                "name": "Normal School Day",
                "description": "Another template with the same name.",
                "is_default": False,
                "is_active": True,
            },
            school=self.school,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        
    def test_apply_period_template_creates_periods_for_selected_days(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal School Day",
            is_active=True,
        )
        
        self.timetable.days = [
            TimetableEntry.Day.MONDAY,
            TimetableEntry.Day.TUESDAY,
        ]
        self.timetable.save()

        monday = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetableEntry.Day.MONDAY,
        )

        tuesday = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetableEntry.Day.TUESDAY,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=monday,
            name="Period 1",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            block_type=TimetablePeriodTemplateBlock.BlockType.TEACHING,
            is_active=True,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=tuesday,
            name="Period 1",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            block_type=TimetablePeriodTemplateBlock.BlockType.TEACHING,
            is_active=True,
        )

        apply_timetable_period_template(
            timetable=self.timetable,
            template=template,
        )

        periods = TimetablePeriod.objects.filter(
            timetable=self.timetable,
        ).order_by("day", "period_number")

        self.assertEqual(periods.count(), 2)

        monday_period = periods.get(
            day=TimetableEntry.Day.MONDAY,
        )
        self.assertEqual(monday_period.name, "Period 1")
        self.assertEqual(monday_period.period_number, 1)
        self.assertEqual(monday_period.start_time, time(8, 0))
        self.assertEqual(monday_period.end_time, time(9, 0))
        self.assertFalse(monday_period.is_break)
        self.assertTrue(monday_period.is_active)
        
    def test_apply_period_template_maps_block_types_correctly(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Mixed Day",
            is_active=True,
        )
        
        self.timetable.days = [
            TimetableEntry.Day.MONDAY,
        ]
        self.timetable.save()

        day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetableEntry.Day.MONDAY,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Teaching",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            block_type=TimetablePeriodTemplateBlock.BlockType.TEACHING,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Break",
            block_number=2,
            start_time=time(9, 0),
            end_time=time(9, 30),
            block_type=TimetablePeriodTemplateBlock.BlockType.BREAK,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Assembly",
            block_number=3,
            start_time=time(9, 30),
            end_time=time(10, 0),
            block_type=TimetablePeriodTemplateBlock.BlockType.ACTIVITY,
        )

        apply_timetable_period_template(
            timetable=self.timetable,
            template=template,
        )

        periods = TimetablePeriod.objects.filter(
            timetable=self.timetable,
        ).order_by("period_number")

        self.assertFalse(periods.get(period_number=1).is_break)
        self.assertTrue(periods.get(period_number=2).is_break)
        self.assertFalse(periods.get(period_number=3).is_break)
        self.assertEqual(
            periods.get(period_number=3).name,
            "Assembly",
        )
        
    def test_apply_period_template_excludes_inactive_blocks(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Active Blocks",
            is_active=True,
        )
        
        self.timetable.days = [
            TimetableEntry.Day.MONDAY,
        ]
        self.timetable.save()

        day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetableEntry.Day.MONDAY,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Period 1",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            is_active=True,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="Inactive Period",
            block_number=2,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_active=False,
        )

        apply_timetable_period_template(
            timetable=self.timetable,
            template=template,
        )

        periods = TimetablePeriod.objects.filter(
            timetable=self.timetable,
        )

        self.assertEqual(periods.count(), 1)
        self.assertEqual(periods.first().name, "Period 1")
        
    
    def test_apply_period_template_ignores_template_days_not_used_by_timetable(
        self,
    ):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Extended Week",
            is_active=True,
        )

        monday = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetableEntry.Day.MONDAY,
        )

        saturday = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetableEntry.Day.SATURDAY,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=monday,
            name="Monday Period",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=saturday,
            name="Saturday Period",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        self.timetable.days = [TimetableEntry.Day.MONDAY]
        self.timetable.save()

        apply_timetable_period_template(
            timetable=self.timetable,
            template=template,
        )

        periods = TimetablePeriod.objects.filter(
            timetable=self.timetable,
        )

        self.assertEqual(periods.count(), 1)
        self.assertEqual(
            periods.first().day,
            TimetableEntry.Day.MONDAY,
        )
        
    def test_apply_period_template_rejects_missing_selected_day_without_partial_periods(
        self,
    ):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Incomplete Template",
            is_active=True,
        )

        monday = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetableEntry.Day.MONDAY,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=monday,
            name="Monday Period",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        self.timetable.days = [
            TimetableEntry.Day.MONDAY,
            TimetableEntry.Day.TUESDAY,
        ]
        self.timetable.save()

        with self.assertRaises(ValidationError):
            apply_timetable_period_template(
                timetable=self.timetable,
                template=template,
            )

        self.assertEqual(
            TimetablePeriod.objects.filter(
                timetable=self.timetable,
            ).count(),
            0,
        )    
    
    def test_apply_period_template_rejects_timetable_with_existing_periods(
        self,
    ):
        TimetablePeriod.objects.create(
            timetable=self.timetable,
            day=TimetableEntry.Day.MONDAY,
            name="Existing Period",
            period_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Normal Day",
            is_active=True,
        )

        day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetableEntry.Day.MONDAY,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=day,
            name="New Period",
            block_number=1,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        with self.assertRaises(ValidationError):
            apply_timetable_period_template(
                timetable=self.timetable,
                template=template,
            )

        self.assertEqual(
            TimetablePeriod.objects.filter(
                timetable=self.timetable,
            ).count(),
            1,
        )

        self.assertEqual(
            TimetablePeriod.objects.get(
                timetable=self.timetable,
            ).name,
            "Existing Period",
        )
        
    def test_apply_period_template_rejects_template_from_another_school(
        self,
    ):
        template = TimetablePeriodTemplate.objects.create(
            school=self.other_school,
            name="Other School Template",
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            apply_timetable_period_template(
                timetable=self.timetable,
                template=template,
            )

        self.assertEqual(
            TimetablePeriod.objects.filter(
                timetable=self.timetable,
            ).count(),
            0,
        )
        
    def test_apply_period_template_rejects_inactive_template(self):
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Inactive Template",
            is_active=False,
        )

        with self.assertRaises(ValidationError):
            apply_timetable_period_template(
                timetable=self.timetable,
                template=template,
            )

        self.assertEqual(
            TimetablePeriod.objects.filter(
                timetable=self.timetable,
            ).count(),
            0,
        )
        
        
    def test_apply_period_template_view_creates_periods(self):
        self.client.force_login(self.user)
        self.timetable.days = [
            TimetablePeriodTemplateDay.Day.MONDAY,
        ]
        self.timetable.save()

        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Standard Template",
        )

        template_day = TimetablePeriodTemplateDay.objects.create(
            template=template,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
        )

        TimetablePeriodTemplateBlock.objects.create(
            day=template_day,
            name="Period 1",
            block_number=1,
            start_time=time(8, 0),
            end_time=time(8, 40),
            block_type=TimetablePeriodTemplateBlock.BlockType.TEACHING,
        )

        response = self.client.post(
            reverse(
                "apply_timetable_period_template",
                args=[self.timetable.id],
            ),
            {
                "template_id": template.id,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "timetable_periods",
                args=[self.timetable.id],
            ),
        )

        self.assertEqual(
            self.timetable.periods.count(),
            1,
        )


    def test_apply_period_template_view_rejects_template_from_another_school(self):
        self.client.force_login(self.user)
        template = TimetablePeriodTemplate.objects.create(
            school=self.other_school,
            name="Other School Template",
        )

        response = self.client.post(
            reverse(
                "apply_timetable_period_template",
                args=[self.timetable.id],
            ),
            {
                "template_id": template.id,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.timetable.periods.count(),
            0,
        )


    def test_apply_period_template_view_rejects_inactive_template(self):
        self.client.force_login(self.user)
        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Inactive Template",
            is_active=False,
        )

        response = self.client.post(
            reverse(
                "apply_timetable_period_template",
                args=[self.timetable.id],
            ),
            {
                "template_id": template.id,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "timetable_periods",
                args=[self.timetable.id],
            ),
        )

        self.assertEqual(
            self.timetable.periods.count(),
            0,
        )


    def test_apply_period_template_view_rejects_timetable_with_existing_periods(self):
        self.client.force_login(self.user)
        TimetablePeriod.objects.create(
            timetable=self.timetable,
            day=TimetablePeriodTemplateDay.Day.MONDAY,
            name="Existing Period",
            period_number=1,
            start_time=time(8, 0),
            end_time=time(8, 40),
        )

        template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Standard Template",
        )

        response = self.client.post(
            reverse(
                "apply_timetable_period_template",
                args=[self.timetable.id],
            ),
            {
                "template_id": template.id,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "timetable_periods",
                args=[self.timetable.id],
            ),
        )

        self.assertEqual(
            self.timetable.periods.count(),
            1,
        )


    def test_apply_period_template_view_redirects_on_get(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "apply_timetable_period_template",
                args=[self.timetable.id],
            ),
        )

        self.assertRedirects(
            response,
            reverse(
                "timetable_periods",
                args=[self.timetable.id],
            ),
        )
        
    def test_timetable_periods_view_shows_only_active_templates_for_current_school(self):
        self.client.force_login(self.user)

        active_template = TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Active Template",
            is_active=True,
        )

        TimetablePeriodTemplate.objects.create(
            school=self.school,
            name="Inactive Template",
            is_active=False,
        )

        TimetablePeriodTemplate.objects.create(
            school=self.other_school,
            name="Other School Template",
            is_active=True,
        )

        response = self.client.get(
            reverse(
                "timetable_periods",
                args=[self.timetable.id],
            ),
        )

        self.assertEqual(response.status_code, 200)

        templates = response.context["templates"]

        self.assertIn(active_template, templates)

        self.assertNotIn(
            TimetablePeriodTemplate.objects.get(
                school=self.school,
                name="Inactive Template",
            ),
            templates,
        )

        self.assertNotIn(
            TimetablePeriodTemplate.objects.get(
                school=self.other_school,
                name="Other School Template",
            ),
            templates,
        )
      
            
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
        day=TimetableEntry.Day.MONDAY,
    ):
        return TimetablePeriod.objects.create(
            timetable=timetable,
            name=name,
            period_number=number,
            start_time=start,
            end_time=end,
            is_break=is_break,
            is_active=is_active,
            day=day,
        )

    def create_standard_periods(self, timetable, day=TimetableEntry.Day.MONDAY):
        self.create_period(
            timetable,
            1,
            "Period 1",
            time(8, 0),
            time(8, 40),
            day=day,
        )
        self.create_period(
            timetable,
            2,
            "Break",
            time(8, 40),
            time(9, 0),
            is_break=True,
            day=day,
        )
        self.create_period(
            timetable,
            3,
            "Period 2",
            time(9, 0),
            time(9, 40),
            day=day,
        )
        self.create_period(
            timetable,
            4,
            "Period 3",
            time(9, 40),
            time(10, 20),
            day=day,
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
        self.create_standard_periods(
            timetable,
            day=TimetableEntry.Day.TUESDAY,
        )
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
            day=TimetableEntry.Day.TUESDAY,
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
        
        cls.timetable_feature = Feature.objects.create(
            code="TIMETABLE",
            name="Timetable",
            description="School timetable management.",
            is_active=True,
        )
        
        cls.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.STANDARD,
        )
        
        cls.package.features.add(cls.timetable_feature)

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
            day=TimetableEntry.Day.MONDAY,
        )

        period_two = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Period 2",
            period_number=2,
            start_time=time(9, 0),
            end_time=time(10, 0),
            day=TimetableEntry.Day.MONDAY,
        )
        
        period_three = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Tuesday Period 1",
            period_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            day=TimetableEntry.Day.TUESDAY,
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

        self.assertEqual(
            response.context["grid"][1]["cells"][0]["period"],
            period_three,
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

        self.assertEqual(
            len(response.context["grid"][1]["cells"]),
            1,
        )
        
    def test_timetable_view_filters_by_section_and_class(self):
        self.client.force_login(self.user)

        period = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Period 1",
            period_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            day=TimetableEntry.Day.MONDAY,
        )
        
        tuesday_period = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Tuesday Period 1",
            period_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            day=TimetableEntry.Day.TUESDAY,
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
            period=tuesday_period,
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
        

class TimetableApprovalViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            name="Timetable Approval School",
            code="TAS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.other_school = School.objects.create(
            name="Other Approval School",
            code="OAS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )
        
        cls.timetable_feature = Feature.objects.create(
            code="TIMETABLE",
            name="Timetable",
            description="School timetable management.",
            is_active=True,
        )

        cls.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.STANDARD,
        )
        
        cls.package.features.add(cls.timetable_feature)

        SchoolSubscription.objects.create(
            school=cls.school,
            package=cls.package,
            start_date=timezone.now().date(),
        )

        SchoolSubscription.objects.create(
            school=cls.other_school,
            package=cls.package,
            start_date=timezone.now().date(),
        )

        cls.user = User.objects.create_superuser(
            username="approval_user",
            password="testpass123",
            email="approval@example.com",
        )
        cls.user.school = cls.school
        cls.user.save()

        cls.other_user = User.objects.create_superuser(
            username="other_approval_user",
            password="testpass123",
            email="otherapproval@example.com",
        )
        cls.other_user.school = cls.other_school
        cls.other_user.save()

        cls.role = SchoolRole.objects.create(
            school=cls.school,
            name="Approval Administrator",
            base_role=SchoolRole.BaseRole.ADMIN,
        )

        cls.approve_permission = Permission.objects.create(
            code="timetable.approve",
            name="Approve Timetables",
            description="Approve generated timetables before publication.",
            module="Timetable",
            is_active=True,
        )

        cls.role.permissions.add(cls.approve_permission)

        cls.user.school_role = cls.role
        cls.user.save()

        cls.other_role = SchoolRole.objects.create(
            school=cls.other_school,
            name="Other Approval Administrator",
            base_role=SchoolRole.BaseRole.ADMIN,
        )

        cls.other_role.permissions.add(cls.approve_permission)

        cls.other_user.school_role = cls.other_role
        cls.other_user.save()

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
            code="TAMATH",
            level=Subject.SubjectLevel.SECONDARY,
        )

        cls.teacher_user = User.objects.create_user(
            username="approval_teacher",
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
            name="Approval Test Timetable",
            days=[
                TimetableEntry.Day.MONDAY,
                TimetableEntry.Day.TUESDAY,
            ],
            created_by=cls.user,
        )

    def create_generated_entry(self):
        period = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Period 1",
            period_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            day=TimetableEntry.Day.MONDAY,
        )

        requirement = TimetableRequirement.objects.create(
            timetable=self.timetable,
            allocation=self.allocation,
            lessons_per_week=1,
        )

        return TimetableEntry.objects.create(
            timetable=self.timetable,
            requirement=requirement,
            day=TimetableEntry.Day.MONDAY,
            period=period,
        )

    def test_user_with_approve_permission_can_approve_generated_draft(self):
        self.create_generated_entry()

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "approve_timetable",
                args=[self.timetable.id],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.timetable.refresh_from_db()

        self.assertEqual(
            self.timetable.status,
            Timetable.Status.APPROVED,
        )

    def test_approval_does_not_publish_timetable(self):
        self.create_generated_entry()

        self.client.force_login(self.user)

        self.client.post(
            reverse(
                "approve_timetable",
                args=[self.timetable.id],
            )
        )

        self.timetable.refresh_from_db()

        self.assertEqual(
            self.timetable.status,
            Timetable.Status.APPROVED,
        )
        self.assertNotEqual(
            self.timetable.status,
            Timetable.Status.PUBLISHED,
        )

    def test_timetable_without_entries_cannot_be_approved(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "approve_timetable",
                args=[self.timetable.id],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.timetable.refresh_from_db()

        self.assertEqual(
            self.timetable.status,
            Timetable.Status.DRAFT,
        )

    def test_already_approved_timetable_cannot_be_approved_again(self):
        self.create_generated_entry()

        self.timetable.status = Timetable.Status.APPROVED
        self.timetable.save()

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "approve_timetable",
                args=[self.timetable.id],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.timetable.refresh_from_db()

        self.assertEqual(
            self.timetable.status,
            Timetable.Status.APPROVED,
        )

    def test_user_from_another_school_cannot_approve_timetable(self):
        self.create_generated_entry()

        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse(
                "approve_timetable",
                args=[self.timetable.id],
            )
        )

        self.assertEqual(response.status_code, 404)

        self.timetable.refresh_from_db()

        self.assertEqual(
            self.timetable.status,
            Timetable.Status.DRAFT,
        )

    def test_user_without_approve_permission_is_denied(self):
        user = User.objects.create_user(
            username="no_approval_permission",
            password="testpass123",
        )
        user.school = self.school

        role = SchoolRole.objects.create(
            school=self.school,
            name="No Approval Role",
            base_role=SchoolRole.BaseRole.ADMIN,
        )

        user.school_role = role
        user.save()

        self.create_generated_entry()

        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "approve_timetable",
                args=[self.timetable.id],
            )
        )

        self.assertEqual(response.status_code, 403)

        self.timetable.refresh_from_db()

        self.assertEqual(
            self.timetable.status,
            Timetable.Status.DRAFT,
        )
        
class TimetablePublishViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            name="Timetable Publish School",
            code="TPS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        cls.other_school = School.objects.create(
            name="Other Publish School",
            code="OPS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )
        
        cls.timetable_feature = Feature.objects.create(
            code="TIMETABLE",
            name="Timetable",
            description="School timetable management.",
            is_active=True,
        )

        cls.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.STANDARD,
        )
        
        cls.package.features.add(cls.timetable_feature)

        SchoolSubscription.objects.create(
            school=cls.school,
            package=cls.package,
            start_date=timezone.now().date(),
        )

        SchoolSubscription.objects.create(
            school=cls.other_school,
            package=cls.package,
            start_date=timezone.now().date(),
        )

        cls.user = User.objects.create_superuser(
            username="publish_user",
            password="testpass123",
            email="publish@example.com",
        )
        cls.user.school = cls.school
        cls.user.save()

        cls.other_user = User.objects.create_superuser(
            username="other_publish_user",
            password="testpass123",
            email="otherpublish@example.com",
        )
        cls.other_user.school = cls.other_school
        cls.other_user.save()

        cls.role = SchoolRole.objects.create(
            school=cls.school,
            name="Publish Administrator",
            base_role=SchoolRole.BaseRole.ADMIN,
        )

        cls.publish_permission = Permission.objects.create(
            code="timetable.publish",
            name="Publish Timetables",
            description="Publish approved timetables.",
            module="Timetable",
            is_active=True,
        )
        
        cls.view_permission = Permission.objects.create(
            code="timetable.view",
            name="View Timetables",
            description="View Timetables",
            module="Timetable",
            is_active=True,
        )

        cls.role.permissions.add(
            cls.publish_permission,
            cls.view_permission,
        )

        cls.user.school_role = cls.role
        cls.user.save()

        cls.other_role = SchoolRole.objects.create(
            school=cls.other_school,
            name="Other Publish Administrator",
            base_role=SchoolRole.BaseRole.ADMIN,
        )

        cls.other_role.permissions.add(
            cls.publish_permission,
            cls.view_permission,
        )
        cls.other_user.school_role = cls.other_role
        cls.other_user.save()

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
            code="TPMATH",
            level=Subject.SubjectLevel.SECONDARY,
        )

        cls.teacher_user = User.objects.create_user(
            username="publish_teacher",
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
            name="Publish Test Timetable",
            days=[
                TimetableEntry.Day.MONDAY,
                TimetableEntry.Day.TUESDAY,
            ],
            status=Timetable.Status.APPROVED,
            created_by=cls.user,
        )

    def create_generated_entry(self):
        period = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Period 1",
            period_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            day=TimetableEntry.Day.MONDAY,
        )

        requirement = TimetableRequirement.objects.create(
            timetable=self.timetable,
            allocation=self.allocation,
            lessons_per_week=1,
        )

        return TimetableEntry.objects.create(
            timetable=self.timetable,
            requirement=requirement,
            day=TimetableEntry.Day.MONDAY,
            period=period,
        )

    def test_user_with_publish_permission_can_publish_approved_timetable(self):
        self.create_generated_entry()

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "publish_timetable",
                kwargs={"timetable_id": self.timetable.id},
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "timetable_view",
                kwargs={"timetable_id": self.timetable.id},
            ),
        )

        self.timetable.refresh_from_db()

        self.assertEqual(
            self.timetable.status,
            Timetable.Status.PUBLISHED,
        )

    def test_publishing_does_not_modify_timetable_entries(self):
        entry = self.create_generated_entry()

        self.client.force_login(self.user)

        self.client.post(
            reverse(
                "publish_timetable",
                kwargs={"timetable_id": self.timetable.id},
            )
        )

        self.assertTrue(
            TimetableEntry.objects.filter(
                id=entry.id,
                timetable=self.timetable,
            ).exists()
        )

    def test_draft_timetable_cannot_be_published(self):
        self.timetable.status = Timetable.Status.DRAFT
        self.timetable.save()

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "publish_timetable",
                kwargs={"timetable_id": self.timetable.id},
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "timetable_view",
                kwargs={"timetable_id": self.timetable.id},
            ),
        )

        self.timetable.refresh_from_db()

        self.assertEqual(
            self.timetable.status,
            Timetable.Status.DRAFT,
        )

    def test_published_timetable_cannot_be_published_again(self):
        self.timetable.status = Timetable.Status.PUBLISHED
        self.timetable.save()

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "publish_timetable",
                kwargs={"timetable_id": self.timetable.id},
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "timetable_view",
                kwargs={"timetable_id": self.timetable.id},
            ),
        )

        self.timetable.refresh_from_db()

        self.assertEqual(
            self.timetable.status,
            Timetable.Status.PUBLISHED,
        )

    def test_user_without_publish_permission_gets_403(self):
        user = User.objects.create_user(
            username="no_publish_user",
            password="testpass123",
        )
        user.school = self.school
        user.save()

        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "publish_timetable",
                kwargs={"timetable_id": self.timetable.id},
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_other_school_user_cannot_publish_timetable(self):
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse(
                "publish_timetable",
                kwargs={"timetable_id": self.timetable.id},
            )
        )

        self.assertEqual(response.status_code, 404)
        
class TimetablePortalViewTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Portal Test School",
            code="PTS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        self.other_school = School.objects.create(
            name="Other Portal School",
            code="OPS",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
        )

        self.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.BASIC,
        )

        SchoolSubscription.objects.create(
            school=self.school,
            package=self.package,
            start_date=timezone.now().date(),
        )

        SchoolSubscription.objects.create(
            school=self.other_school,
            package=self.package,
            start_date=timezone.now().date(),
        )
        
        self.timetable_feature = Feature.objects.create(
            code="TIMETABLE",
            name="Timetable",
        )

        self.student_portal_feature = Feature.objects.create(
            code="STUDENT_PORTAL",
            name="Student Portal",
        )

        self.package.features.add(
            self.timetable_feature,
            self.student_portal_feature,
        )

        # Current academic session / term for the main school.
        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2025/2026",
            is_current=True,
        )
        self.term = Term.objects.create(
            session=self.session,
            name=Term.TermName.FIRST,
            is_current=True,
        )

        # A non-current session / term.
        self.old_session = AcademicSession.objects.create(
            school=self.school,
            name="2024/2025",
            is_current=False,
        )
        self.old_term = Term.objects.create(
            session=self.old_session,
            name=Term.TermName.FIRST,
            is_current=False,
        )

        # Other school's current session / term.
        self.other_session = AcademicSession.objects.create(
            school=self.other_school,
            name="2025/2026",
            is_current=True,
        )
        self.other_term = Term.objects.create(
            session=self.other_session,
            name=Term.TermName.FIRST,
            is_current=True,
        )

        # Classes in the main school.
        self.own_class = SchoolClass.objects.create(
            school=self.school,
            name="JSS 1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=True,
        )
        self.other_class = SchoolClass.objects.create(
            school=self.school,
            name="JSS 2",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=True,
        )

        # Class in another school.
        self.other_school_class = SchoolClass.objects.create(
            school=self.other_school,
            name="JSS 1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=True,
        )

        # Users.
        self.teacher_user = User.objects.create_user(
            username="portal_teacher",
            password="testpass123",
        )
        self.teacher_user.school = self.school
        self.teacher_user.save()

        self.student_user = User.objects.create_user(
            username="portal_student",
            password="testpass123",
        )
        self.student_user.school = self.school
        self.student_user.save()

        self.other_student_user = User.objects.create_user(
            username="portal_other_student",
            password="testpass123",
        )
        self.other_student_user.school = self.school
        self.other_student_user.save()

        # Teacher profile.
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            assigned_class=self.own_class,
        )

        # Student profiles.
        self.student = Student.objects.create(
            user=self.student_user,
            school_class=self.own_class,
        )
        self.other_student = Student.objects.create(
            user=self.other_student_user,
            school_class=self.other_class,
        )

        # Subjects.
        self.math = Subject.objects.create(
            school=self.school,
            name="Mathematics",
            level=Subject.SubjectLevel.SECONDARY,
        )
        self.english = Subject.objects.create(
            school=self.school,
            name="English",
            code="TPENG",
            level=Subject.SubjectLevel.SECONDARY,
        )

        # Teachers for allocations.
        self.teacher_two_user = User.objects.create_user(
            username="portal_teacher_two",
            password="testpass123",
        )
        self.teacher_two_user.school = self.school
        self.teacher_two_user.save()

        self.teacher_two = Teacher.objects.create(
            user=self.teacher_two_user,
            assigned_class=self.other_class,
        )

        # Allocations for both classes.
        self.own_allocation = SubjectAllocation.objects.create(
            school_class=self.own_class,
            subject=self.math,
            teacher=self.teacher,
            term=self.term,
        )
        self.other_allocation = SubjectAllocation.objects.create(
            school_class=self.other_class,
            subject=self.english,
            teacher=self.teacher_two,
            term=self.term,
        )

        # Current published timetable.
        self.timetable = Timetable.objects.create(
            school=self.school,
            term=self.term,
            name="2025/2026 First Term Timetable",
            days=[
                TimetableEntry.Day.MONDAY,
                TimetableEntry.Day.TUESDAY,
            ],
            status=Timetable.Status.PUBLISHED,
        )

        self.period_one = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Period 1",
            period_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            is_break=False,
            is_active=True,
            day=TimetableEntry.Day.MONDAY,
        )

        self.period_two = TimetablePeriod.objects.create(
            timetable=self.timetable,
            name="Period 2",
            period_number=2,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_break=False,
            is_active=True,
            day=TimetableEntry.Day.MONDAY,
        )

        self.own_requirement = TimetableRequirement.objects.create(
            timetable=self.timetable,
            allocation=self.own_allocation,
            lessons_per_week=1,
        )

        self.other_requirement = TimetableRequirement.objects.create(
            timetable=self.timetable,
            allocation=self.other_allocation,
            lessons_per_week=1,
        )

        self.own_entry = TimetableEntry.objects.create(
            timetable=self.timetable,
            requirement=self.own_requirement,
            day=TimetableEntry.Day.MONDAY,
            period=self.period_one,
        )

        self.other_entry = TimetableEntry.objects.create(
            timetable=self.timetable,
            requirement=self.other_requirement,
            day=TimetableEntry.Day.MONDAY,
            period=self.period_two,
        )

        # Published timetable for the previous/non-current academic term.
        self.old_timetable = Timetable.objects.create(
            school=self.school,
            term=self.old_term,
            name="2024/2025 First Term Timetable",
            days=[TimetableEntry.Day.MONDAY],
            status=Timetable.Status.PUBLISHED,
        )

        old_period = TimetablePeriod.objects.create(
            timetable=self.old_timetable,
            name="Period 1",
            period_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            is_break=False,
            is_active=True,
            day=TimetableEntry.Day.MONDAY,
        )

        old_allocation = SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=self.math,
            school_class=self.own_class,
            term=self.old_term,
        )

        old_requirement = TimetableRequirement.objects.create(
            timetable=self.old_timetable,
            allocation=old_allocation,
            lessons_per_week=1,
        )

        TimetableEntry.objects.create(
            timetable=self.old_timetable,
            requirement=old_requirement,
            day=TimetableEntry.Day.MONDAY,
            period=old_period,
        )

        # Published timetable belonging to another school.
        other_subject = Subject.objects.create(
            school=self.other_school,
            name="Mathematics",
            code="OPMATH",
            level=Subject.SubjectLevel.SECONDARY,
        )

        other_teacher_user = User.objects.create_user(
            username="other_school_teacher",
            password="testpass123",
        )
        other_teacher_user.school = self.other_school
        other_teacher_user.save()

        other_teacher = Teacher.objects.create(
            user=other_teacher_user,
            assigned_class=self.other_school_class,
        )

        other_allocation = SubjectAllocation.objects.create(
            school_class=self.other_school_class,
            subject=other_subject,
            teacher=other_teacher,
            term=self.other_term,
        )

        self.other_timetable = Timetable.objects.create(
            school=self.other_school,
            term=self.other_term,
            name="Other School Timetable",
            days=[TimetableEntry.Day.MONDAY],
            status=Timetable.Status.PUBLISHED,
        )

        other_period = TimetablePeriod.objects.create(
            timetable=self.other_timetable,
            name="Period 1",
            period_number=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
            is_break=False,
            is_active=True,
            day=TimetableEntry.Day.MONDAY,
        )

        other_requirement = TimetableRequirement.objects.create(
            timetable=self.other_timetable,
            allocation=other_allocation,
            lessons_per_week=1,
        )

        TimetableEntry.objects.create(
            timetable=self.other_timetable,
            requirement=other_requirement,
            day=TimetableEntry.Day.MONDAY,
            period=other_period,
        )

    def _get_grid_entries(self, response):
        """
        Extract timetable entries from the expected portal grid context.
        """
        entries = []

        for row in response.context["grid"]:
            for cell in row["cells"]:
                cell_entries = cell.get("entry") or []
                if not isinstance(cell_entries, list):
                    cell_entries = [cell_entries]
                entries.extend(cell_entries)

        return entries

    def test_teacher_can_view_published_whole_school_timetable(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get(
            reverse("teacher_timetable")
        )

        self.assertEqual(response.status_code, 200)

        entries = self._get_grid_entries(response)
        entry_ids = {entry.id for entry in entries}

        self.assertIn(self.own_entry.id, entry_ids)
        self.assertIn(self.other_entry.id, entry_ids)

    def test_teacher_does_not_need_timetable_permission(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get(
            reverse("teacher_timetable")
        )

        self.assertEqual(response.status_code, 200)

    def test_teacher_cannot_view_draft_timetable(self):
        self.timetable.status = Timetable.Status.DRAFT
        self.timetable.save()

        self.client.force_login(self.teacher_user)

        response = self.client.get(
            reverse("teacher_timetable")
        )

        self.assertEqual(response.status_code, 404)

    def test_teacher_cannot_view_approved_timetable(self):
        self.timetable.status = Timetable.Status.APPROVED
        self.timetable.save()

        self.client.force_login(self.teacher_user)

        response = self.client.get(
            reverse("teacher_timetable")
        )

        self.assertEqual(response.status_code, 404)

    def test_teacher_cannot_view_other_school_timetable(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get(
            reverse("teacher_timetable")
        )

        self.assertEqual(response.status_code, 200)

        entries = self._get_grid_entries(response)

        other_school_entry_ids = set(
            self.other_timetable.entries.values_list("id", flat=True)
        )
        returned_entry_ids = {entry.id for entry in entries}

        self.assertTrue(
            returned_entry_ids.isdisjoint(other_school_entry_ids)
        )

    def test_student_can_view_only_own_class_timetable(self):
        self.client.force_login(self.student_user)

        response = self.client.get(
            reverse("student_timetable")
        )

        self.assertEqual(response.status_code, 200)

        entries = self._get_grid_entries(response)
        entry_ids = {entry.id for entry in entries}

        self.assertIn(self.own_entry.id, entry_ids)
        self.assertNotIn(self.other_entry.id, entry_ids)

    def test_student_timetable_is_server_side_filtered_to_own_class(self):
        self.client.force_login(self.student_user)

        response = self.client.get(
            reverse("student_timetable")
        )

        self.assertEqual(response.status_code, 200)

        entries = self._get_grid_entries(response)

        returned_class_ids = {
            entry.requirement.allocation.school_class_id
            for entry in entries
        }

        self.assertEqual(
            returned_class_ids,
            {self.own_class.id},
        )

    def test_student_cannot_view_draft_timetable(self):
        self.timetable.status = Timetable.Status.DRAFT
        self.timetable.save()

        self.client.force_login(self.student_user)

        response = self.client.get(
            reverse("student_timetable")
        )

        self.assertEqual(response.status_code, 404)

    def test_student_cannot_view_approved_timetable(self):
        self.timetable.status = Timetable.Status.APPROVED
        self.timetable.save()

        self.client.force_login(self.student_user)

        response = self.client.get(
            reverse("student_timetable")
        )

        self.assertEqual(response.status_code, 404)

    def test_student_cannot_view_other_school_timetable(self):
        self.student_user.school = self.school
        self.student_user.save()

        self.client.force_login(self.student_user)

        response = self.client.get(
            reverse("student_timetable")
        )

        self.assertEqual(response.status_code, 200)

        entries = self._get_grid_entries(response)

        other_school_entry_ids = set(
            self.other_timetable.entries.values_list("id", flat=True)
        )
        returned_entry_ids = {entry.id for entry in entries}

        self.assertTrue(
            returned_entry_ids.isdisjoint(other_school_entry_ids)
        )

    def test_student_cannot_view_non_current_term_timetable(self):
        self.client.force_login(self.student_user)

        response = self.client.get(
            reverse("student_timetable")
        )

        self.assertEqual(response.status_code, 200)

        entries = self._get_grid_entries(response)
        returned_entry_ids = {entry.id for entry in entries}

        old_entry_ids = set(
            self.old_timetable.entries.values_list("id", flat=True)
        )

        self.assertTrue(
            returned_entry_ids.isdisjoint(old_entry_ids)
        )