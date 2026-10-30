import hmac

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class StaticAPIKeyAuthentication(BaseAuthentication):
    """
    Authenticates machine-to-machine calls (dcm4chee webhooks, modality worklist)
    with the shared CARE_RADIOLOGY_WEBHOOK_SECRET sent in the Authorization header.
    """

    def authenticate(self, request):
        secret = settings.PLUGIN_CONFIGS["care_radiology"].get(
            "CARE_RADIOLOGY_WEBHOOK_SECRET", ""
        )
        # Refuse everything when unconfigured, otherwise an empty header matches
        if not secret:
            raise AuthenticationFailed("API key authentication is not configured")

        api_key = request.headers.get("Authorization", "")
        if not api_key or not hmac.compare_digest(
            api_key.encode(), str(secret).encode()
        ):
            raise AuthenticationFailed("Invalid API key")
        return (AnonymousUser(), None)
