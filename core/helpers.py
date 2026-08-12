from academics.models import AcademicSession, Term


def current_session(user):
    if not user or not user.is_authenticated or not user.school:
        return None

    return AcademicSession.objects.filter(
        school=user.school,
        is_current=True,
    ).first()


def current_term(user):
    if not user or not user.is_authenticated or not user.school:
        return None

    return Term.objects.filter(
        session__school=user.school,
        is_current=True,
    ).first()