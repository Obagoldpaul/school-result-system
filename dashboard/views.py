from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from academics.models import AcademicSession, Term
from accounts.permissions import is_management
from accounts.permissions import school_permission_required

from .services import build_dashboard
from django.db import IntegrityError
from students.models import Student, SchoolClass, Department
from schools.utils import school_has_feature

@login_required
def home(request):

    # Students must have the Student Portal feature
    # in their school's subscription package.
    if hasattr(request.user, "student_profile"):

        school = getattr(request.user, "school", None)

        if not school or not school_has_feature(
            school,
            "STUDENT_PORTAL"
        ):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "The Student Portal is not available "
                "on your school's current subscription package."
            )

    context = build_dashboard(request.user)

    return render(
        request,
        "dashboard/home.html",
        context
    )

@login_required
@school_permission_required("academics.manage")
def academic_management(request):

    school = request.user.school

    current_session = AcademicSession.objects.filter(
        school=school,
        is_current=True
    ).first()

    sessions = AcademicSession.objects.filter(
        school=school
    ).order_by("-name")

    # Which session are we viewing?
    selected_session_id = request.GET.get("session")

    if selected_session_id:
        selected_session = get_object_or_404(
            AcademicSession,
            id=selected_session_id,
            school=school,
        )
    else:
        selected_session = current_session

    terms = (
        Term.objects.filter(
            session=selected_session
        ).order_by("name")
        if selected_session
        else Term.objects.none()
    )

    # ---------------------------------------------------------
    # DEPARTMENTS
    # ---------------------------------------------------------

    departments = Department.objects.filter(
        school=school
    ).order_by("name")

    context = {
        "current_session": current_session,
        "selected_session": selected_session,
        "sessions": sessions,
        "terms": terms,
        "departments": departments,
    }

    return render(
        request,
        "dashboard/academic_management.html",
        context,
    )
    

@login_required
@school_permission_required("academics.manage")
def create_academic_session(request):

    if request.method != "POST":
        return redirect("academic_management")

    name = request.POST.get("name", "").strip()
    

    if not name:
        messages.error(request, "Please enter an academic session.")
        return redirect("academic_management")

    try:
        AcademicSession.objects.create(
            school=request.user.school,
            name=name,
        )

        messages.success(
            request,
            f"Academic session {name} was created successfully."
        )

    except IntegrityError:
        messages.error(
            request,
            f"Academic session {name} already exists."
        )

    return redirect("academic_management")


@login_required
@school_permission_required("academics.manage")
def set_current_session(request, session_id):

    if request.method != "POST":
        return redirect("academic_management")

    session = get_object_or_404(
        AcademicSession,
        id=session_id,
        school=request.user.school,
    )

    # Find the first term belonging to this session.
    first_term = session.terms.filter(
        name=Term.TermName.FIRST
    ).first()

    if not first_term:
        messages.error(
            request,
            f"{session.name} does not have a First Term yet. "
            "Create the terms before making this session current."
        )
        return redirect("academic_management")

    # Making the term current automatically makes
    # its session current because of Term.save().
    first_term.is_current = True
    first_term.save()

    messages.success(
        request,
        f"{session.name} is now the current academic session "
        f"and First Term is now current."
    )

    return redirect("academic_management")

@login_required
@school_permission_required("academics.manage")
def create_term(request):

    if request.method != "POST":
        return redirect("academic_management")

    session = get_object_or_404(
        AcademicSession,
        id=request.POST.get("session_id"),
        school=request.user.school,
    )

    name = request.POST.get("name")
    start_date = request.POST.get("start_date") or None
    end_date = request.POST.get("end_date") or None

    if not name:
        messages.error(request, "Please select a term.")
        return redirect("academic_management")

    if Term.objects.filter(
        session=session,
        name=name
    ).exists():
        messages.error(
            request,
            f"{dict(Term.TermName.choices).get(name, name)} already exists "
            f"for {session.name}."
        )
        return redirect("academic_management")

    Term.objects.create(
        session=session,
        name=name,
        start_date=start_date,
        end_date=end_date,
    )

    messages.success(
        request,
        f"{dict(Term.TermName.choices).get(name, name)} "
        f"created successfully for {session.name}."
    )

    return redirect("academic_management")

@login_required
@school_permission_required("academics.manage")
def set_current_term(request, term_id):

    if request.method != "POST":
        return redirect("academic_management")

    term = get_object_or_404(
        Term,
        id=term_id,
        session__school=request.user.school,
    )

    term.is_current = True
    term.save()

    messages.success(
        request,
        f"{term.get_name_display()} is now the current term."
    )

    return redirect("academic_management")

@login_required
@school_permission_required("academics.manage")
def create_department(request):

    if request.method == "POST":

        name = request.POST.get("name", "").strip()

        if not name:
            messages.error(
                request,
                "Department name is required."
            )
            return redirect("academic_management")

        school = request.user.school

        if Department.objects.filter(
            school=school,
            name__iexact=name,
        ).exists():

            messages.error(
                request,
                f"The department '{name}' already exists."
            )
            return redirect("academic_management")

        Department.objects.create(
            school=school,
            name=name,
        )

        messages.success(
            request,
            f"Department '{name}' was created successfully."
        )

    return redirect("academic_management")

@login_required
@school_permission_required("academics.manage")
def edit_department(request, department_id):

    department = get_object_or_404(
        Department,
        id=department_id,
        school=request.user.school,
    )

    if request.method != "POST":
        return redirect("academic_management")

    name = request.POST.get("name", "").strip()

    if not name:
        messages.error(
            request,
            "Department name is required."
        )
        return redirect("academic_management")

    # Prevent duplicate department names within this school.
    if Department.objects.filter(
        school=request.user.school,
        name__iexact=name,
    ).exclude(
        id=department.id
    ).exists():

        messages.error(
            request,
            f"The department '{name}' already exists."
        )
        return redirect("academic_management")

    old_name = department.name

    department.name = name
    department.save()

    messages.success(
        request,
        f"Department '{old_name}' was renamed to '{name}'."
    )

    return redirect("academic_management")