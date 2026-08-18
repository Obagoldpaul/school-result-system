from .models import FeeAssignment


def get_student_fee_assignments(student, term):
    """
    Return all fee assignments that apply to a student for a term.

    Priority:
        1. Individual student assignment
        2. Class + department assignment
        3. Class-wide assignment

    If a higher-priority assignment exists for a fee category,
    lower-priority assignments for that same category are ignored.
    """

    assignments = FeeAssignment.objects.filter(
        term=term,
        is_active=True,
        fee_category__is_active=True,
    ).select_related(
        "fee_category",
        "school_class",
        "department",
        "student",
    )

    applicable = []

    for assignment in assignments:

        # ---------------------------------------------------------
        # 1. Individual student assignment
        # ---------------------------------------------------------

        if assignment.student_id:

            if assignment.student_id == student.id:
                applicable.append(assignment)

            continue

        # ---------------------------------------------------------
        # 2. Class assignment
        # ---------------------------------------------------------

        if assignment.school_class_id != student.school_class_id:
            continue

        # ---------------------------------------------------------
        # 2a. Class + department assignment
        # ---------------------------------------------------------

        if assignment.department_id:

            if assignment.department_id == student.department_id:
                applicable.append(assignment)

            continue

        # ---------------------------------------------------------
        # 3. Class-wide assignment
        # ---------------------------------------------------------

        applicable.append(assignment)

    # -------------------------------------------------------------
    # Resolve conflicts by fee category.
    #
    # Student-specific assignment wins over
    # department-specific assignment, which wins over
    # class-wide assignment.
    # -------------------------------------------------------------

    resolved = {}

    for assignment in applicable:

        category_id = assignment.fee_category_id

        if category_id not in resolved:

            resolved[category_id] = assignment
            continue

        existing = resolved[category_id]

        # Student-specific assignment has highest priority.
        if assignment.student_id:

            resolved[category_id] = assignment
            continue

        # Department-specific assignment beats class-wide.
        if assignment.department_id and not existing.department_id:
            resolved[category_id] = assignment

    return list(resolved.values())


def get_student_fee_breakdown(student, term):
    """
    Return the fee breakdown applicable to a student for a term.

    Returns:
        {
            "items": [...],
            "compulsory_total": ...,
            "optional_total": ...,
            "grand_total": ...,
        }
    """

    assignments = get_student_fee_assignments(
        student,
        term
    )

    compulsory_total = 0
    optional_total = 0

    items = []

    for assignment in assignments:

        amount = assignment.amount
        category = assignment.fee_category

        item = {
            "assignment": assignment,
            "category": category,
            "name": category.name,
            "category_type": category.category_type,
            "amount": amount,
        }

        items.append(item)

        if category.category_type == "COMPULSORY":
            compulsory_total += amount

        else:
            optional_total += amount

    return {
        "items": items,
        "compulsory_total": compulsory_total,
        "optional_total": optional_total,
        "grand_total": compulsory_total + optional_total,
    }