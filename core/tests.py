from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
import json

from core.utils.image_optimizer import optimize_image

from unittest.mock import patch

from django.conf import settings
from django.core.mail import EmailMessage
from django.test import SimpleTestCase

from core.services.brevo_email_backend import BrevoEmailBackend

class BrevoEmailBackendSenderTests(SimpleTestCase):

    @patch("core.services.brevo_email_backend.urllib.request.urlopen")
    def test_custom_sender_name_is_used_with_configured_address(
        self,
        mock_urlopen,
    ):
        mock_urlopen.return_value.__enter__.return_value.status = 201

        message = EmailMessage(
            subject="Set Up Your Password",
            body="Password setup link",
            from_email=(
                f"Great Goshenland Blossom School via Paul SchoolHub "
                f"<{settings.DEFAULT_FROM_EMAIL.split('<')[-1].rstrip('>')}>"
            ),
            to=["student@example.com"],
        )

        backend = BrevoEmailBackend()
        backend.send_messages([message])

        import json

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))

        self.assertEqual(
            payload["sender"]["name"],
            "Great Goshenland Blossom School via Paul SchoolHub",
        )
        self.assertEqual(
            payload["sender"]["email"],
            settings.DEFAULT_FROM_EMAIL.split("<")[-1].rstrip(">"),
        )

    @patch("core.services.brevo_email_backend.urllib.request.urlopen")
    def test_default_sender_name_is_preserved_for_other_emails(
        self,
        mock_urlopen,
    ):
        mock_urlopen.return_value.__enter__.return_value.status = 201

        message = EmailMessage(
            subject="Ordinary email",
            body="Test message",
            from_email=None,
            to=["recipient@example.com"],
        )

        backend = BrevoEmailBackend()
        backend.send_messages([message])

        import json

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))

        self.assertEqual(payload["sender"]["name"], "Paul SchoolHub")
        

    @patch("core.services.brevo_email_backend.urllib.request.urlopen")
    def test_reply_to_and_cc_are_included_in_brevo_payload(
        self,
        mock_urlopen,
    ):
        mock_urlopen.return_value.__enter__.return_value.status = 201

        message = EmailMessage(
            subject="Set Up Your Password",
            body="Password setup link",
            from_email=(
                "Great Goshenland Blossom School via Paul SchoolHub "
                "<noreply@paulschoolhub.com.ng>"
            ),
            to=["student@example.com"],
            cc=["noreply@paulschoolhub.com.ng"],
            headers={
                "Reply-To": "school@example.com",
            },
        )

        backend = BrevoEmailBackend()
        backend.send_messages([message])

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))

        self.assertEqual(
            payload["replyTo"],
            {"email": "school@example.com"},
        )
        self.assertEqual(
            payload["cc"],
            [{"email": "noreply@paulschoolhub.com.ng"}],
        )

    @patch("core.services.brevo_email_backend.urllib.request.urlopen")
    def test_emails_without_reply_to_or_cc_keep_payload_unchanged(
        self,
        mock_urlopen,
    ):
        mock_urlopen.return_value.__enter__.return_value.status = 201

        message = EmailMessage(
            subject="Ordinary email",
            body="Test message",
            to=["recipient@example.com"],
        )

        backend = BrevoEmailBackend()
        backend.send_messages([message])

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))

        self.assertNotIn("replyTo", payload)
        self.assertNotIn("cc", payload)




class ImageOptimizerTests(TestCase):

    def create_image(self, image_format="JPEG", size=(2000, 1500), mode="RGB"):
        image = Image.new(mode, size, "black")
        output = BytesIO()
        image.save(output, format=image_format)
        output.seek(0)

        extension = "jpg" if image_format == "JPEG" else "png"

        return SimpleUploadedFile(
            f"test-image.{extension}",
            output.read(),
            content_type=f"image/{extension}",
        )

    def test_jpeg_is_resized_and_compressed(self):
        uploaded_file = self.create_image(
            image_format="JPEG",
            size=(2000, 1500),
        )

        original_size = uploaded_file.size

        result = optimize_image(uploaded_file)
        result.seek(0)

        optimized = Image.open(result)

        self.assertEqual(optimized.format, "JPEG")
        self.assertLessEqual(optimized.width, 1600)
        self.assertLessEqual(optimized.height, 1600)
        self.assertLess(result.size, original_size)

    def test_png_format_is_preserved(self):
        uploaded_file = self.create_image(
            image_format="PNG",
            size=(800, 400),
            mode="RGBA",
        )

        result = optimize_image(uploaded_file)
        result.seek(0)

        optimized = Image.open(result)

        self.assertEqual(optimized.format, "PNG")
        self.assertEqual(optimized.mode, "RGBA")

    def test_png_transparency_is_preserved(self):
        image = Image.new(
            "RGBA",
            (800, 400),
            (255, 255, 255, 0),
        )

        output = BytesIO()
        image.save(output, format="PNG")
        output.seek(0)

        uploaded_file = SimpleUploadedFile(
            "transparent.png",
            output.read(),
            content_type="image/png",
        )

        result = optimize_image(uploaded_file)
        result.seek(0)

        optimized = Image.open(result)

        self.assertEqual(
            optimized.getchannel("A").getextrema(),
            (0, 0),
        )

    def test_original_file_is_not_modified(self):
        uploaded_file = self.create_image(
            image_format="JPEG",
            size=(2000, 1500),
        )

        original_bytes = uploaded_file.read()
        uploaded_file.seek(0)

        optimize_image(uploaded_file)

        uploaded_file.seek(0)

        self.assertEqual(uploaded_file.read(), original_bytes)

    def test_original_filename_is_preserved(self):
        uploaded_file = self.create_image(
            image_format="JPEG",
            size=(800, 600),
        )

        result = optimize_image(uploaded_file)

        self.assertEqual(result.name, "test-image.jpg")