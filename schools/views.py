from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import Count
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone


from accounts.decorators import platform_admin_required

from .forms import (
    SchoolRegistrationForm,
    EditSchoolForm,
    SchoolSubscriptionForm,
    PlatformSettingsForm,
    AssignSchoolRoleForm,
    SchoolRoleForm,
    CreateSchoolUserForm,
    EditSchoolUserForm,
)
from .models import (
    School,
    SchoolSubscription,
    SubscriptionPackage,
    PlatformSettings,
    SchoolRole,
    Permission,
)

from students.models import SchoolClass
from subjects.models import Subject
from .utils import (
    calculate_subscription_end_date,
    get_subscription_status,
)

@login_required
@platform_admin_required
def platform_dashboard(request):
    """
    Main dashboard for Paul SchoolHub platform administrators.

    Platform administrators manage the entire SchoolHub platform,
    including schools, packages, features, and subscriptions.
    """

    # ---------------------------------------------------------
    # SCHOOLS
    # ---------------------------------------------------------

    schools = list(
        School.objects.select_related(
            "subscription",
            "subscription__package",
        ).annotate(
            user_count=Count("users")
        ).order_by("name")
    )

    # ---------------------------------------------------------
    # SUBSCRIPTION STATUS
    # ---------------------------------------------------------

    for school in schools:

        subscription = getattr(
            school,
            "subscription",
            None,
        )

        school.subscription_status = get_subscription_status(
            subscription
        )

    # ---------------------------------------------------------
    # DASHBOARD CONTEXT
    # ---------------------------------------------------------

    context = {

        "schools": schools,

        "schools_count": School.objects.count(),

        "active_schools_count": School.objects.filter(
            is_active=True
        ).count(),

        "inactive_schools_count": School.objects.filter(
            is_active=False
        ).count(),

        "packages_count": SubscriptionPackage.objects.filter(
            is_active=True
        ).count(),

        "subscriptions_count": SchoolSubscription.objects.filter(
            is_active=True
        ).count(),

        "basic_schools_count": SchoolSubscription.objects.filter(
            is_active=True,
            package__name=SubscriptionPackage.PackageType.BASIC,
        ).count(),

        "standard_schools_count": SchoolSubscription.objects.filter(
            is_active=True,
            package__name=SubscriptionPackage.PackageType.STANDARD,
        ).count(),

        "premium_schools_count": SchoolSubscription.objects.filter(
            is_active=True,
            package__name=SubscriptionPackage.PackageType.PREMIUM,
        ).count(),

        "is_platform_admin": True,
    }

    return render(
        request,
        "schools/platform_dashboard.html",
        context,
    )

@login_required
@platform_admin_required
def manage_schools(request):
    """
    Display all schools registered on Paul SchoolHub
    for Platform Administrators.
    """

    User = get_user_model()

    schools = School.objects.select_related(
        "subscription",
        "subscription__package",
    ).annotate(
        total_users=Count("users"),
        total_students=Count(
            "users",
            filter=models.Q(users__role=User.Role.STUDENT),
        ),
        total_teachers=Count(
            "users",
            filter=models.Q(users__role=User.Role.TEACHER),
        ),
        total_admins=Count(
            "users",
            filter=models.Q(users__role=User.Role.ADMIN),
        ),
    ).order_by("name")

    context = {
        "schools": schools,
        "schools_count": schools.count(),
        "is_platform_admin": True,
    }

    return render(
        request,
        "schools/manage_schools.html",
        context,
    )

@login_required
@platform_admin_required
def manage_school_roles(request, school_id):
    """
    Display all configurable roles belonging to a specific school.
    Platform administrators only.
    """

    school = get_object_or_404(
        School,
        id=school_id,
    )

    roles = SchoolRole.objects.filter(
        school=school
    ).prefetch_related(
        "permissions"
    )

    return render(
        request,
        "schools/manage_school_roles.html",
        {
            "school": school,
            "roles": roles,
            "is_platform_admin": True,
        },
    )


