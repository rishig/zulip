import uuid
from typing import Any

from django import forms
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
            raise ValidationError(_('Enter a valid UUID.'))

        if RemoteZulipServer.objects.filter(uuid=server_uuid).exists():
            raise ValidationError(_("Zulip organization id already exists."))
        return server_uuid

    def clean_hostname(self):
        # type: () -> None
        hostname = self.cleaned_data['hostname']
        if not hostname.startswith('https://'):
            raise ValidationError(_("Hostname should start with https://."))

        if RemoteZulipServer.objects.filter(hostname=hostname).exists():
            raise ValidationError(
                _("{hostname} has already been registered.").format(
                    hostname=hostname))
        return hostname
