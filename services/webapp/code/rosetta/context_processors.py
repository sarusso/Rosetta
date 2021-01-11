import os
from django.conf import settings
def export_vars(request):
    data = {}
    if settings.OIDC_RP_CLIENT_ID:
        data['OPENID_ENABLED'] = True
    else:
        data['OPENID_ENABLED'] = False        
    return data