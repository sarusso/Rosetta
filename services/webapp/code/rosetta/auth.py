from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from .core_app.utils import finalize_user_creation

# Setup logging
import logging
logger = logging.getLogger(__name__)


class RosettaOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    
    def create_user(self, claims):
        
        # Call parent user creation function
        user = super(RosettaOIDCAuthenticationBackend, self).create_user(claims)

        # Add profile, keys etc.
        finalize_user_creation(user)

        return user


    def get_userinfo(self, access_token, id_token, payload):

        # Payload must contain the "email" key
        return payload

