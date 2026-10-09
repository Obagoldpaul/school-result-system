from django.core.exceptions import ValidationError
from django.test import TestCase
from accounts.models import User
from allocations.models import SubjectAllocation
from library.forms import LessonNoteForm

from academics.models import AcademicSession, Term
from library.models import (
    Curriculum,
    CurriculumLevel,
    CurriculumSubject,
    CurriculumSubjectMapping,
    CurriculumTopic,
    LessonNote,
    SchemeOfWork,
    SchemeOfWorkItem,
)

from library.views import lesson_note_create

from accounts.utils import get_teacher

from library.forms import LessonNoteForm

from schools.models import School
from students.models import SchoolClass
from subjects.models import Subject
from teachers.models import Teacher


class SchemeOfWorkItemValidationTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
        )

        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
        )

        self.term = Term.objects.create(
            session=self.session,
            name=Term.TermName.FIRST,
        )

        self.school_class = SchoolClass.objects.create(
            school=self.school,
            name="JSS 1",
        )

        self.math_subject = Subject.objects.create(
            school=self.school,
            name="Mathematics",
            code="MATH",
        )

        self.english_subject = Subject.objects.create(
            school=self.school,
            name="English Language",
            code="ENG",
        )

        self.scheme = SchemeOfWork.objects.create(
            school=self.school,
            school_class=self.school_class,
            subject=self.math_subject,
            term=self.term,
            name="JSS 1 Mathematics Scheme",
        )

        self.curriculum = Curriculum.objects.create(
            name="Test Curriculum",
            provider="Test Provider",
            is_system=True,
        )

        self.level = CurriculumLevel.objects.create(
            curriculum=self.curriculum,
            name="Junior Secondary",
        )

        self.math_curriculum_subject = CurriculumSubject.objects.create(
            curriculum=self.curriculum,
            curriculum_level=self.level,
            name="Mathematics",
        )

        self.english_curriculum_subject = CurriculumSubject.objects.create(
            curriculum=self.curriculum,
            curriculum_level=self.level,
            name="English Language",
        )

        self.math_topic = CurriculumTopic.objects.create(
            curriculum_subject=self.math_curriculum_subject,
            title="Algebra",
        )

    def test_mapped_curriculum_topic_is_valid(self):
        CurriculumSubjectMapping.objects.create(
            curriculum_subject=self.math_curriculum_subject,
            subject=self.math_subject,
        )

        item = SchemeOfWorkItem(
            scheme_of_work=self.scheme,
            curriculum_topic=self.math_topic,
            title="Introduction to Algebra",
        )

        item.full_clean()

    def test_unmapped_curriculum_topic_raises_validation_error(self):
        item = SchemeOfWorkItem(
            scheme_of_work=self.scheme,
            curriculum_topic=self.math_topic,
            title="Introduction to Algebra",
        )

        with self.assertRaises(ValidationError):
            item.full_clean()
            
            
class SchemeOfWorkTenantValidationTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="School A",
            code="SCHOOL-A",
        )

        self.other_school = School.objects.create(
            name="School B",
            code="SCHOOL-B",
        )

        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
        )

        self.other_session = AcademicSession.objects.create(
            school=self.other_school,
            name="2026/2027",
        )

        self.term = Term.objects.create(
            session=self.session,
            name=Term.TermName.FIRST,
        )

        self.other_term = Term.objects.create(
            session=self.other_session,
            name=Term.TermName.FIRST,
        )

        self.school_class = SchoolClass.objects.create(
            school=self.school,
            name="JSS 1",
        )

        self.other_school_class = SchoolClass.objects.create(
            school=self.other_school,
            name="JSS 1",
        )

        self.subject = Subject.objects.create(
            school=self.school,
            name="Mathematics",
            code="MATH",
        )

        self.other_subject = Subject.objects.create(
            school=self.other_school,
            name="Mathematics",
            code="MATH",
        )

    def test_matching_school_relationships_are_valid(self):
        scheme = SchemeOfWork(
            school=self.school,
            school_class=self.school_class,
            subject=self.subject,
            term=self.term,
            name="JSS 1 Mathematics Scheme",
        )

        scheme.full_clean()

    def test_school_class_from_another_school_raises_validation_error(self):
        scheme = SchemeOfWork(
            school=self.school,
            school_class=self.other_school_class,
            subject=self.subject,
            term=self.term,
            name="JSS 1 Mathematics Scheme",
        )

        with self.assertRaises(ValidationError):
            scheme.full_clean()

    def test_subject_from_another_school_raises_validation_error(self):
        scheme = SchemeOfWork(
            school=self.school,
            school_class=self.school_class,
            subject=self.other_subject,
            term=self.term,
            name="JSS 1 Mathematics Scheme",
        )

        with self.assertRaises(ValidationError):
            scheme.full_clean()

    def test_term_from_another_school_raises_validation_error(self):
        scheme = SchemeOfWork(
            school=self.school,
            school_class=self.school_class,
            subject=self.subject,
            term=self.other_term,
            name="JSS 1 Mathematics Scheme",
        )

        with self.assertRaises(ValidationError):
            scheme.full_clean()
            
            
class LessonNoteTenantValidationTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="School A",
            code="SCHOOL-A",
        )

        self.other_school = School.objects.create(
            name="School B",
            code="SCHOOL-B",
        )

        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
        )

        self.term = Term.objects.create(
            session=self.session,
            name=Term.TermName.FIRST,
        )

        self.school_class = SchoolClass.objects.create(
            school=self.school,
            name="JSS 1",
        )

        self.subject = Subject.objects.create(
            school=self.school,
            name="Mathematics",
            code="MATH",
        )

        self.scheme = SchemeOfWork.objects.create(
            school=self.school,
            school_class=self.school_class,
            subject=self.subject,
            term=self.term,
            name="JSS 1 Mathematics Scheme",
        )

        self.scheme_item = SchemeOfWorkItem.objects.create(
            scheme_of_work=self.scheme,
            title="Introduction to Algebra",
        )

        self.user = User.objects.create_user(
            username="teacher_a",
            school=self.school,
            role=User.Role.TEACHER,
        )

        self.other_user = User.objects.create_user(
            username="teacher_b",
            school=self.other_school,
            role=User.Role.TEACHER,
        )

        self.teacher = Teacher.objects.create(
            user=self.user,
            staff_id="T001",
        )

        self.other_teacher = Teacher.objects.create(
            user=self.other_user,
            staff_id="T002",
        )

    def test_teacher_from_same_school_is_valid(self):
        lesson_note = LessonNote(
            scheme_item=self.scheme_item,
            teacher=self.teacher,
            title="Introduction to Algebra",
        )

        lesson_note.full_clean()

    def test_teacher_from_another_school_raises_validation_error(self):
        lesson_note = LessonNote(
            scheme_item=self.scheme_item,
            teacher=self.other_teacher,
            title="Introduction to Algebra",
        )

        with self.assertRaises(ValidationError):
            lesson_note.full_clean()
            
    def test_duplicate_active_lesson_number_for_same_scheme_item_is_rejected(self):
        LessonNote.objects.create(
            scheme_item=self.scheme_item,
            teacher=self.teacher,
            lesson_number=1,
            title="First Lesson",
        )

        duplicate = LessonNote(
            scheme_item=self.scheme_item,
            teacher=self.teacher,
            lesson_number=1,
            title="Duplicate First Lesson",
        )

        with self.assertRaises(ValidationError):
            duplicate.validate_constraints()


    def test_same_lesson_number_is_allowed_when_existing_note_is_inactive(self):
        LessonNote.objects.create(
            scheme_item=self.scheme_item,
            teacher=self.teacher,
            lesson_number=1,
            title="Inactive First Lesson",
            is_active=False,
        )

        active_note = LessonNote(
            scheme_item=self.scheme_item,
            teacher=self.teacher,
            lesson_number=1,
            title="Active First Lesson",
        )

        active_note.validate_constraints()


    def test_same_lesson_number_is_allowed_for_different_scheme_items(self):
        other_scheme_item = SchemeOfWorkItem.objects.create(
            scheme_of_work=self.scheme,
            title="Another Scheme Item",
        )

        LessonNote.objects.create(
            scheme_item=self.scheme_item,
            teacher=self.teacher,
            lesson_number=1,
            title="First Lesson",
        )

        other_note = LessonNote(
            scheme_item=other_scheme_item,
            teacher=self.teacher,
            lesson_number=1,
            title="First Lesson for Another Topic",
        )

        other_note.validate_constraints()
        
        

class LessonNoteFormTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="School A",
            code="FORM-SCHOOL-A",
        )
        self.other_school = School.objects.create(
            name="School B",
            code="FORM-SCHOOL-B",
        )

        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
        )
        self.term = Term.objects.create(
            session=self.session,
            name=Term.TermName.FIRST,
        )

        self.other_session = AcademicSession.objects.create(
            school=self.school,
            name="2027/2028",
        )
        self.other_term = Term.objects.create(
            session=self.other_session,
            name=Term.TermName.FIRST,
        )

        self.other_school_session = AcademicSession.objects.create(
            school=self.other_school,
            name="2026/2027",
        )
        self.other_school_term = Term.objects.create(
            session=self.other_school_session,
            name=Term.TermName.FIRST,
        )

        self.school_class = SchoolClass.objects.create(
            school=self.school,
            name="JSS 1",
        )
        self.other_class = SchoolClass.objects.create(
            school=self.school,
            name="JSS 2",
        )
        self.other_school_class = SchoolClass.objects.create(
            school=self.other_school,
            name="JSS 1",
        )

        self.subject = Subject.objects.create(
            school=self.school,
            name="Mathematics",
            code="FORM-MATH",
        )
        self.other_subject = Subject.objects.create(
            school=self.school,
            name="English",
            code="FORM-ENG",
        )
        self.other_school_subject = Subject.objects.create(
            school=self.other_school,
            name="Mathematics",
            code="FORM-OTHER-MATH",
        )

        self.user = User.objects.create_user(
            username="form_teacher_a",
            school=self.school,
            role=User.Role.TEACHER,
        )
        self.other_user = User.objects.create_user(
            username="form_teacher_b",
            school=self.school,
            role=User.Role.TEACHER,
        )
        self.other_school_user = User.objects.create_user(
            username="form_teacher_c",
            school=self.other_school,
            role=User.Role.TEACHER,
        )

        self.teacher = Teacher.objects.create(
            user=self.user,
            staff_id="FORM-T001",
        )
        self.other_teacher = Teacher.objects.create(
            user=self.other_user,
            staff_id="FORM-T002",
        )
        self.other_school_teacher = Teacher.objects.create(
            user=self.other_school_user,
            staff_id="FORM-T003",
        )

        self.scheme = SchemeOfWork.objects.create(
            school=self.school,
            school_class=self.school_class,
            subject=self.subject,
            term=self.term,
            name="JSS 1 Mathematics Scheme",
        )

        self.scheme_item = SchemeOfWorkItem.objects.create(
            scheme_of_work=self.scheme,
            title="Introduction to Algebra",
        )

        SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
            term=self.term,
        )

    def test_teacher_sees_correctly_allocated_scheme_item(self):
        form = LessonNoteForm(user=self.user)

        self.assertIn(
            self.scheme_item,
            form.fields["scheme_item"].queryset,
        )

    def test_teacher_does_not_see_another_teachers_allocation(self):
        other_scheme = SchemeOfWork.objects.create(
            school=self.school,
            school_class=self.school_class,
            subject=self.other_subject,
            term=self.term,
            name="JSS 1 English Scheme",
        )
        other_item = SchemeOfWorkItem.objects.create(
            scheme_of_work=other_scheme,
            title="Parts of Speech",
        )

        SubjectAllocation.objects.create(
            teacher=self.other_teacher,
            subject=self.other_subject,
            school_class=self.school_class,
            term=self.term,
        )

        form = LessonNoteForm(user=self.user)

        self.assertNotIn(
            other_item,
            form.fields["scheme_item"].queryset,
        )

    def test_teacher_does_not_see_another_school_scheme_item(self):
        other_scheme = SchemeOfWork.objects.create(
            school=self.other_school,
            school_class=self.other_school_class,
            subject=self.other_school_subject,
            term=self.other_school_term,
            name="Other School Mathematics Scheme",
        )
        other_item = SchemeOfWorkItem.objects.create(
            scheme_of_work=other_scheme,
            title="Other School Topic",
        )

        SubjectAllocation.objects.create(
            teacher=self.other_school_teacher,
            subject=self.other_school_subject,
            school_class=self.other_school_class,
            term=self.other_school_term,
        )

        form = LessonNoteForm(user=self.user)

        self.assertNotIn(
            other_item,
            form.fields["scheme_item"].queryset,
        )

    def test_inactive_scheme_item_is_excluded(self):
        inactive_item = SchemeOfWorkItem.objects.create(
            scheme_of_work=self.scheme,
            title="Inactive Topic",
            is_active=False,
        )

        form = LessonNoteForm(user=self.user)

        self.assertNotIn(
            inactive_item,
            form.fields["scheme_item"].queryset,
        )

    def test_inactive_scheme_is_excluded(self):
        inactive_scheme = SchemeOfWork.objects.create(
            school=self.school,
            school_class=self.school_class,
            subject=self.other_subject,
            term=self.other_term,
            name="Inactive English Scheme",
            is_active=False,
        )
        inactive_item = SchemeOfWorkItem.objects.create(
            scheme_of_work=inactive_scheme,
            title="Inactive Scheme Topic",
        )

        SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=self.other_subject,
            school_class=self.school_class,
            term=self.other_term,
        )

        form = LessonNoteForm(user=self.user)

        self.assertNotIn(
            inactive_item,
            form.fields["scheme_item"].queryset,
        )

    def test_teacher_lesson_number_status_and_is_active_are_not_form_fields(self):
        form = LessonNoteForm(user=self.user)

        self.assertNotIn("teacher", form.fields)
        self.assertNotIn("lesson_number", form.fields)
        self.assertNotIn("status", form.fields)
        self.assertNotIn("is_active", form.fields)
        
        
class LessonNoteCreateViewTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="View Test School",
            code="VIEW-SCHOOL-A",
        )

        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
        )

        self.term = Term.objects.create(
            session=self.session,
            name=Term.TermName.FIRST,
        )

        self.school_class = SchoolClass.objects.create(
            school=self.school,
            name="JSS 1",
        )

        self.subject = Subject.objects.create(
            school=self.school,
            name="Mathematics",
            code="VIEW-MATH",
        )

        self.user = User.objects.create_user(
            username="view_teacher",
            password="testpass123",
            school=self.school,
            role=User.Role.TEACHER,
        )

        self.teacher = Teacher.objects.create(
            user=self.user,
            staff_id="VIEW-T001",
        )

        self.scheme = SchemeOfWork.objects.create(
            school=self.school,
            school_class=self.school_class,
            subject=self.subject,
            term=self.term,
            name="JSS 1 Mathematics Scheme",
        )

        self.scheme_item = SchemeOfWorkItem.objects.create(
            scheme_of_work=self.scheme,
            title="Introduction to Algebra",
        )

        SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
            term=self.term,
        )

    def test_teacher_can_create_lesson_note(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/library/lesson-notes/create/",
            {
                "scheme_item": self.scheme_item.pk,
                "title": "Introduction to Algebra",
                "objectives": "Understand basic algebraic expressions.",
                "content": "An algebraic expression contains variables and constants.",
                "activities": "Teacher explanation and class exercises.",
                "resources": "Whiteboard and textbook.",
                "assessment": "Short class exercise.",
                "notes": "First lesson.",
            },
        )

        self.assertEqual(response.status_code, 302)

        lesson_note = LessonNote.objects.get()

        self.assertEqual(lesson_note.teacher, self.teacher)
        self.assertEqual(lesson_note.scheme_item, self.scheme_item)
        self.assertEqual(lesson_note.lesson_number, 1)
        self.assertEqual(lesson_note.status, LessonNote.Status.DRAFT)
        self.assertTrue(lesson_note.is_active)

    def test_second_lesson_note_gets_next_lesson_number(self):
        self.client.force_login(self.user)

        LessonNote.objects.create(
            scheme_item=self.scheme_item,
            teacher=self.teacher,
            lesson_number=1,
            title="First Lesson",
        )

        response = self.client.post(
            "/library/lesson-notes/create/",
            {
                "scheme_item": self.scheme_item.pk,
                "title": "Second Lesson",
                "content": "Second lesson content.",
            },
        )

        self.assertEqual(response.status_code, 302)

        lesson_notes = LessonNote.objects.filter(
            scheme_item=self.scheme_item,
            is_active=True,
        ).order_by("lesson_number")

        self.assertEqual(lesson_notes.count(), 2)
        self.assertEqual(lesson_notes[1].lesson_number, 2)

    def test_non_teacher_cannot_create_lesson_note(self):
        non_teacher = User.objects.create_user(
            username="view_admin",
            password="testpass123",
            school=self.school,
            role=User.Role.ADMIN,
        )

        self.client.force_login(non_teacher)

        response = self.client.post(
            "/library/lesson-notes/create/",
            {
                "scheme_item": self.scheme_item.pk,
                "title": "Should Not Save",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(LessonNote.objects.count(), 0)