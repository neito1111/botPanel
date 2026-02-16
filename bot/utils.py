from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from aiogram.types import Message

from bot.models import AccessRequestStatus, FormStatus

PHONE_RE = re.compile(r"^\+?\d[\d\-\s\(\)]{6,}$")

DM_APPROVED_NOTICE_IDS: dict[int, list[int]] = {}
DM_REJECT_NOTICE_IDS: dict[int, dict[int, int]] = {}
TL_DUPLICATE_NOTICE_IDS: dict[int, list[int]] = {}
TL_FORM_NOTICE_IDS: dict[int, dict[int, int]] = {}


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def pack_media_item(kind: str, file_id: str) -> str:
    return f"{kind}:{file_id}"


def unpack_media_item(raw: str) -> tuple[str, str]:
    if not raw:
        return "photo", ""
    if ":" not in raw:
        return "photo", raw
    kind, file_id = raw.split(":", 1)
    kind = (kind or "photo").strip().lower()
    if kind not in {"photo", "doc", "video"}:
        kind = "photo"
    return kind, file_id


def normalize_phone(text: str, default_country_code: str = "+380") -> str:
    raw = text.strip()
    if not raw:
        return ""
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""

    code_digits = default_country_code[1:] if default_country_code.startswith("+") else default_country_code
    local = ""
    if code_digits and digits.startswith(code_digits) and len(digits) >= len(code_digits) + 9:
        local = digits[len(code_digits): len(code_digits) + 9]
    elif digits.startswith("0") and len(digits) == 10:
        local = digits[1:]
    elif len(digits) == 9:
        local = digits
    elif len(digits) > 9:
        local = digits[-9:]

    if local and len(local) == 9:
        return f"+{code_digits} {local}"

    if code_digits:
        return f"+{code_digits} {digits}"
    return digits


def is_valid_phone(text: str) -> bool:
    text = text.strip()
    if not PHONE_RE.match(text):
        return False
    if re.search(r"[A-Za-zА-Яа-я]", text):
        return False
    digits = re.sub(r"\D", "", text)
    return 7 <= len(digits) <= 15


def register_dm_approved_notice(user_tg_id: int, msg_id: int) -> None:
    if user_tg_id <= 0 or msg_id <= 0:
        return
    DM_APPROVED_NOTICE_IDS.setdefault(user_tg_id, []).append(int(msg_id))


def pop_dm_approved_notices(user_tg_id: int) -> list[int]:
    return DM_APPROVED_NOTICE_IDS.pop(user_tg_id, [])


def register_dm_reject_notice(user_tg_id: int, form_id: int, msg_id: int) -> None:
    if user_tg_id <= 0 or form_id <= 0 or msg_id <= 0:
        return
    DM_REJECT_NOTICE_IDS.setdefault(user_tg_id, {})[int(form_id)] = int(msg_id)


def pop_dm_reject_notice(user_tg_id: int, form_id: int) -> int | None:
    data = DM_REJECT_NOTICE_IDS.get(user_tg_id) or {}
    msg_id = data.pop(int(form_id), None)
    if not data:
        DM_REJECT_NOTICE_IDS.pop(user_tg_id, None)
    return msg_id


def register_tl_duplicate_notice(tl_tg_id: int, msg_id: int) -> None:
    if tl_tg_id <= 0 or msg_id <= 0:
        return
    TL_DUPLICATE_NOTICE_IDS.setdefault(tl_tg_id, []).append(int(msg_id))


def pop_tl_duplicate_notices(tl_tg_id: int) -> list[int]:
    return TL_DUPLICATE_NOTICE_IDS.pop(tl_tg_id, [])


def register_tl_form_notice(tl_tg_id: int, form_id: int, msg_id: int) -> None:
    if tl_tg_id <= 0 or form_id <= 0 or msg_id <= 0:
        return
    TL_FORM_NOTICE_IDS.setdefault(tl_tg_id, {})[int(form_id)] = int(msg_id)


def pop_tl_form_notice(tl_tg_id: int, form_id: int) -> int | None:
    data = TL_FORM_NOTICE_IDS.get(tl_tg_id) or {}
    msg_id = data.pop(int(form_id), None)
    if not data:
        TL_FORM_NOTICE_IDS.pop(tl_tg_id, None)
    return msg_id


def extract_forward_payload(message: Message) -> dict[str, Any]:
    """
    Telegram may provide different forward metadata depending on origin.
    We store only best-effort identity data (tg_id/username/name) if possible.
    We do NOT store forwarded message text/log content.
    """
    payload: dict[str, Any] = {"captured_at": utcnow().isoformat()}

    # aiogram v3: forward_origin is present for forwarded messages
    origin = getattr(message, "forward_origin", None)
    if origin is not None:
        payload["forward_origin_type"] = origin.type
        if hasattr(origin, "sender_user") and origin.sender_user:
            u = origin.sender_user
            payload.update(
                {
                    "tg_id": u.id,
                    "username": u.username,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                }
            )
        if hasattr(origin, "sender_user_name") and getattr(origin, "sender_user_name", None):
            payload["sender_user_name"] = origin.sender_user_name

    # fallback older fields
    if getattr(message, "forward_from", None):
        u = message.forward_from
        payload.update(
            {
                "tg_id": u.id,
                "username": u.username,
                "first_name": u.first_name,
                "last_name": u.last_name,
            }
        )
    if getattr(message, "forward_sender_name", None):
        payload["sender_user_name"] = message.forward_sender_name

    if message.contact:
        payload["contact_phone"] = message.contact.phone_number
        payload["contact_tg_id"] = message.contact.user_id

    return payload


def format_user_payload(p: dict[str, Any] | None) -> str:
    if not p:
        return ". | . | . | . |"

    tg_id = str(p.get("tg_id") or "").strip() or "."
    username = str(p.get("username") or "").strip().lstrip("@").strip() or "."
    phone = str(p.get("contact_phone") or "").strip() or "."

    profile_name = (
        str(p.get("sender_user_name") or "").strip()
        or " ".join([x for x in [p.get("first_name"), p.get("last_name")] if x]).strip()
    )
    name = profile_name if profile_name else "."

    return f"{tg_id} | {username} | {phone} | {name} |"


def format_bank_hashtag(bank_name: str | None) -> str:
    name = (bank_name or "").strip()
    if not name:
        return "—"
    if name in {"—", "-"}:
        return "—"
    if name.startswith("#"):
        name = name[1:].strip()
    name = name.replace(" ", "")
    if not name:
        return "—"
    if name in {"—", "-"}:
        return "—"
    return f"#{name}"


def format_timedelta_seconds(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}ч {m}м {s}с"
    if m:
        return f"{m}м {s}с"
    return f"{s}с"


def format_form_status(status: FormStatus | str | None) -> str:
    mapping = {
        FormStatus.IN_PROGRESS: "В работе",
        FormStatus.PENDING: "На проверке",
        FormStatus.APPROVED: "Подтверждена",
        FormStatus.REJECTED: "Отклонена",
        "IN_PROGRESS": "В работе",
        "PENDING": "На проверке",
        "APPROVED": "Подтверждена",
        "REJECTED": "Отклонена",
    }
    return mapping.get(status, "—")


def format_access_status(status: AccessRequestStatus | str | None) -> str:
    mapping = {
        AccessRequestStatus.PENDING: "На рассмотрении",
        AccessRequestStatus.APPROVED: "Одобрена",
        AccessRequestStatus.REJECTED: "Отклонена",
        "PENDING": "На рассмотрении",
        "APPROVED": "Одобрена",
        "REJECTED": "Отклонена",
    }
    return mapping.get(status, "—")


