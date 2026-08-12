from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import SubjectAllocationForm
from .models import SubjectAllocation
from accounts.decorators import staff_required
from accounts.utils import get_current_term


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


@staff_required
@login_required
def allocation_list(request):
    from academics.models import Term
    from students.models import SchoolClass

    school = request.user.school

    term_id = request.GET.get('term')

    if term_id:
        selected_term = Term.objects.filter(
            id=term_id,
            session__school=school,
        ).first()
    else:
        selected_term = get_current_term(request.user)

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

    classes = SchoolClass.objects.filter(
        school=school
    )

    grouped = []

    for c in classes:
        class_allocations = [
            a for a in allocations
            if a.school_class_id == c.id
        ]

        if class_allocations:
            grouped.append({
                'school_class': c,
                'allocations': class_allocations,
            })

    return render(
        request,
        'allocations/allocation_list.html',
        {
            'grouped': grouped,
            'terms': Term.objects.filter(
                session__school=school
            ).select_related(
                'session'
            ).order_by(
                '-session__name',
                'name',
            ),
            'selected_term': selected_term,
        }
    )