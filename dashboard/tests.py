from django.test import TestCase
from django.contrib.auth import get_user_model

from schools.models import School
from students.models import Department, SchoolClass, Student
from subjects.models import ClassSubject, Subject

from .services import get_registered_subjects_for_student


User = get_user_model()


class RegisteredSubjectsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            name="Test School",
            code="TST001",
            school_type=School.SchoolType.SECONDARY,
        )

        cls.school_class = SchoolClass.objects.create(
            school=cls.school,
            name="SS 1",
            section=SchoolClass.Section.SENIOR_SECONDARY,
        )

        cls.science_department = Department.objects.create(
            school=cls.school,
            name="Science",
        )

        cls.arts_department = Department.objects.create(
            school=cls.school,
            name="Arts",
        )

        cls.science_student = cls.create_student(
            username="science_student",
            admission_number="TST001",
            department=cls.science_department,
        )

        cls.arts_student = cls.create_student(
            username="arts_student",
            admission_number="TST002",
            department=cls.arts_department,
        )

        cls.compulsory_subject = cls.create_subject(
            "English Language", "TST-ENG"
        )
        cls.elective_subject = cls.create_subject(
            "Physics", "TST-PHY", is_elective=True
        )
        cls.science_subject = cls.create_subject(
            "Chemistry", "TST-CHEM"
        )
        cls.arts_subject = cls.create_subject(
            "Literature", "TST-LIT"
        )
        cls.inactive_subject = cls.create_subject(
            "Inactive Subject", "TST-INACT", is_active=False
        )

        ClassSubject.objects.create(
            school_class=cls.school_class,
            subject=cls.compulsory_subject,
        )
        ClassSubject.objects.create(
            school_class=cls.school_class,
            subject=cls.elective_subject,
        )
        ClassSubject.objects.create(
            school_class=cls.school_class,
            subject=cls.science_subject,
        )
        ClassSubject.objects.create(
            school_class=cls.school_class,
            subject=cls.arts_subject,
        )
        ClassSubject.objects.create(
            school_class=cls.school_class,
            subject=cls.inactive_subject,
        )

    @classmethod
    def create_student(cls, username, admission_number, department):
        user = User.objects.create_user(
            username=username,
            password="test-password",
            school=cls.school,
            role=User.Role.STUDENT,
        )
        return Student.objects.create(
            user=user,
            school_class=cls.school_class,
            department=department,
            admission_number=admission_number,
        )

    @classmethod
    def create_subject(
        cls, name, code, is_elective=False, is_active=True
    ):
        return Subject.objects.create(
            name=name,
            code=code,
            school=cls.school,
            level=Subject.SubjectLevel.SECONDARY,
            is_elective=is_elective,
            is_active=is_active,
        )

    def get_subject_ids(self, student):
        return set(
            get_registered_subjects_for_student(
                student, self.school
            ).values_list("id", flat=True)
        )

    def test_compulsory_subject_is_included_automatically(self):
        self.assertIn(
            self.compulsory_subject.id,
            self.get_subject_ids(self.science_student),
        )

    def test_unselected_elective_is_excluded(self):
        self.assertNotIn(
            self.elective_subject.id,
            self.get_subject_ids(self.science_student),
        )

    def test_selected_eligible_elective_is_included(self):
        self.science_student.elective_subjects.add(
            self.elective_subject
        )
        self.assertIn(
            self.elective_subject.id,
            self.get_subject_ids(self.science_student),
        )

    def test_class_subject_assignment_does_not_restrict_students(self):
        science_ids = self.get_subject_ids(self.science_student)
        arts_ids = self.get_subject_ids(self.arts_student)

        self.assertIn(self.science_subject.id, science_ids)
        self.assertIn(self.science_subject.id, arts_ids)
        self.assertIn(self.arts_subject.id, science_ids)
        self.assertIn(self.arts_subject.id, arts_ids)

    def test_inactive_subject_is_excluded(self):
        self.assertNotIn(
            self.inactive_subject.id,
            self.get_subject_ids(self.science_student),
        )

    def test_registered_subject_count_has_no_duplicates(self):
        self.science_student.elective_subjects.add(
            self.elective_subject
        )
        subjects = get_registered_subjects_for_student(
            self.science_student, self.school
        )
        subject_ids = list(subjects.values_list("id", flat=True))

        self.assertEqual(len(subject_ids), len(set(subject_ids)))
        
    
    def test_student_from_another_school_gets_no_subjects(self):
        other_school = School.objects.create(
            name="Other Test School",
            code="TST002",
            school_type=School.SchoolType.SECONDARY,
        )

        other_school_user = User.objects.create_user(
            username="other_school_student",
            password="test-password",
            school=other_school,
            role=User.Role.STUDENT,
        )

        other_school_class = SchoolClass.objects.create(
            school=other_school,
            name="SS 1",
            section=SchoolClass.Section.SENIOR_SECONDARY,
        )

        other_school_student = Student.objects.create(
            user=other_school_user,
            school_class=other_school_class,
            admission_number="OTHER001",
        )

        subjects = get_registered_subjects_for_student(
            other_school_student,
            self.school,
        )

        self.assertFalse(subjects.exists())

