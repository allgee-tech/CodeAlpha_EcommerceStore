from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from PIL import Image, UnidentifiedImageError


def validate_product_image(image):
    if image.size > 5 * 1024 * 1024:
        raise ValidationError("Product images must be 5 MB or smaller.")
    try:
        image.seek(0)
        with Image.open(image) as opened:
            if opened.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValidationError("Only JPEG, PNG, and WEBP product images are supported.")
            opened.verify()
    except (UnidentifiedImageError, OSError):
        raise ValidationError("Upload a valid image file.")
    finally:
        image.seek(0)


image_extension_validator = FileExtensionValidator(["jpg", "jpeg", "png", "webp"])
