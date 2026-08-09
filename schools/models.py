from django.db import models


class School(models.Model):
    """
    Represents a school using Paul SchoolHub.
    Each school will have its own students, teachers,
    classes, subjects, billing records, results, etc.
    """

    name = models.CharField(max_length=200)

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
        null=True
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


class SubscriptionPackage(models.Model):
    """
    Defines the packages available to schools.
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

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.get_name_display()


class SchoolSubscription(models.Model):
    """
    Connects a school to its current subscription package.
    """

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