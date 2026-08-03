from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import management_required
from .forms import AnnouncementForm
from .models import Announcement, get_announcements_for_user


@management_required
@login_required
def post_announcement(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()
            return redirect('announcement_list')
    else:
        form = AnnouncementForm()
    return render(request, 'announcements/post_announcement.html', {
        'form': form,
        'announcement_list_url': '/announcements/',
    })


@login_required
def announcement_list(request):
    announcements = get_announcements_for_user(request.user)
    return render(request, 'announcements/announcement_list.html', {
        'announcements': announcements,
    })


@management_required
@login_required
def delete_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if request.method == 'POST':
        announcement.delete()
    return redirect('announcement_list')