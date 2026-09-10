from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from accounts.decorators import management_required
from accounts.permissions import school_permission_required
from academics.models import Term

from .forms import (
    TimetableForm,
    TimetablePeriodForm,
    TimetableRequirementForm,
    TeacherAvailabilityForm,
)
from .models import (
    Timetable,
    TimetablePeriod,
    TimetableRequirement,
    TeacherAvailability,
)

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError


@management_required
@login_required
@school_permission_required("timetable.create")
def create_timetable(request):
    school = request.user.school

    if request.method == "POST":
        form = TimetableForm(request.POST, school=school)

        if form.is_valid():
            timetable = form.save(commit=False)
            timetable.school = school
            timetable.created_by = request.user
            timetable.term = form.cleaned_data["term"]
            timetable.save()

            return redirect("timetable_list")
    else:
        form = TimetableForm(school=school)

    return render(
        request,
        "timetable/create_timetable.html",
        {"form": form},
    )


@login_required
def timetable_list(request):
    school = request.user.school

    timetables = (
        Timetable.objects
        .filter(school=school)
        .select_related("term", "term__session")
        .order_by("-created_at")
    )

    return render(
        request,
        "timetable/timetable_list.html",
        {"timetables": timetables},
    )

@login_required
def timetable_periods(request, timetable_id):
    school = request.user.school

    timetable = get_object_or_404(
        Timetable.objects.select_related("term", "term__session"),
        id=timetable_id,
        school=school,
    )

    if request.method == "POST":
        form = TimetablePeriodForm(request.POST)

        if form.is_valid():
            period = form.save(commit=False)
            period.timetable = timetable

            try:
                period.save()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    f"Period '{period.name}' was added successfully.",
                )

                return redirect(
                    "timetable_periods",
                    timetable_id=timetable.id,
                )
    else:
        form = TimetablePeriodForm()

    periods = timetable.periods.all()

    return render(
        request,
        "timetable/timetable_periods.html",
        {
            "timetable": timetable,
            "periods": periods,
            "form": form,
        },
    )

@login_required
def timetable_requirements(request, timetable_id):
    school = request.user.school

    timetable = get_object_or_404(
        Timetable.objects.select_related(
            "term",
            "term__session",
        ),
        id=timetable_id,
        school=school,
    )

    if request.method == "POST":
        form = TimetableRequirementForm(
            request.POST,
            timetable=timetable,
        )

        if form.is_valid():
            requirement = form.save(commit=False)
            requirement.timetable = timetable

            try:
                requirement.save()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    "Timetable requirement was added successfully.",
                )

                return redirect(
                    "timetable_requirements",
                    timetable_id=timetable.id,
                )
    else:
        form = TimetableRequirementForm(
            timetable=timetable,
        )

    requirements = (
        timetable.requirements
        .select_related(
            "allocation",
            "allocation__subject",
            "allocation__school_class",
            "allocation__teacher",
            "allocation__teacher__user",
        )
        .order_by(
            "allocation__school_class__name",
            "allocation__subject__name",
        )
    )

    return render(
        request,
        "timetable/timetable_requirements.html",
        {
            "timetable": timetable,
            "requirements": requirements,
            "form": form,
        },
    )

@login_required
def edit_timetable_requirement(request, timetable_id, requirement_id):
    school = request.user.school

    timetable = get_object_or_404(
        Timetable.objects.select_related(
            "term",
            "term__session",
        ),
        id=timetable_id,
        school=school,
    )

    requirement = get_object_or_404(
        TimetableRequirement.objects.select_related(
            "allocation",
            "allocation__subject",
            "allocation__school_class",
            "allocation__teacher",
            "allocation__teacher__user",
        ),
        id=requirement_id,
        timetable=timetable,
    )

    if request.method == "POST":
        form = TimetableRequirementForm(
            request.POST,
            instance=requirement,
            timetable=timetable,
        )

        if form.is_valid():
            try:
                form.save()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    "Timetable requirement was updated successfully.",
                )

                return redirect(
                    "timetable_requirements",
                    timetable_id=timetable.id,
                )
    else:
        form = TimetableRequirementForm(
            instance=requirement,
            timetable=timetable,
        )

    return render(
        request,
        "timetable/edit_timetable_requirement.html",
        {
            "timetable": timetable,
            "requirement": requirement,
            "form": form,
        },
    )
    