@login_required
@platform_admin_required
def create_school_role(request, school_id):
    """
    Create a configurable role for a specific school.

    Each custom school role is based on one of the four
    fundamental account types:

        ADMIN
        TEACHER
        STUDENT
        PLATFORM_ADMIN

    The base role determines the user's fundamental account type,
    while the permissions assigned to the SchoolRole determine
    what the user can actually do within the school.
    """

    school = get_object_or_404(
        School,
        id=school_id,
    )

    if request.method == "POST":

        form = SchoolRoleForm(
            request.POST,
            school=school,
        )

        if form.is_valid():

            role = form.save(
                commit=False
            )

            role.school = school
            role.save()

            form.save_m2m()

            messages.success(
                request,
                f"Role '{role.name}' was created successfully.",
            )

            return redirect(
                "manage_school_roles",
                school_id=school.id,
            )

    else:

        form = SchoolRoleForm(
            school=school,
        )

    return render(
        request,
        "schools/create_school_role.html",
        {
            "school": school,
            "form": form,
            "is_platform_admin": True,
        },
    )
    
@login_required
@platform_admin_required
def edit_school_role(request, school_id, role_id):
    """
    Edit a configurable SchoolRole belonging to a specific school.
    Platform administrators only.
    """

    school = get_object_or_404(
        School,
        id=school_id,
    )

    role = get_object_or_404(
        SchoolRole,
        id=role_id,
        school=school,
    )

    if request.method == "POST":

        form = SchoolRoleForm(
            request.POST,
            instance=role,
            school=school,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                f"Role '{role.name}' was updated successfully.",
            )

            return redirect(
                "manage_school_roles",
                school_id=school.id,
            )

    else:

        form = SchoolRoleForm(
            instance=role,
            school=school,
        )

    return render(
        request,
        "schools/edit_school_role.html",
        {
            "school": school,
            "role": role,
            "form": form,
            "is_platform_admin": True,
        },
    )

@login_required
@platform_admin_required
def delete_school_role(request, school_id, role_id):
    """
    Delete a configurable SchoolRole belonging to a specific school.

    Platform administrators only.

    Users assigned to the role are not deleted. Their school_role
    is cleared before the role itself is removed.
    """

    school = get_object_or_404(
        School,
        id=school_id,
    )

    role = get_object_or_404(
        SchoolRole,
        id=role_id,
        school=school,
    )

    # Only allow deletion through POST.
    if request.method != "POST":
        return redirect(
            "manage_school_roles",
            school_id=school.id,
        )

    role_name = role.name

    # Remove the role from users currently assigned to it.
    User = get_user_model()

    User.objects.filter(
        school=school,
        school_role=role,
    ).update(
        school_role=None,
    )

    # Delete the role itself.
    role.delete()

    messages.success(
        request,
        f"Role '{role_name}' was deleted successfully.",
    )

    return redirect(
        "manage_school_roles",
        school_id=school.id,
    )

@login_required
@platform_admin_required
def manage_role_permissions(request, school_id, role_id):
    """
    Assign permissions to a specific school role.
    """

    school = get_object_or_404(
        School,
        id=school_id,
    )

    role = get_object_or_404(
        SchoolRole,
        id=role_id,
        school=school,
    )

    permissions = Permission.objects.filter(
        is_active=True
    ).order_by(
        "module",
        "name",
    )

    if request.method == "POST":

        permission_ids = request.POST.getlist(
            "permissions"
        )

        selected_permissions = Permission.objects.filter(
            id__in=permission_ids,
            is_active=True,
        )

        role.permissions.set(
            selected_permissions
        )

        messages.success(
            request,
            f"Permissions for '{role.name}' were updated successfully."
        )

        return redirect(
            "manage_role_permissions",
            school_id=school.id,
            role_id=role.id,
        )

    selected_permissions = set(
        role.permissions.values_list(
            "id",
            flat=True,
        )
    )

    grouped_permissions = {}

    for permission in permissions:

        grouped_permissions.setdefault(
            permission.module,
            []
        ).append(
            permission
        )

    return render(
        request,
        "schools/manage_role_permissions.html",
        {
            "school": school,
            "role": role,
            "grouped_permissions": grouped_permissions,
            "selected_permissions": selected_permissions,
            "is_platform_admin": True,
        },
    )

