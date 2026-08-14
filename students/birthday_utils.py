from datetime import date, timedelta

from students.models import Student
from teachers.models import Teacher


def _birthday_this_year(dob, year):
    """
    Return the person's birthday in the supplied year.
    Handles February 29 birthdays in non-leap years.
    """
    try:
        return date(year, dob.month, dob.day)
    except ValueError:
        # Feb 29 in a non-leap year
        return date(year, 2, 28)


def _days_until_birthday(dob, today):
    """
    Number of days from today until the next occurrence
    of the person's birthday.
    """
    birthday = _birthday_this_year(dob, today.year)

    if birthday < today:
        birthday = _birthday_this_year(dob, today.year + 1)

    return (birthday - today).days


def get_school_birthdays(school, days=30):
    """
    Return students and teachers in this school whose birthdays
    fall between today and the next `days` days.
    """

    today = date.today()
    end_date = today + timedelta(days=days)

    students = Student.objects.filter(
        user__school=school,
        date_of_birth__isnull=False,
        is_active=True,
        user__is_active=True,
    ).select_related(
        "user",
        "school_class",
    )

    teachers = Teacher.objects.filter(
        user__school=school,
        date_of_birth__isnull=False,
        is_active=True,
        user__is_active=True,
    ).select_related(
        "user",
    )

    student_birthdays = []
    teacher_birthdays = []

    for student in students:

        birthday = _birthday_this_year(
            student.date_of_birth,
            today.year,
        )

        if birthday < today:
            birthday = _birthday_this_year(
                student.date_of_birth,
                today.year + 1,
            )

        if today <= birthday <= end_date:

            student_birthdays.append({
                "person": student,
                "name": student.user.get_full_name()
                         or student.user.username,
                "birthday": birthday,
                "days_until": (birthday - today).days,
                "type": "Student",
                "class": student.school_class,
            })

    for teacher in teachers:

        birthday = _birthday_this_year(
            teacher.date_of_birth,
            today.year,
        )

        if birthday < today:
            birthday = _birthday_this_year(
                teacher.date_of_birth,
                today.year + 1,
            )

        if today <= birthday <= end_date:

            teacher_birthdays.append({
                "person": teacher,
                "name": teacher.user.get_full_name()
                         or teacher.user.username,
                "birthday": birthday,
                "days_until": (birthday - today).days,
                "type": "Staff",
                "class": None,
            })

    birthdays = student_birthdays + teacher_birthdays

    birthdays.sort(
        key=lambda item: item["days_until"]
    )

    return birthdays

def get_today_birthdays(school):
    """
    Return birthdays occurring today.
    """

    birthdays = get_school_birthdays(
        school,
        days=0,
    )

    return birthdays


def get_upcoming_birthdays(school, days=30):
    """
    Return birthdays coming up within the specified number of days,
    excluding today.
    """

    birthdays = get_school_birthdays(
        school,
        days=days,
    )

    return [
        birthday
        for birthday in birthdays
        if birthday["days_until"] > 0
    ]