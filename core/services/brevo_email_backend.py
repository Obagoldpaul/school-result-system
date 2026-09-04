import json
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class BrevoEmailBackend(BaseEmailBackend):
    """
    Django email backend that sends transactional emails through
    Brevo's HTTPS API instead of SMTP.
    """

    api_url = "https://api.brevo.com/v3/smtp/email"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0

        for message in email_messages:
            if self._send_message(message):
                sent_count += 1

        return sent_count

    def _send_message(self, message):
        if not message.recipients():
            return False

        sender_email = settings.DEFAULT_FROM_EMAIL
        sender_name = "Paul SchoolHub"

        if "<" in sender_email and ">" in sender_email:
            sender_name = sender_email.split("<", 1)[0].strip()
            sender_email = sender_email.split("<", 1)[1].split(">", 1)[0].strip()

        payload = {
            "sender": {
                "name": sender_name,
                "email": sender_email,
            },
            "to": [
                {"email": recipient}
                for recipient in message.recipients()
            ],
            "subject": message.subject,
            "textContent": message.body,
        }

        if message.content_subtype == "html":
            payload["htmlContent"] = message.body
            payload.pop("textContent", None)

        request = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "accept": "application/json",
                "api-key": settings.BREVO_API_KEY,
                "content-type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if 200 <= response.status < 300:
                    return True

        except urllib.error.HTTPError as exc:
            if not self.fail_silently:
                error_body = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Brevo API error {exc.code}: {error_body}"
                ) from exc

        except urllib.error.URLError as exc:
            if not self.fail_silently:
                raise RuntimeError(
                    f"Brevo API connection error: {exc.reason}"
                ) from exc

        return False