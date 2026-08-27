from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import (
    SubjectAllocationForm,
    BulkSubjectAllocationForm,
)

from .models import SubjectAllocation

from accounts.decorators import staff_required
from accounts.permissions import school_permission_required
from accounts.utils import get_current_term

from students.models import SchoolClass
from academics.models import Term


@school_permission_required("subjects.assign")
@staff_required
@login_required
def add_allocation(request):
    if request.method == 'POST':
        form = SubjectAllocationForm(
            request.POST,
            user=request.user,
        )
        if form.is_valid():
            form.save()
            return redirect('allocation_list')
    else:
        form = SubjectAllocationForm(
            user=request.user,
        )
    return render(request, 'allocations/add_allocation.html', {
        'form': form,
        'allocation_list_url': '/allocations/',
        }
    )
    
@school_permission_required("subjects.assign")
@staff_required
@login_required
def bulk_add_allocation(request):
    """
    Professional bulk subject allocation.

    Step 1:
        Select class and term.

    Step 2:
        Load subjects assigned to that class.

    Step 3:
        Assign a teacher to each subject.

    Step 4:
        Allocate all selected subjects.
    """

    school = request.user.school

    form = BulkSubjectAllocationForm(
        request.POST or None,
        user=request.user,
    )

    selected_class = None
    selected_term = None

    subject_rows = []
    existing_allocations = {}

    teachers = form.get_teachers()

    # --------------------------------------------------
    # LOAD SUBJECTS
    # --------------------------------------------------

    if request.method == 'POST':

        action = request.POST.get('action')

        if action == 'load_subjects':

            if form.is_valid():

                selected_class = form.cleaned_data[
                    'school_class'
                ]

                selected_term = form.cleaned_data[
                    'term'
                ]

                subjects = form.get_subjects()

                allocations = SubjectAllocation.objects.filter(
                    school_class=selected_class,
                    term=selected_term,
                    subject__school=school,
                    teacher__user__school=school,
                ).select_related(
                    'teacher',
                    'teacher__user',
                    'subject',
                )

                existing_allocations = {
                    allocation.subject_id: allocation
                    for allocation in allocations
                }

                subject_rows = [
                    {
                        'subject': subject,
                        'existing': existing_allocations.get(
                            subject.id
                        ),
                    }
                    for subject in subjects
                ]

        # --------------------------------------------------
        # ALLOCATE ALL
        # --------------------------------------------------

        elif action == 'allocate_all':

            if form.is_valid():

                selected_class = form.cleaned_data[
                    'school_class'
                ]

                selected_term = form.cleaned_data[
                    'term'
                ]

                subjects = form.get_subjects()

                created_count = 0
                updated_count = 0
                skipped_count = 0
                error_count = 0

                for subject in subjects:

                    field_name = f'teacher_{subject.id}'

                    teacher_id = request.POST.get(
                        field_name
                    )

                    # No teacher selected.
                    if not teacher_id:
                        continue

                    teacher = teachers.filter(
                        id=teacher_id
                    ).first()

                    if not teacher:
                        error_count += 1
                        continue

                    # Extra school protection.
                    # Extra multi-tenant protection.
                    if teacher.user.school_id != school.id:
                        error_count += 1
                        continue

                    existing = SubjectAllocation.objects.filter(
                        subject=subject,
                        school_class=selected_class,
                        term=selected_term,
                    ).first()

                    # ------------------------------------------
                    # EXISTING ALLOCATION
                    # ------------------------------------------

                    if existing:

                        # Only draft allocations can be changed.
                        if (
                            existing.status
                            == SubjectAllocation.Status.DRAFT
                        ):

                            if existing.teacher_id != teacher.id:

                                existing.teacher = teacher
                                existing.save()

                                updated_count += 1

                            else:

                                skipped_count += 1

                        else:

                            skipped_count += 1

                        continue

                    # ------------------------------------------
                    # NEW ALLOCATION
                    # ------------------------------------------

                    SubjectAllocation.objects.create(
                        teacher=teacher,
                        subject=subject,
                        school_class=selected_class,
                        term=selected_term,
                    )

                    created_count += 1

                if created_count:

                    messages.success(
                        request,
                        f'{created_count} subject allocation(s) '
                        'created successfully.'
                    )

                if updated_count:

                    messages.success(
                        request,
                        f'{updated_count} draft allocation(s) '
                        'updated successfully.'
                    )

                if skipped_count:

                    messages.warning(
                        request,
                        f'{skipped_count} allocation(s) were skipped '
                        'because they already exist or are already '
                        'in the approval workflow.'
                    )

                if error_count:

                    messages.error(
                        request,
                        f'{error_count} allocation(s) could not '
                        'be processed.'
                    )

                return redirect(
                    'allocation_list'
                )

    # --------------------------------------------------
    # GET
    # --------------------------------------------------

    elif request.method == 'GET':

        current_term = get_current_term(
            request.user
        )

        if current_term:

            form.initial['term'] = current_term

    # --------------------------------------------------
    # RENDER
    # --------------------------------------------------

    return render(
        request,
        'allocations/bulk_add_allocation.html',
        {
            'form': form,
            'subject_rows': subject_rows,
            'teachers': teachers,
            'existing_allocations': existing_allocations,
            'selected_class': selected_class,
            'selected_term': selected_term,
            'allocation_list_url': '/allocations/',
        }
    )


