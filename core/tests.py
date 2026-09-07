from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from core.utils.image_optimizer import optimize_image


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