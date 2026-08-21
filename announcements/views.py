from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from accounts.decorators import management_required, feature_required
from .forms import AnnouncementForm
from .models import (
    Announcement,
    AnnouncementRead,
    get_announcements_for_user,
)


@management_required
@login_required
@feature_required("ANNOUNCEMENTS")
def post_announcement(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES)

        if form.is_valid():
            announcement = form.save(commit=False)

            # Always attach the announcement to the logged-in user's school
            announcement.school = request.user.school
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
@feature_required("ANNOUNCEMENTS")
def announcement_list(request):

    announcements = get_announcements_for_user(request.user)

    # Get IDs of announcements already read by this user
    read_ids = set(
        AnnouncementRead.objects.filter(
            user=request.user,
            announcement__in=announcements,
        ).values_list(
            'announcement_id',
            flat=True
        )
    )

    # Add read status to each announcement
    for announcement in announcements:
        announcement.is_read = announcement.id in read_ids

    return render(
        request,
        'announcements/announcement_list.html',
        {
            'announcements': announcements,
        }
    )


@login_required
@feature_required("ANNOUNCEMENTS")
def announcement_detail(request, announcement_id):

    announcement = get_object_or_404(
        Announcement,
        id=announcement_id,
        school=request.user.school,
    )

    # Check that the announcement is actually visible
    # to this user's role/audience.
    visible_ids = get_announcements_for_user(
        request.user
    ).filter(
        id=announcement.id
    ).values_list(
        'id',
        flat=True
    )

    if not visible_ids:
        return get_object_or_404(
            Announcement,
            id=None
        )

    # Record that this user has read the announcement.
    AnnouncementRead.objects.get_or_create(
        announcement=announcement,
        user=request.user,
    )

    return render(
        request,
        'announcements/announcement_detail.html',
        {
            'announcement': announcement,
        }
    )


@management_required
@login_required
@feature_required("ANNOUNCEMENTS")
def delete_announcement(request, announcement_id):

    announcement = get_object_or_404(
        Announcement,
        id=announcement_id,
        school=request.user.school,
    )

    if request.method == 'POST':
        announcement.delete()

    return redirect('announcement_list')


@management_required
@login_required
@feature_required("ANNOUNCEMENTS")
def toggle_announcement_pin(request, announcement_id):

    announcement = get_object_or_404(
        Announcement,
        id=announcement_id,
        school=request.user.school,
    )

    if request.method == 'POST':
        announcement.pinned = not announcement.pinned
        announcement.save(update_fields=['pinned'])

    return redirect('announcement_list')


@management_required
@login_required
@feature_required("ANNOUNCEMENTS")
def announcement_readers(request, announcement_id):

    announcement = get_object_or_404(
        Announcement,
        id=announcement_id,
        school=request.user.school,
    )

    # Determine who should receive this announcement.
    from accounts.models import User

    eligible_users = User.objects.filter(
        school=request.user.school,
        is_active=True,
    )

    if announcement.audience == Announcement.Audience.STUDENTS:

        eligible_users = eligible_users.filter(
            role=User.Role.STUDENT
        )

    elif announcement.audience == Announcement.Audience.STAFF:

        eligible_users = eligible_users.exclude(
            role=User.Role.STUDENT
        )

    # Users who have read the announcement
    read_user_ids = AnnouncementRead.objects.filter(
        announcement=announcement,
        user__school=request.user.school,
    ).values_list(
        'user_id',
        flat=True
    )

    readers = (
        eligible_users
        .filter(id__in=read_user_ids)
        .order_by('last_name', 'first_name')
    )

    unread_users = (
        eligible_users
        .exclude(id__in=read_user_ids)
        .order_by('last_name', 'first_name')
    )

    return render(
        request,
        'announcements/announcement_readers.html',
        {
            'announcement': announcement,

            'readers': readers,
            'unread_users': unread_users,

            'read_count': readers.count(),
            'unread_count': unread_users.count(),
            'total_recipients': eligible_users.count(),
        }
    )