@school_permission_required("subjects.view")
@staff_required
@login_required
def allocation_list(request):
    from academics.models import Term
    from students.models import SchoolClass

    school = request.user.school

    term_id = request.GET.get('term')
    class_id = request.GET.get('class')

    # ----------------------------
    # Selected Term
    # ----------------------------

    if term_id:
        selected_term = Term.objects.filter(
            id=term_id,
            session__school=school,
        ).first()
    else:
        selected_term = get_current_term(request.user)

    # ----------------------------
    # Selected Class
    # ----------------------------

    if class_id:
        selected_class = SchoolClass.objects.filter(
            id=class_id,
            school=school,
        ).first()
    else:
        selected_class = None

    # ----------------------------
    # Allocations
    # ----------------------------

    allocations = SubjectAllocation.objects.filter(
        school_class__school=school,
        subject__school=school,
        teacher__user__school=school,
        term__session__school=school,
    ).select_related(
        'teacher',
        'subject',
        'school_class',
        'term',
    )

    if selected_term:
        allocations = allocations.filter(
            term=selected_term
        )

    if selected_class:
        allocations = allocations.filter(
            school_class=selected_class
        )

    # ----------------------------
    # Classes grouped by section
    # ----------------------------

    classes = SchoolClass.objects.filter(
        school=school
    ).order_by(
        'section',
        'name',
    )

    section_order = [
        SchoolClass.Section.PRE_PRIMARY,
        SchoolClass.Section.PRIMARY,
        SchoolClass.Section.JUNIOR_SECONDARY,
        SchoolClass.Section.SENIOR_SECONDARY,
    ]

    section_groups = []

    for section_value, section_label in SchoolClass.Section.choices:

        if section_value not in section_order:
            continue

        section_classes = []

        for c in classes:

            if c.section != section_value:
                continue

            class_allocations = [
                a for a in allocations
                if a.school_class_id == c.id
            ]

            if class_allocations:
                section_classes.append({
                    'school_class': c,
                    'allocations': class_allocations,
                })

        if section_classes:
            section_groups.append({
                'value': section_value,
                'label': section_label,
                'classes': section_classes,
            })
            
    return render(
        request,
        'allocations/allocation_list.html',
        {
            'section_groups': section_groups,

            'terms': Term.objects.filter(
                session__school=school
            ).select_related(
                'session'
            ).order_by(
                '-session__name',
                'name',
            ),

            'classes': classes,

            'selected_term': selected_term,

            'selected_class': selected_class,
        }
    )