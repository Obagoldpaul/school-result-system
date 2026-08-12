from academics.utils import get_term_order


def get_class_results(school_class, term):
    """
    Returns a list of dicts, one per student, with total score,
    average, and position — sorted by total score descending.
    """
    if school_class.school_id != term.session.school_id:
        return []

    from students.models import Student
    from .models import Score

    students = Student.objects.filter(
        school_class=school_class,
        is_active=True
    )

    results = []

    for student in students:
        scores = Score.objects.filter(
            student=student,
            term=term
        )

        if not scores.exists():
            continue

        total = sum(s.total_score for s in scores)
        average = total / scores.count()

        results.append({
            'student': student,
            'scores': scores,
            'total': total,
            'average': round(average, 2),
        })

    results.sort(
        key=lambda r: r['total'],
        reverse=True
    )

    for index, result in enumerate(results, start=1):
        result['position'] = index

    return results


def get_report_card_rows(student, term):
    """
    Returns subject rows for a report card, combining parent/sub-subjects
    into a single averaged row where applicable.
    """
    if student.school_class.school_id != term.session.school_id:
        return []
    from .models import Score

    all_scores = Score.objects.filter(
        student=student,
        term=term
    ).select_related(
        'subject',
        'subject__parent'
    )

    standalone_rows = []
    parent_groups = {}

    for score in all_scores:
        subject = score.subject

        if subject.parent:
            parent_groups.setdefault(
                subject.parent,
                []
            ).append(score)

        else:
            standalone_rows.append({
                'subject_name': subject.name,
                'code': subject.code,
                'ca_score': score.ca_score,
                'exam_score': score.exam_score,
                'total_score': score.total_score,
                'grade': score.grade,
            })

    combined_rows = []

    for parent_subject, child_scores in parent_groups.items():

        count = len(child_scores)

        avg_ca = sum(
            s.ca_score for s in child_scores
        ) / count

        avg_exam = sum(
            s.exam_score for s in child_scores
        ) / count

        avg_total = avg_ca + avg_exam

        combined_rows.append({
            'subject_name': parent_subject.name,
            'code': parent_subject.code,
            'ca_score': round(avg_ca, 2),
            'exam_score': round(avg_exam, 2),
            'total_score': round(avg_total, 2),
            'grade': _grade_from_total(avg_total),
        })

    return standalone_rows + combined_rows


def get_cumulative_report_rows(student, term):
    """
    Returns cumulative report rows across terms in the same session.
    """
    if student.school_class.school_id != term.session.school_id:
        return [], []
    from academics.models import Term

    current_order = get_term_order(term)

    terms_in_session = Term.objects.filter(
        session=term.session
    )

    relevant_terms = sorted(
        [
            t for t in terms_in_session
            if get_term_order(t) <= current_order
        ],
        key=get_term_order
    )

    subject_totals = {}
    subject_code = {}
    current_term_detail = {}

    for t in relevant_terms:

        term_rows = get_report_card_rows(
            student,
            t
        )

        for row in term_rows:

            key = row['subject_name']

            subject_code[key] = row['code']

            subject_totals.setdefault(
                key,
                {}
            )[t.id] = row['total_score']

            if t.id == term.id:
                current_term_detail[key] = {
                    'ca_score': row['ca_score'],
                    'exam_score': row['exam_score'],
                }

    rows = []

    for subject_name, term_scores in subject_totals.items():

        term_values = [
            term_scores.get(t.id)
            for t in relevant_terms
        ]

        available_values = [
            value for value in term_values
            if value is not None
        ]

        cumulative_average = (
            round(
                sum(available_values) / len(available_values),
                2
            )
            if available_values
            else 0
        )

        detail = current_term_detail.get(
            subject_name,
            {}
        )

        grade = _grade_from_total(
            cumulative_average
        )

        rows.append({
            'subject_name': subject_name,
            'code': subject_code[subject_name],
            'ca_score': detail.get('ca_score', '-'),
            'exam_score': detail.get('exam_score', '-'),
            'term_scores': term_values,
            'average': cumulative_average,
            'grade': grade,
            'remark': _remark_from_grade(grade),
        })

    return rows, relevant_terms


def _grade_from_total(total):
    if total >= 75:
        return 'A1'
    elif total >= 70:
        return 'B2'
    elif total >= 65:
        return 'B3'
    elif total >= 60:
        return 'C4'
    elif total >= 55:
        return 'C5'
    elif total >= 50:
        return 'C6'
    elif total >= 45:
        return 'D7'
    elif total >= 40:
        return 'E8'
    else:
        return 'F9'


def _remark_from_grade(grade):
    remarks = {
        'A1': 'Excellent',
        'B2': 'Very Good',
        'B3': 'Very Good',
        'C4': 'Good',
        'C5': 'Good',
        'C6': 'Credit',
        'D7': 'Fair',
        'E8': 'Pass',
        'F9': 'Fail',
    }

    return remarks.get(grade, '-')