from django.core.exceptions import ValidationError


MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_DOCUMENT_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_image_size(value):
    if value and value.size > MAX_IMAGE_SIZE:
        raise ValidationError(
            "Image file size must not exceed 2 MB."
        )


def validate_document_size(value):
    if value and value.size > MAX_DOCUMENT_SIZE:
        raise ValidationError(
            "Document file size must not exceed 5 MB."
        )