@login_required
@platform_admin_required
def school_users(request, school_id):
    """
    Display all users belonging to a specific school.

    The system role represents the user's fundamental account type:

        ADMIN
        TEACHER
        STUDENT

    SchoolRole provides the school's customised role, such as:

        Principal
        Vice Principal
        Headmaster
        Class Teacher
        Subject Teacher
        Bursar
        etc.
    """

    school = get_object_or_404(
        School,
        id=school_id,
    )

    User = get_user_model()

    users = (
        User.objects
        .filter(school=school)
        .select_related("school_role")
        .order_by(
            "role",
            "last_name",
            "first_name",
            "username",
        )
    )

    context = {
        "school": school,
        "users": users,

        # -----------------------------------------
        # TOTAL USERS
        # -----------------------------------------

        "total_users": users.count(),

        # -----------------------------------------
        # SYSTEM ROLE COUNTS
        # -----------------------------------------

        "total_students": users.filter(
            role=User.Role.STUDENT
        ).count(),

        "total_teachers": users.filter(
            role=User.Role.TEACHER
        ).count(),

        "total_management": users.filter(
            role=User.Role.ADMIN
        ).count(),

        # -----------------------------------------
        # USER STATUS
        # -----------------------------------------

        "active_users": users.filter(
            is_active=True
        ).count(),

        "inactive_users": users.filter(
            is_active=False
        ).count(),

        "is_platform_admin": True,
    }

    return render(
        request,
        "schools/school_users.html",
        context,
    )

@login_required
@platform_admin_required
def create_school_user(request, school_id):
    """
    Create an ADMIN user account for a specific school.

    Teacher and Student accounts continue to be created
    through their existing registration modules.
    """

    school = get_object_or_404(
        School,
        id=school_id,
    )

    if request.method == "POST":

        form = CreateSchoolUserForm(
            request.POST,
            school=school,
        )

        if form.is_valid():

            user = form.save()

            messages.success(
                request,
                f"{user.get_full_name() or user.username} "
                f"was created successfully for {school.name}."
            )

            return redirect(
                "school_users",
                school_id=school.id,
            )

    else:

        form = CreateSchoolUserForm(
            school=school,
        )

    return render(
        request,
        "schools/create_school_user.html",
        {
            "school": school,
            "form": form,
            "is_platform_admin": True,
        },
    )

@login_required
@platform_admin_required
def edit_school_user(request, school_id, user_id):
    """
    Edit an administrative user belonging to a specific school.

    This view does not change:
        - Account Type
        - School
        - School Role
        - Password

    Those responsibilities are handled separately.
    """

    User = get_user_model()

    school = get_object_or_404(
        School,
        id=school_id,
    )

    user = get_object_or_404(
        User,
        id=user_id,
        school=school,
        role=User.Role.ADMIN,
    )

    if request.method == "POST":

        form = EditSchoolUserForm(
            request.POST,
            instance=user,
            school=school,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                f"{user.get_full_name() or user.username} "
                f"was updated successfully."
            )

            return redirect(
                "school_users",
                school_id=school.id,
            )

    else:

        form = EditSchoolUserForm(
            instance=user,
            school=school,
        )

    return render(
        request,
        "schools/edit_school_user.html",
        {
            "school": school,
            "user_obj": user,
            "form": form,
            "is_platform_admin": True,
        },
    )

@login_required
@platform_admin_required
def assign_user_school_role(request, school_id, user_id):
    """
    Assign a configurable SchoolRole to a user belonging
    to the specified school.

    Platform administrators only for now.
    """

    User = get_user_model()

    school = get_object_or_404(
        School,
        id=school_id,
    )

    user = get_object_or_404(
        User,
        id=user_id,
        school=school,
    )

    if request.method == "POST":

        form = AssignSchoolRoleForm(
            request.POST,
            instance=user,
            school=school,
        )

        if form.is_valid():

            selected_role = form.cleaned_data.get("school_role")

            # Extra school-isolation protection
            if (
                selected_role is not None
                and selected_role.school_id != school.id
            ):
                messages.error(
                    request,
                    "Invalid role selected for this school.",
                )

                return redirect(
                    "assign_user_school_role",
                    school_id=school.id,
                    user_id=user.id,
                )

            form.save()

            if selected_role:
                messages.success(
                    request,
                    f"{user.get_full_name() or user.username} "
                    f"was assigned the '{selected_role.name}' role."
                )
            else:
                messages.success(
                    request,
                    f"The School Role for "
                    f"{user.get_full_name() or user.username} "
                    f"was removed."
                )

            return redirect(
                "school_users",
                school_id=school.id,
            )

    else:

        form = AssignSchoolRoleForm(
            instance=user,
            school=school,
        )

    return render(
        request,
        "schools/assign_user_school_role.html",
        {
            "school": school,
            "user_obj": user,
            "form": form,
            "is_platform_admin": True,
        },
    )

