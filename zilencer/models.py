from django.db import models
from django.db.models import Manager
from typing import Dict, Optional, Text

import zerver.models
import datetime

def get_remote_server_by_uuid(uuid):
    # type: (Text) -> RemoteZulipServer
    return RemoteZulipServer.objects.get(uuid=uuid)

class RemoteZulipServer(models.Model):
    UUID_LENGTH = 36
    API_KEY_LENGTH = 64
    MAX_HOST_NAME_LENGTH = 128

    uuid = models.CharField(max_length=UUID_LENGTH, unique=True)  # type: Text
    api_key = models.CharField(max_length=API_KEY_LENGTH)  # type: Text

    hostname = models.CharField(max_length=MAX_HOST_NAME_LENGTH, unique=True)  # type: Text
    contact_email = models.EmailField(blank=True, null=False)  # type: Text
    last_updated = models.DateTimeField('last updated', auto_now=True)  # type: datetime.datetime

# Variant of PushDeviceToken for a remote server.
class RemotePushDeviceToken(zerver.models.AbstractPushDeviceToken):
    server = models.ForeignKey(RemoteZulipServer)  # type: RemoteZulipServer
    # The user id on the remote server for this device device this is
    user_id = models.BigIntegerField(db_index=True)  # type: int
    token = models.CharField(max_length=4096, db_index=True)  # type: bytes

    class Meta:
        unique_together = ("server", "token")

class RemoteServerRegistrationStatus(models.Model):
    email = models.EmailField()  # type: Text
    updated_at = models.DateTimeField(auto_now=True)  # type: datetime.datetime

    # status: whether an object has been confirmed.
    #   if confirmed, set to confirmation.settings.STATUS_ACTIVE
    status = models.IntegerField(default=0)  # type: int
