from academics.models import AcademicSession, Term


def current_session():

    return AcademicSession.objects.filter(
        is_current=True
    ).first()


def current_term():

    return Term.objects.filter(
        is_current=True
    ).first()