@login_required
@platform_admin_required
def school_detail(request, school_id):
    """
    Platform administrator view for managing a specific school.

    The four fundamental system roles are:

        PLATFORM_ADMIN
        ADMIN
        TEACHER
        STUDENT

    School-specific positions such as Principal, Vice Principal,
    Headmaster, Class Teacher and Subject Teacher are represented
    through SchoolRole.
    """

    school = get_object_or_404(
        School.objects.select_related(
            "subscription",
            "subscription__package",
        ),
        id=school_id,
    )

    User = get_user_model()

    # -----------------------------------------
    # USERS BELONGING TO THIS SCHOOL
    # -----------------------------------------

    school_users = User.objects.filter(
        school=school
    )

    # -----------------------------------------
    # SYSTEM ROLE COUNTS
    # -----------------------------------------

    total_users = school_users.count()

    total_students = school_users.filter(
        role=User.Role.STUDENT,
    ).count()

    total_teachers = school_users.filter(
        role=User.Role.TEACHER,
    ).count()

    total_admins = school_users.filter(
        role=User.Role.ADMIN,
    ).count()

    context = {
        "school": school,

        "total_users": total_users,
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_admins": total_admins,

        "is_platform_admin": True,
    }

    return render(
        request,
        "schools/school_detail.html",
        context,
    )
    
@login_required
@platform_admin_required
def edit_school(request, school_id):
    """
    Allow Platform Administrators to edit the basic information
    of an existing school.

    This view does not change:
        - Subscription
        - School users
        - Academic structure
    """

    school = get_object_or_404(
        School,
        id=school_id,
    )

    if request.method == "POST":

        form = EditSchoolForm(
            request.POST,
            request.FILES,
            instance=school,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                f"{school.name}'s information was updated successfully."
            )

            return redirect(
                "school_detail",
                school_id=school.id,
            )

    else:

        form = EditSchoolForm(
            instance=school,
        )

    return render(
        request,
        "schools/edit_school.html",
        {
            "school": school,
            "form": form,
            "is_platform_admin": True,
        },
    )

@login_required
@platform_admin_required
def toggle_school_status(request, school_id):
    """
    Activate or deactivate a school from the platform administration area.
    """

    if request.method != "POST":
        return redirect("manage_schools")

    school = get_object_or_404(
        School,
        id=school_id,
    )

    school.is_active = not school.is_active
    school.save(update_fields=["is_active"])

    if school.is_active:
        messages.success(
            request,
            f"{school.name} has been activated successfully."
        )
    else:
        messages.warning(
            request,
            f"{school.name} has been deactivated."
        )

    return redirect("manage_schools")

@login_required
@platform_admin_required
def platform_settings(request):
    """
    Allow Platform Administrators to manage
    Paul SchoolHub platform branding.
    """

    settings, created = PlatformSettings.objects.get_or_create(
        pk=1
    )

    if request.method == "POST":
        form = PlatformSettingsForm(
            request.POST,
            request.FILES,
            instance=settings,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Platform settings updated successfully."
            )

            return redirect("platform_settings")

    else:
        form = PlatformSettingsForm(
            instance=settings,
        )

    return render(
        request,
        "schools/platform_settings.html",
        {
            "form": form,
            "platform_settings": settings,
            "is_platform_admin": True,
        },
    )

