# deals/backends.py
from django.core.mail.backends.smtp import EmailBackend
import ssl

class UnverifiedTLSBackend(EmailBackend):
    """
    Backend SMTP qui désactive la vérification du certificat.
    STRICTEMENT DEV/LOCAL.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssl_context = ssl._create_unverified_context()
