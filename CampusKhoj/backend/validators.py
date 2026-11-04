import datetime
import re

from .errors import ValidationError

PRN_REGEX = re.compile(r"^\d{10}$")
VIT_EMAIL_REGEX = re.compile(r"^[a-z]+(\.[a-z]+)?\.(\d{10})@vit\.edu$")
PHONE_REGEX = re.compile(r"^\+?[0-9]{10,15}$")

def validate_prn(prn: str) -> str:
    """Validates that PRN is exactly 10 digits."""
    if not prn or not isinstance(prn, str) or not PRN_REGEX.match(prn.strip()):
        raise ValidationError("PRN must be exactly 10 numeric digits", {"field": "prn"})
    return prn.strip()

def validate_email(email: str | None, prn: str | None = None) -> str | None:
    """
    Validates optional VIT student email format:
    name.<PRN>@vit.edu where digits match the student's PRN.
    """
    if not email:
        return None
    cleaned = email.strip().lower()
    match = VIT_EMAIL_REGEX.match(cleaned)
    if not match:
        raise ValidationError(
            "Email must follow the VIT format: firstname.<PRN>@vit.edu",
            {"field": "email"}
        )
    email_prn = match.group(2)
    if prn and email_prn != prn.strip():
        raise ValidationError(
            f"The digits in email ({email_prn}) do not match your PRN ({prn.strip()})",
            {"field": "email"}
        )
    return cleaned

def validate_phone(phone: str | None) -> str | None:
    """Validates optional phone number."""
    if not phone:
        return None
    cleaned = phone.strip().replace(" ", "").replace("-", "")
    if not PHONE_REGEX.match(cleaned):
        raise ValidationError("Invalid phone number format. Must be 10 to 15 digits", {"field": "phone"})
    return cleaned

def validate_date(date_str: str, field_name: str = "date") -> datetime.date:
    """Validates date string (YYYY-MM-DD) and ensures not in future."""
    if not date_str:
        raise ValidationError(f"{field_name} is required", {"field": field_name})
    try:
        parsed_date = datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"{field_name} must be in YYYY-MM-DD format", {"field": field_name})

    today = datetime.date.today()
    if parsed_date > today:
        raise ValidationError(f"{field_name} cannot be in the future", {"field": field_name})
    return parsed_date

def validate_time(time_str: str | None, field_name: str = "time") -> str | None:
    """Validates optional time string (HH:MM or HH:MM:SS)."""
    if not time_str:
        return None
    cleaned = time_str.strip()
    try:
        if len(cleaned) == 5:
            datetime.datetime.strptime(cleaned, "%H:%M")
        else:
            datetime.datetime.strptime(cleaned, "%H:%M:%S")
        return cleaned
    except ValueError:
        raise ValidationError(f"{field_name} must be in HH:MM or HH:MM:SS format", {"field": field_name})

def validate_int_param(value: any, param_name: str = "parameter", default: int = 1, min_val: int = 1, max_val: int | None = None) -> int:
    """
    Safely validates integer query parameters like page, page_size, limit.
    Raises ValidationError (HTTP 400) on non-integer or out-of-range values,
    and clamps to max_val if specified.
    """
    if value is None or value == "":
        return default
    try:
        val = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Query parameter '{param_name}' must be an integer", {"field": param_name})
    if val < min_val:
        raise ValidationError(f"Query parameter '{param_name}' must be at least {min_val}", {"field": param_name})
    if max_val is not None:
        val = min(val, max_val)
    return val

def parse_pagination(request, default_page: int = 1, default_size: int = 20, max_size: int = 50) -> tuple[int, int, int]:
    """
    Parses and validates page, page_size from request.args.
    Returns (page, page_size, offset).
    Raises ValidationError (400) if page or page_size are non-numeric or < 1.
    """
    page_raw = request.args.get("page")
    size_raw = request.args.get("page_size") or request.args.get("limit")

    page = validate_int_param(page_raw, "page", default=default_page, min_val=1)
    page_size = validate_int_param(size_raw, "page_size", default=default_size, min_val=1, max_val=max_size)
    offset = (page - 1) * page_size
    return page, page_size, offset

