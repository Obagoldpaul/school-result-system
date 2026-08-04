TERM_ORDER = {
    "FIRST": 1,
    "SECOND": 2,
    "THIRD": 3,
}


def get_term_order(term):
    """
    Returns the numeric order of a term within an academic session.
    """
    return TERM_ORDER.get(term.name, 0)