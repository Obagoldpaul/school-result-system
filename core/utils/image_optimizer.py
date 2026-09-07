from io import BytesIO
import os

from django.core.files.base import ContentFile
from PIL import Image


MAX_IMAGE_DIMENSION = 1600
JPEG_QUALITY = 85


def optimize_image(uploaded_file):
    """
    Optimize an uploaded image before it is stored.

    - Resizes unnecessarily large images.
    - Compresses JPEG images.
    - Preserves PNG transparency.
    - Returns a Django ContentFile.
    - Does not modify the original uploaded file.
    """

    image = Image.open(uploaded_file)

    original_format = image.format

    if image.width > MAX_IMAGE_DIMENSION or image.height > MAX_IMAGE_DIMENSION:
        image.thumbnail(
            (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
            Image.Resampling.LANCZOS,
        )

    output = BytesIO()

    if original_format == "PNG":
        image.save(
            output,
            format="PNG",
            optimize=True,
        )
        extension = "png"

    elif original_format in ("JPEG", "JPG"):
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        image.save(
            output,
            format="JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
        )
        extension = "jpg"

    else:
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        image.save(
            output,
            format="JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
        )
        extension = "jpg"

    output.seek(0)

    original_name = os.path.basename(uploaded_file.name)
    base_name = os.path.splitext(original_name)[0]

    return ContentFile(
        output.read(),
        name=f"{base_name}.{extension}",
    )