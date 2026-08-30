from django.db import models
from core.validators import validate_image_size


class Feature(models.Model):
    """
    Represents a feature/functionality available in Paul SchoolHub.

    Features are assigned to subscription packages.
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique internal code used to identify this feature."
    )

    name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PlatformSettings(models.Model):
    """
    Global branding and settings for the Paul SchoolHub platform.
    This is separate from individual school branding.
    """

    platform_name = models.CharField(
        max_length=200,
        default="Paul SchoolHub",
    )

    platform_logo = models.ImageField(
        upload_to="platform/",
        blank=True,
        null=True,
    )

    platform_primary_color = models.CharField(
        max_length=7,
        default="#16401C",
    )

    platform_secondary_color = models.CharField(
        max_length=7,
        default="#F0F2F0",
    )

    platform_footer = models.CharField(
        max_length=300,
        default="Powered by Paul Media",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.platform_name

class School(models.Model):
    """
    Represents a school using Paul SchoolHub.

    Each school will eventually have its own students, teachers,
    classes, subjects, billing records, results, etc.
    """
    
    class SchoolType(models.TextChoices):
        PRIMARY = "PRIMARY", "Primary"
        SECONDARY = "SECONDARY", "Secondary"
        PRIMARY_SECONDARY = "PRIMARY_SECONDARY", "Primary & Secondary"

    school_type = models.CharField(
        max_length=20,
        choices=SchoolType.choices,
        default=SchoolType.SECONDARY,
        help_text="The academic level(s) offered by this school.",
    )

    name = models.CharField(
        max_length=200
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique identifier for this school."
    )

    email = models.EmailField(
        blank=True
    )

    phone = models.CharField(
        max_length=30,
        blank=True
    )

    address = models.TextField(
        blank=True
    )

    logo = models.ImageField(
        upload_to="schools/logos/",
        blank=True,
        null=True,
        validators=[validate_image_size]
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.name

class Permission(models.Model):
    """
    Represents a specific action that a school user can perform.

    Permissions are assigned to SchoolRole objects rather than directly
    to individual users.
    """

    code = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique internal permission code.",
    )

    name = models.CharField(
        max_length=150,
        help_text="Human-readable permission name.",
    )

    description = models.TextField(
        blank=True,
    )

    module = models.CharField(
        max_length=50,
        help_text="Module this permission belongs to, e.g. Students, Billing, Scores.",
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["module", "name"]

    def __str__(self):
        return self.name

class SchoolRole(models.Model):
    """
    A configurable role belonging to one specific school.

    SchoolRole is a custom permission profile built on top of
    one of the three school-level system roles:

        ADMIN
        TEACHER
        STUDENT

    Examples:

        ADMIN     → Principal
        ADMIN     → Vice Principal
        ADMIN     → Bursar
        ADMIN     → Examination Officer

        TEACHER   → Mathematics Teacher
        TEACHER   → Class Teacher
        TEACHER   → Senior Teacher

        STUDENT   → Student
    """

    class BaseRole(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        TEACHER = "TEACHER", "Teacher"
        STUDENT = "STUDENT", "Student"

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="roles",
    )

    name = models.CharField(
        max_length=100,
    )

    base_role = models.CharField(
        max_length=20,
        choices=BaseRole.choices,
    )

    description = models.TextField(
        blank=True,
    )

    permissions = models.ManyToManyField(
        "Permission",
        blank=True,
        related_name="school_roles",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["school", "name"],
                name="unique_school_role_name",
            )
        ]

        ordering = ["name"]

    def __str__(self):
        return f"{self.school.name} - {self.name}"

class SubscriptionPackage(models.Model):
    """
    Defines the subscription packages available to schools.
    """

    class PackageType(models.TextChoices):
        BASIC = "BASIC", "Basic"
        STANDARD = "STANDARD", "Standard"
        PREMIUM = "PREMIUM", "Premium"

    name = models.CharField(
        max_length=20,
        choices=PackageType.choices,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    features = models.ManyToManyField(
        Feature,
        blank=True,
        related_name="packages"
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.get_name_display()


class SchoolSubscription(models.Model):

    class BillingCycle(models.TextChoices):
        TERMLY = "TERMLY", "Termly"
        YEARLY = "YEARLY", "Yearly"

    school = models.OneToOneField(
        School,
        on_delete=models.CASCADE,
        related_name="subscription"
    )

    package = models.ForeignKey(
        SubscriptionPackage,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )

    billing_cycle = models.CharField(
        max_length=10,
        choices=BillingCycle.choices,
        default=BillingCycle.TERMLY,
    )

    start_date = models.DateField()

    end_date = models.DateField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.school} - {self.package}"