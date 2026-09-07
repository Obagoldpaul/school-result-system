from django.test import TestCase

# Create your tests here.
from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from academics.forms import SchoolSettingsForm
from schools.models import School, SubscriptionPackage, SchoolSubscription
from django.utils import timezone


class SchoolLogoOptimizationTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="Logo Test School",
            code="LOGO-001",
        )

        self.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.PREMIUM,
        )

        SchoolSubscription.objects.create(
            school=self.school,
            package=self.package,
            start_date=timezone.now().date(),
        )

    def create_large_logo(self):
        image = Image.new(
            "RGB",
            (2400, 1800),
            "white",
        )

        output = BytesIO()

        image.save(
            output,
            format="JPEG",
            quality=95,
        )

        return SimpleUploadedFile(
            "large-school-logo.jpg",
            output.getvalue(),
            content_type="image/jpeg",
        )

    def test_school_logo_is_optimized_before_validation(self):
        uploaded_logo = self.create_large_logo()

        form = SchoolSettingsForm(
            data={
                "school_name": "Logo Test School",
                "school_address": "Test Address",
                "school_phone": "08000000000",
                "school_email": "school@example.com",
                "primary_color": "#ffc837",
                "secondary_color": "#201e1e",
                "report_card_heading": "School Report",
            },
            files={
                "school_logo": uploaded_logo,
            },
            school=self.school,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        optimized = form.cleaned_data["school_logo"]

        optimized.seek(0)

        image = Image.open(optimized)

        self.assertLessEqual(
            image.width,
            1600,
        )

        self.assertLessEqual(
            image.height,
            1600,
        )

        self.assertLessEqual(
            optimized.size,
            2 * 1024 * 1024,
        )
        
class PrincipalSignatureOptimizationTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="Signature Test School",
            code="SIGN-001",
        )

        self.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.PREMIUM,
        )

        SchoolSubscription.objects.create(
            school=self.school,
            package=self.package,
            start_date=timezone.now().date(),
        )

    def create_large_signature(self):
        image = Image.new(
            "RGB",
            (2400, 1800),
            "white",
        )

        output = BytesIO()

        image.save(
            output,
            format="JPEG",
            quality=95,
        )

        return SimpleUploadedFile(
            "large-principal-signature.jpg",
            output.getvalue(),
            content_type="image/jpeg",
        )

    def test_principal_signature_is_optimized_before_validation(self):
        uploaded_signature = self.create_large_signature()

        form = SchoolSettingsForm(
            data={
                "school_name": "Signature Test School",
                "school_address": "Test Address",
                "school_phone": "08000000000",
                "school_email": "school@example.com",
                "primary_color": "#ffc837",
                "secondary_color": "#201e1e",
                "report_card_heading": "School Report",
            },
            files={
                "principal_signature": uploaded_signature,
            },
            school=self.school,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        optimized = form.cleaned_data["principal_signature"]

        optimized.seek(0)

        image = Image.open(optimized)

        self.assertLessEqual(
            image.width,
            1600,
        )

        self.assertLessEqual(
            image.height,
            1600,
        )

        self.assertLessEqual(
            optimized.size,
            2 * 1024 * 1024,
        )