def setup_new_school(school):
    """
    Create the standard academic structure for a newly
    onboarded school.

    This creates:
        - Default classes
        - Default subjects

    It deliberately does NOT create ClassSubject records.
    Subject-to-class assignment remains the responsibility
    of the school's administrator.

    Existing subjects are reused rather than duplicated.
    """

    # ---------------------------------------------------------
    # STANDARD CLASSES
    # ---------------------------------------------------------

    primary_classes = [
        ("CRECHE", SchoolClass.Section.PRE_PRIMARY),
        ("TODDLER", SchoolClass.Section.PRE_PRIMARY),
        ("PRESCHOOL 1", SchoolClass.Section.PRE_PRIMARY),
        ("PRESCHOOL 2", SchoolClass.Section.PRE_PRIMARY),

        ("BASIC 1", SchoolClass.Section.PRIMARY),
        ("BASIC 2", SchoolClass.Section.PRIMARY),
        ("BASIC 3", SchoolClass.Section.PRIMARY),
        ("BASIC 4", SchoolClass.Section.PRIMARY),
        ("BASIC 5", SchoolClass.Section.PRIMARY),
        ("BASIC 6", SchoolClass.Section.PRIMARY),
    ]

    secondary_classes = [
        ("JSS 1", SchoolClass.Section.JUNIOR_SECONDARY),
        ("JSS 2", SchoolClass.Section.JUNIOR_SECONDARY),
        ("JSS 3", SchoolClass.Section.JUNIOR_SECONDARY),

        ("SS 1", SchoolClass.Section.SENIOR_SECONDARY),
        ("SS 2", SchoolClass.Section.SENIOR_SECONDARY),
        ("SS 3", SchoolClass.Section.SENIOR_SECONDARY),
    ]

    if school.school_type == School.SchoolType.PRIMARY:
        classes_to_create = primary_classes

    elif school.school_type == School.SchoolType.SECONDARY:
        classes_to_create = secondary_classes

    else:
        classes_to_create = primary_classes + secondary_classes

    for class_name, section in classes_to_create:
        SchoolClass.objects.get_or_create(
            school=school,
            name=class_name,
            defaults={
                "section": section,
            },
        )

    # ---------------------------------------------------------
    # STANDARD PRIMARY / PRE-PRIMARY SUBJECTS
    # ---------------------------------------------------------
    #
    # Combined subjects are parents.
    # Existing component subjects are reused and linked
    # to their appropriate parent.
    #
    # get_or_create() prevents duplicate subjects when
    # the setup function is run again.
    # ---------------------------------------------------------

    primary_subjects = [
        {
            "name": "Citizenship Education",
            "code": "CITE",
            "components": [
                ("Civic Education", "CE"),
                ("Social Studies", "SOS"),
            ],
        },
        {
            "name": "Basic Science and Technology",
            "code": "BST",
            "components": [
                ("Basic Science", "BSC"),
                ("Basic Technology", "BT"),
            ],
        },
        {
            "name": "Pre-Vocational Studies",
            "code": "PVS",
            "components": [
                ("Home Economics", "HE"),
                ("Agricultural Science", "AGS"),
            ],
        },
        {
            "name": "Digital Technology",
            "code": "DT",
            "components": [],
        },
        {
            "name": "Physical Health Education",
            "code": "PHE",
            "components": [],
        },
        {
            "name": "Nigerian History",
            "code": "NH",
            "components": [],
        },
        {
            "name": "Literacy",
            "code": "LIT",
            "components": [],
        },
        {
            "name": "Numeracy",
            "code": "NUM",
            "components": [],
        },
        {
            "name": "Cultural Studies",
            "code": "CULT",
            "components": [],
        },
        {
            "name": "Practical Life",
            "code": "PL",
            "components": [
                ("Social Norms", "SN"),
                ("Health Habit", "HH"),
            ],
        },
        {
            "name": "Sensorial",
            "code": "SEN",
            "components": [
                ("Expressive Art & Design", "EAD"),
                ("Rhymes", "RHY"),
            ],
        },
        {
            "name": "Creative Art",
            "code": "CA",
            "components": [
                ("Handwriting", "HW"),
                ("Music", "MSC"),
            ],
        },
        {
            "name": "Literature",
            "code": "LITENG",
            "components": [],
        },
        {
            "name": "Grammar",
            "code": "GRAM",
            "components": [],
        },
        {
            "name": "Fine Art",
            "code": "FA",
            "components": [],
        },
    ]

    # ---------------------------------------------------------
    # CREATE PRIMARY SUBJECTS
    # ---------------------------------------------------------

    if school.school_type in [
        School.SchoolType.PRIMARY,
        School.SchoolType.PRIMARY_SECONDARY,
    ]:

        for subject_data in primary_subjects:

            # -------------------------------------------------
            # CREATE / REUSE PARENT SUBJECT
            # -------------------------------------------------

            parent, _ = Subject.objects.get_or_create(
                school=school,
                name=subject_data["name"],
                level=Subject.SubjectLevel.PRIMARY,
                defaults={
                    "code": subject_data["code"],
                    "is_elective": False,
                    "is_active": True,
                    "parent": None,
                },
            )

            # -------------------------------------------------
            # CREATE / REUSE COMPONENT SUBJECTS
            # -------------------------------------------------

            for component_name, component_code in subject_data["components"]:

                component, _ = Subject.objects.get_or_create(
                    school=school,
                    name=component_name,
                    level=Subject.SubjectLevel.PRIMARY,
                    defaults={
                        "code": component_code,
                        "is_elective": False,
                        "is_active": True,
                        "parent": parent,
                    },
                )

                # If the component already existed without a
                # parent, attach it to the appropriate parent.
                if component.parent_id is None:
                    component.parent = parent
                    component.save(
                        update_fields=["parent"]
                    )

    # ---------------------------------------------------------
    # STANDARD SECONDARY SUBJECTS
    # ---------------------------------------------------------

    secondary_subjects = [
        ("Agricultural Science", "AGS"),
        ("Agriculture", "AGR"),
        ("Basic Science and Technology", "BST"),
        ("Biology", "BIO"),
        ("Business Studies", "BSTD"),
        ("Chemistry", "CHM"),
        ("Christian Religious Studies", "CRS"),
        ("Civic Education", "CE"),
        ("Commerce", "CME"),
        ("Computer Studies", "ICT"),
        ("Cultural and Creative Arts", "CCA"),
        ("Data Processing", "DAP"),
        ("Economics", "ECON"),
        ("English Language", "ENG"),
        ("Financial Accounting", "FACC"),
        ("French", "FRH"),
        ("Further Mathematics", "FMTH"),
        ("General Paper", "GRP"),
        ("Geography", "GEO"),
        ("Government", "GOV"),
        ("Hausa", "HUS"),
        ("History", "HST"),
        ("Home Economics", "HE"),
        ("Igbo", "IGB"),
        ("Islamic Religious Studies", "IRS"),
        ("Literature in English", "LTENG"),
        ("Marketing", "MRKT"),
        ("Mathematics", "MTH"),
        ("Music", "MSC"),
        ("National Values Education", "NVE"),
        ("Physical and Health Education", "PHE"),
        ("Physics", "PHY"),
        ("Pre-Vocational Studies", "PVS"),
        ("Security Education", "SE"),
        ("Social Studies", "SS"),
        ("Technical Drawing", "TCD"),
        ("Yoruba", "YRB"),
    ]

    # ---------------------------------------------------------
    # CREATE SECONDARY SUBJECTS
    # ---------------------------------------------------------

    if school.school_type in [
        School.SchoolType.SECONDARY,
        School.SchoolType.PRIMARY_SECONDARY,
    ]:

        for name, code in secondary_subjects:

            Subject.objects.get_or_create(
                school=school,
                name=name,
                level=Subject.SubjectLevel.SECONDARY,
                defaults={
                    "code": code,
                    "is_elective": False,
                    "is_active": True,
                    "parent": None,
                },
            )
    # ---------------------------------------------------------
    # DEFAULT SCHOOL ROLES AND PERMISSIONS
    # ---------------------------------------------------------
    #
    # Permission records are global and reused.
    # SchoolRole records belong to this specific school.
    #
    # Default roles:
    #   - Principal
    #   - Bursar
    #   - Class Teacher
    #   - Teacher
    #
    # Other roles can be created manually by the school.
    # ---------------------------------------------------------

    default_roles = {
        "Principal": {
            "base_role": SchoolRole.BaseRole.ADMIN,
            "permission_codes": None,  # All active permissions
        },

        "Bursar": {
            "base_role": SchoolRole.BaseRole.ADMIN,
            "permission_codes": [
                "billing.delete_payment",
                "billing.edit_payment",
                "billing.manage",
                "billing.record_payment",
                "billing.view",
                "billing.view_reports",
            ],
        },

        "Class Teacher": {
            "base_role": SchoolRole.BaseRole.TEACHER,
            "permission_codes": [
                "academics.view",
                "attendance.manage",
                "attendance.mark",
                "attendance.view",
                "class_management.view",
                "classes.manage",
                "classes.view",
                "reports.teacher_remark",
                "reports.view",
                "scores.change",
                "scores.enter",
                "scores.submit",
                "scores.view",
                "students.change",
                "students.view",
                "subjects.view",
                "teachers.view",
            ],
        },

        "Teacher": {
            "base_role": SchoolRole.BaseRole.TEACHER,
            "permission_codes": [
                "academics.view",
                "attendance.mark",
                "attendance.view",
                "reports.teacher_remark",
                "reports.view",
                "scores.change",
                "scores.enter",
                "scores.submit",
                "scores.view",
                "students.view",
                "subjects.view",
            ],
        },
    }

    for role_name, role_data in default_roles.items():

        role, _ = SchoolRole.objects.get_or_create(
            school=school,
            name=role_name,
            base_role=role_data["base_role"],
            defaults={
                "is_active": True,
            },
        )

        role.is_active = True
        role.save(update_fields=["is_active"])

        if role_data["permission_codes"] is None:
            permissions = Permission.objects.filter(
                is_active=True,
            )
        else:
            permissions = Permission.objects.filter(
                code__in=role_data["permission_codes"],
                is_active=True,
            )

        role.permissions.set(permissions)
    
    
