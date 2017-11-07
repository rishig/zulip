
from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.db import transaction

from confirmation.models import get_object_from_key, \
    render_confirmation_key_error, ConfirmationKeyException, \
    create_confirmation_link, Confirmation

from zilencer.models import RemotePushDeviceToken, RemoteZulipServer, \
    RemoteServerRegistrationStatus
from zilencer.forms import ServerRegistrationForm, \
    StartServerRegistrationForm

from zerver.lib.exceptions import JsonableError
from zerver.lib.push_notifications import send_android_push_notification, \
    send_apple_push_notification
from zerver.lib.response import json_error, json_success
from zerver.lib.request import has_request_variables, REQ
from zerver.lib.validator import check_dict, check_int
from zerver.lib.send_email import send_email
from zerver.models import UserProfile, PushDeviceToken, Realm
from zerver.views.push_notifications import validate_token

from typing import Any, Dict, Optional, Union, Text, cast

def validate_entity(entity):
    # type: (Union[UserProfile, RemoteZulipServer]) -> None
    if not isinstance(entity, RemoteZulipServer):
        raise JsonableError(_("Must validate with valid Zulip server API key"))

def validate_bouncer_token_request(entity, token, kind):
    # type: (Union[UserProfile, RemoteZulipServer], bytes, int) -> None
    if kind not in [RemotePushDeviceToken.APNS, RemotePushDeviceToken.GCM]:
        raise JsonableError(_("Invalid token type"))
    validate_entity(entity)
    validate_token(token, kind)

@has_request_variables
def remote_server_register_push(request, entity, user_id=REQ(),
                                token=REQ(), token_kind=REQ(validator=check_int), ios_app_id=None):
    # type: (HttpRequest, Union[UserProfile, RemoteZulipServer], int, bytes, int, Optional[Text]) -> HttpResponse
    validate_bouncer_token_request(entity, token, token_kind)
    server = cast(RemoteZulipServer, entity)

    # If a user logged out on a device and failed to unregister,
    # we should delete any other user associations for this token
    # & RemoteServer pair
    RemotePushDeviceToken.objects.filter(
        token=token, kind=token_kind, server=server).exclude(user_id=user_id).delete()

    # Save or update
    remote_token, created = RemotePushDeviceToken.objects.update_or_create(
        user_id=user_id,
        server=server,
        kind=token_kind,
        token=token,
        defaults=dict(
            ios_app_id=ios_app_id,
            last_updated=timezone.now()))

    return json_success()

@has_request_variables
def remote_server_unregister_push(request, entity, token=REQ(),
                                  token_kind=REQ(validator=check_int), ios_app_id=None):
    # type: (HttpRequest, Union[UserProfile, RemoteZulipServer], bytes, int, Optional[Text]) -> HttpResponse
    validate_bouncer_token_request(entity, token, token_kind)
    server = cast(RemoteZulipServer, entity)
    deleted = RemotePushDeviceToken.objects.filter(token=token,
                                                   kind=token_kind,
                                                   server=server).delete()
    if deleted[0] == 0:
        return json_error(_("Token does not exist"))

    return json_success()

@has_request_variables
def remote_server_notify_push(request,  # type: HttpRequest
                              entity,  # type: Union[UserProfile, RemoteZulipServer]
                              payload=REQ(argument_type='body')  # type: Dict[str, Any]
                              ):
    # type: (...) -> HttpResponse
    validate_entity(entity)
    server = cast(RemoteZulipServer, entity)

    user_id = payload['user_id']
    gcm_payload = payload['gcm_payload']
    apns_payload = payload['apns_payload']

    android_devices = list(RemotePushDeviceToken.objects.filter(
        user_id=user_id,
        kind=RemotePushDeviceToken.GCM,
        server=server
    ))

    apple_devices = list(RemotePushDeviceToken.objects.filter(
        user_id=user_id,
        kind=RemotePushDeviceToken.APNS,
        server=server
    ))

    if android_devices:
        send_android_push_notification(android_devices, gcm_payload, remote=True)

    if apple_devices:
        send_apple_push_notification(user_id, apple_devices, apns_payload)

    return json_success()

def register_remote_server(request):
    # type: (HttpRequest) -> HttpResponse
    if request.method == 'POST':
        form = StartRemoteServerRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            with transaction.atomic():
                status_obj = RemoteServerRegistrationStatus.objects.create(email=email)
                activation_url = create_confirmation_link(status_obj,
                                                          request.get_host(),
                                                          Confirmation.SERVER_REGISTRATION)

            send_email('zerver/emails/confirm_server_registration',
                       to_email=email,
                       from_address=settings.DEFAULT_FROM_EMAIL,
                       context={'activate_url': activation_url})

            return HttpResponseRedirect(
                reverse('remotes_send_confirm', kwargs={'email': email}))
    else:
        form = StartRemoteServerRegistrationForm()

    return render(
        request,
        'zilencer/start_register_remote_server.html',
        context={'form': form, 'current_url': request.get_full_path})

def confirm(request, confirmation_key):
    # type: (HttpRequest, str) -> HttpResponse
    confirmation_key = confirmation_key.lower()
    try:
        status_obj = get_object_from_key(confirmation_key)
    except ConfirmationKeyException as exception:
        return render_confirmation_key_error(request, exception)

    if request.method == 'POST':
        assert isinstance(status_obj, RemoteServerRegistrationStatus)
        form = RemoteServerRegistrationForm(request.POST)
        if form.is_valid():
            api_key = form.cleaned_data['server_api_key']
            uuid = form.cleaned_data['server_uuid']
            hostname = form.cleaned_data['hostname']
            RemoteZulipServer.objects.create(
                uuid=uuid,
                api_key=api_key,
                hostname=hostname,
                contact_email=status_obj.email,
            )
            return render(request, 'confirmation/confirm_remote_server.html',
                          {'hostname': hostname})
    else:
        form = RemoteServerRegistrationForm()

    context = {'form': form, 'current_url': request.get_full_path}
    return render(request, 'zilencer/register_remote_server.html',
                  context=context)
