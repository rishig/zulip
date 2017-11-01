import uuid
from typing import Any

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from zilencer.models import RemoteZulipServer

class EnterpriseToSForm(forms.Form):
    full_name = forms.CharField(max_length=100)
    company = forms.CharField(max_length=100)
    terms = forms.BooleanField(required=True)

class StartServerRegistrationForm(forms.Form):
    email = forms.EmailField()

class ServerRegistrationForm(forms.Form):
    server_uuid = forms.CharField(max_length=RemoteZulipServer.UUID_LENGTH)
    server_api_key = forms.CharField(max_length=RemoteZulipServer.API_KEY_LENGTH)
    hostname = forms.URLField(max_length=RemoteZulipServer.MAX_HOST_NAME_LENGTH)
    terms = forms.BooleanField(required=True)

    def clean_server_uuid(self):
        # type: () -> None
        server_uuid = self.cleaned_data['server_uuid']
        try:
            uuid.UUID(server_uuid)
        except ValueError:
            raise ValidationError(_('Not a valid zulip_org_id.'))

        if RemoteZulipServer.objects.filter(uuid=server_uuid).exists():
            raise ValidationError(
                _("This zulip_org_id has already been registered. "
                  "Contact {email} to update your registration information.").format(
                      email=settings.ZULIP_ADMINISTRATOR))
        return server_uuid

    def clean_server_api_key(self):
        # type: () -> None
        server_api_key = self.cleaned_data['server_api_key']
        if len(server_api_key) != RemoteZulipServer.API_KEY_LENGTH:
            raise ValidationError(_('Not a valid zulip_api_key.'))
        forms.CharField(max_length=RemoteZulipServer.API_KEY_LENGTH)


    def clean_hostname(self):
        # type: () -> None
        hostname = self.cleaned_data['hostname']
        if not hostname.startswith('https://'):
            raise ValidationError(_("Hostname must start with https://."))

        if RemoteZulipServer.objects.filter(hostname=hostname).exists():
            raise ValidationError(
                _("{hostname} has already been registered. "
                  "Contact {email} to update your registration information.").format(
                      hostname=hostname, email=settings.ZULIP_ADMINISTRATOR))
        return hostname