@login_required
@platform_admin_required
def create_school(request):
    """
    Register a new school together with its first administrator
    and subscription.
    """

    if request.method == "POST":
        form = SchoolRegistrationForm(request.POST)

        if form.is_valid():

            User = get_user_model()

            try:
                with transaction.atomic():

                    # -------------------------------------------------
                    # CREATE SCHOOL
                    # -------------------------------------------------

                    school = School.objects.create(
                        name=form.cleaned_data["school_name"].strip(),
                        code=form.cleaned_data["school_code"],
                        school_type=form.cleaned_data["school_type"],
                        email=form.cleaned_data["email"],
                        phone=form.cleaned_data["phone"].strip(),
                        address=form.cleaned_data["address"].strip(),
                    )
                    
                    # -------------------------------------------------
                    # CREATE DEFAULT ACADEMIC STRUCTURE
                    # -------------------------------------------------

                    setup_new_school(school)

                    # -------------------------------------------------
                    # CREATE SUBSCRIPTION
                    # -------------------------------------------------

                    subscription_start_date = timezone.now().date()

                    subscription_billing_cycle = form.cleaned_data[
                        "billing_cycle"
                    ]

                    subscription_end_date = calculate_subscription_end_date(
                        subscription_start_date,
                        subscription_billing_cycle,
                    )

                    SchoolSubscription.objects.create(
                        school=school,
                        package=form.cleaned_data["package"],
                        billing_cycle=subscription_billing_cycle,
                        start_date=subscription_start_date,
                        end_date=subscription_end_date,
                        is_active=True,
                    )

                    # -------------------------------------------------
                    # CREATE SCHOOL ADMINISTRATOR
                    # -------------------------------------------------

                    administrator = User.objects.create_user(
                        username=form.cleaned_data["admin_username"],
                        email=form.cleaned_data["admin_email"],
                        password=form.cleaned_data["admin_password"],
                        first_name=form.cleaned_data["admin_first_name"],
                        last_name=form.cleaned_data["admin_last_name"],
                        role=User.Role.ADMIN,
                        school=school,
                    )

                messages.success(
                    request,
                    f"{school.name} was registered successfully."
                )

                return redirect("platform_dashboard")

            except Exception:
                messages.error(
                    request,
                    "The school could not be registered. "
                    "Please try again."
                )

    else:
        form = SchoolRegistrationForm()

    return render(
        request,
        "schools/school_create.html",
        {
            "form": form,
        },
    )


@login_required
@platform_admin_required
def edit_subscription(request, school_id):
    """
    Allow Platform Administrators to change an existing
    school's subscription package, billing cycle, and start date.

    End date is calculated automatically:
        Termly -> 3 calendar months + 14 days
        Yearly -> 1 calendar year
    """

    school = get_object_or_404(
        School,
        id=school_id,
    )

    subscription = school.subscription

    if request.method == "POST":

        form = SchoolSubscriptionForm(
            request.POST,
            instance=subscription,
        )

        if form.is_valid():

            subscription = form.save(
                commit=False
            )

            subscription.end_date = calculate_subscription_end_date(
                subscription.start_date,
                subscription.billing_cycle,
            )

            subscription.save()

            messages.success(
                request,
                f"{school.name}'s subscription was updated successfully."
            )

            return redirect(
                "platform_dashboard"
            )

    else:

        form = SchoolSubscriptionForm(
            instance=subscription,
        )

    return render(
        request,
        "schools/edit_subscription.html",
        {
            "school": school,
            "subscription": subscription,
            "form": form,
        },
    )