import json
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Notification, NotificationStatus


async def send_email(
    db: AsyncSession,
    recipient: str,
    event: str,
    subject: str,
    html: str,
    metadata: dict[str, Any] | None = None,
) -> Notification:
    settings = get_settings()
    notification = Notification(
        recipient=recipient,
        event=event,
        channel="email",
        status=NotificationStatus.SKIPPED,
        payload_json=json.dumps({"subject": subject, **(metadata or {})}, ensure_ascii=False, default=str),
    )
    db.add(notification)
    await db.flush()

    if not settings.resend_api_key:
        return notification

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={"from": settings.resend_from_email, "to": [recipient], "subject": subject, "html": html},
            )
            response.raise_for_status()
            result = response.json()
        notification.status = NotificationStatus.SENT
        notification.provider_message_id = result.get("id")
        notification.sent_at = datetime.now(UTC)
    except (httpx.HTTPError, ValueError) as exc:
        notification.status = NotificationStatus.FAILED
        notification.error_message = str(exc)[:1000]
    return notification
