from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.decorators import management_required
from .forms import AnnouncementForm
from .models import Announcement, get_announcements_for_user


@management_required
@login_required
def post_announcement(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
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