@login_required
def delete_timetable_requirement(request, timetable_id, requirement_id):
    school = request.user.school

    timetable = get_object_or_404(
        Timetable.objects.select_related(
            "term",
            "term__session",
        ),
        id=timetable_id,
        school=school,
    )

    requirement = get_object_or_404(
        TimetableRequirement.objects.select_related(
            "allocation",
            "allocation__subject",
            "allocation__school_class",
            "allocation__teacher",
            "allocation__teacher__user",
        ),
        id=requirement_id,
        timetable=timetable,
    )

    if request.method == "POST":
        requirement.delete()

        messages.success(
            request,
            "Timetable requirement was deleted successfully.",
        )

        return redirect(
            "timetable_requirements",
            timetable_id=timetable.id,
        )

    return render(
        request,
        "timetable/delete_timetable_requirement.html",
        {
            "timetable": timetable,
            "requirement": requirement,
        },
    )

@login_required
def edit_timetable_period(request, timetable_id, period_id):
    school = request.user.school

    timetable = get_object_or_404(
        Timetable.objects.select_related("term", "term__session"),
        id=timetable_id,
        school=school,
    )

    period = get_object_or_404(
        TimetablePeriod,
        id=period_id,
        timetable=timetable,
    )

    if request.method == "POST":
        form = TimetablePeriodForm(request.POST, instance=period)

        if form.is_valid():
            try:
                form.save()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    f"Period '{period.name}' was updated successfully.",
                )

                return redirect(
                    "timetable_periods",
                    timetable_id=timetable.id,
                )
    else:
        form = TimetablePeriodForm(instance=period)

    return render(
        request,
        "timetable/edit_timetable_period.html",
        {
            "timetable": timetable,
            "period": period,
            "form": form,
        },
    )


@login_required
def delete_timetable_period(request, timetable_id, period_id):
    school = request.user.school

    timetable = get_object_or_404(
        Timetable,
        id=timetable_id,
        school=school,
    )

    period = get_object_or_404(
        TimetablePeriod,
        id=period_id,
        timetable=timetable,
    )

    if request.method == "POST":
        period_name = period.name
        period.delete()

        messages.success(
            request,
            f"Period '{period_name}' was deleted successfully.",
        )

        return redirect(
            "timetable_periods",
            timetable_id=timetable.id,
        )

    return render(
        request,
        "timetable/delete_timetable_period.html",
        {
            "timetable": timetable,
            "period": period,
        },
    )
    
@login_required
@school_permission_required("timetable.create")
def teacher_availability(request):
    if request.method == "POST":
        form = TeacherAvailabilityForm(
            request.POST,
            school=request.user.school,
        )

        if form.is_valid():
            availability = form.save(commit=False)
            availability.save()

            messages.success(
                request,
                "Teacher availability was added successfully.",
            )

            return redirect("teacher_availability")
    else:
        form = TeacherAvailabilityForm(
            school=request.user.school,
        )

    availabilities = (
        TeacherAvailability.objects.filter(
            teacher__user__school=request.user.school
        )
        .select_related("teacher", "teacher__user")
        .order_by(
            "teacher__user__last_name",
            "teacher__user__first_name",
            "day",
            "start_time",
        )
    )

    return render(
        request,
        "timetable/teacher_availability.html",
        {
            "form": form,
            "availabilities": availabilities,
        },
    )

@login_required
@school_permission_required("timetable.create")
def edit_teacher_availability(request, availability_id):
    availability = get_object_or_404(
        TeacherAvailability.objects.select_related(
            "teacher",
            "teacher__user",
        ),
        id=availability_id,
        teacher__user__school=request.user.school,
    )

    if request.method == "POST":
        form = TeacherAvailabilityForm(
            request.POST,
            instance=availability,
            school=request.user.school,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Teacher availability was updated successfully.",
            )

            return redirect("teacher_availability")
    else:
        form = TeacherAvailabilityForm(
            instance=availability,
            school=request.user.school,
        )

    return render(
        request,
        "timetable/edit_teacher_availability.html",
        {
            "form": form,
            "availability": availability,
        },
    )
    

@login_required
@school_permission_required("timetable.create")
def delete_teacher_availability(request, availability_id):
    availability = get_object_or_404(
        TeacherAvailability.objects.select_related(
            "teacher",
            "teacher__user",
        ),
        id=availability_id,
        teacher__user__school=request.user.school,
    )

    if request.method == "POST":
        availability.delete()

        messages.success(
            request,
            "Teacher availability was deleted successfully.",
        )

        return redirect("teacher_availability")

    return render(
        request,
        "timetable/delete_teacher_availability.html",
        {
            "availability": availability,
        },
    )