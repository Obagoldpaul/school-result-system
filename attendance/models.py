from django.db import models


class AttendanceRecord(models.Model):
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    is_present = models.BooleanField(default=True)
    marked_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('student', 'date')

    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f"{self.student} - {self.date} - {status}"


def get_attendance_summary(student, term):
    """Returns (days_present, days_marked) for a student within a term's date range."""

    if student.school_class.school_id != term.session.school_id:
        return None, None

    if not term.start_date or not term.end_date:
        return None, None

    records = AttendanceRecord.objects.filter(
        student=student,
        date__gte=term.start_date,
        date__lte=term.end_date
    )

    days_marked = records.count()
    days_present = records.filter(is_present=True).count()

    return days_present, days_marked