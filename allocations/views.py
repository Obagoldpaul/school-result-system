from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import SubjectAllocationForm
from .models import SubjectAllocation
from accounts.decorators import staff_required

@staff_required
@login_required
def add_allocation(request):
    if request.method == 'POST':
        form = SubjectAllocationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('allocation_list')
    else:
        form = SubjectAllocationForm()
    return render(request, 'allocations/add_allocation.html', {'form': form})

@staff_required
@login_required
def allocation_list(request):
    allocations = SubjectAllocation.objects.select_related('teacher', 'subject', 'school_class', 'term')
    return render(request, 'allocations/allocation_list.html', {'allocations': allocations})