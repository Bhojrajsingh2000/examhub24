"""
Reusable validators for file/image uploads across the project. None of the existing
FileField/ImageField definitions had any size or type limit before this — meaning a user
could upload an arbitrarily large file (disk-space risk) or a mismatched file type.

Usage in a model field:
    from core.validators import validate_image_size, validate_document_size
    profile_picture = models.ImageField(upload_to='profiles/', validators=[validate_image_size])
    file = models.FileField(upload_to='study_material/', validators=[validate_document_size])
"""
from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE_MB = 5
MAX_DOCUMENT_SIZE_MB = 20

ALLOWED_DOCUMENT_EXTENSIONS = ('.pdf', '.doc', '.docx')


def _size_in_mb(file_obj):
    try:
        return file_obj.size / (1024 * 1024)
    except (OSError, ValueError):
        # Can happen when validating an already-saved FieldFile whose underlying file is
        # temporarily unreadable (e.g. storage hiccup) — don't let a size check crash the
        # whole form; just skip the check rather than raising an unrelated server error.
        return 0


def validate_image_size(file_obj):
    if _size_in_mb(file_obj) > MAX_IMAGE_SIZE_MB:
        raise ValidationError(f'Image file too large. Maximum allowed size is {MAX_IMAGE_SIZE_MB} MB.')


def validate_document_size(file_obj):
    if _size_in_mb(file_obj) > MAX_DOCUMENT_SIZE_MB:
        raise ValidationError(f'File too large. Maximum allowed size is {MAX_DOCUMENT_SIZE_MB} MB.')


def validate_document_extension(file_obj):
    name = file_obj.name.lower()
    if not name.endswith(ALLOWED_DOCUMENT_EXTENSIONS):
        allowed = ', '.join(ALLOWED_DOCUMENT_EXTENSIONS)
        raise ValidationError(f'Unsupported file type. Allowed types: {allowed}')
