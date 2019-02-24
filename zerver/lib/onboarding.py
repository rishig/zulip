
from django.conf import settings

from zerver.lib.actions import \
    internal_prep_stream_message_by_name, internal_send_private_message, \
    do_send_messages, \
    do_add_reaction_legacy, create_users, missing_any_realm_internal_bots
from zerver.models import Message, Realm, UserProfile, get_system_bot

from typing import Dict, List

def setup_realm_internal_bots(realm: Realm) -> None:
    """Create this realm's internal bots.

    This function is idempotent; it does nothing for a bot that
    already exists.
    """
    internal_bots = [(bot['name'], bot['email_template'] % (settings.INTERNAL_BOT_DOMAIN,))
                     for bot in settings.REALM_INTERNAL_BOTS]
    create_users(realm, internal_bots, bot_type=UserProfile.DEFAULT_BOT)
    bots = UserProfile.objects.filter(
        realm=realm,
        email__in=[bot_info[1] for bot_info in internal_bots],
        bot_owner__isnull=True
    )
    for bot in bots:
        bot.bot_owner = bot
        bot.save()

def create_if_missing_realm_internal_bots() -> None:
    """This checks if there is any realm internal bot missing.

    If that is the case, it creates the missing realm internal bots.
    """
    if missing_any_realm_internal_bots():
        for realm in Realm.objects.all():
            setup_realm_internal_bots(realm)

def send_initial_pms(user: UserProfile) -> None:
    organization_setup_text = ""
    if user.is_realm_admin:
        help_url = user.realm.uri + "/help/getting-your-organization-started-with-zulip"
        organization_setup_text = ("* [Read the guide](%s) for getting your organization "
                                   "started with Zulip\n" % (help_url,))

    content = (
        "Hello, and welcome to Zulip!\n\nThis is a private message from me, Welcome Bot. "
        "Here are some tips to get you started:\n"
        "* Download our [Desktop and mobile apps](/apps)\n"
        "* Customize your account and notifications on your [Settings page](#settings)\n"
        "* Type `?` to check out Zulip's keyboard shortcuts\n"
        "%s"
        "\n"
        "The most important shortcut is `r` to reply.\n\n"
        "Practice sending a few messages by replying to this conversation. If you're not into "
        "keyboards, that's okay too; clicking anywhere on this message will also do the trick!") \
        % (organization_setup_text,)

    internal_send_private_message(user.realm, get_system_bot(settings.WELCOME_BOT),
                                  user, content)

def send_initial_realm_messages(realm: Realm) -> None:
    welcome_bot = get_system_bot(settings.WELCOME_BOT)
    # Make sure each stream created in the realm creation process has at least one message below
    # Order corresponds to the ordering of the streams on the left sidebar, to make the initial Home
    # view slightly less overwhelming
    welcome_messages = [
        {'stream': Realm.DEFAULT_NOTIFICATION_STREAM_NAME,
         'topic': "welcome",
         'content': "This is a message on stream `%s` with the topic `welcome`. We'll use this stream "
         "for system-generated notifications." % (Realm.DEFAULT_NOTIFICATION_STREAM_NAME,)},
        {'stream': Realm.INITIAL_PRIVATE_STREAM_NAME,
         'topic': "private streams",
         'content': "This is a private stream. Only admins and people you invite "
         "to the stream will be able to see that this stream exists."},
        {'stream': Realm.DEFAULT_NOTIFICATION_STREAM_NAME,
         'topic': "topic demonstration",
         'content': "Here is a message in one topic. Replies to this message will go to this topic."},
        {'stream': Realm.DEFAULT_NOTIFICATION_STREAM_NAME,
         'topic': "topic demonstration",
         'content': "A second message in this topic. With [turtles](/static/images/cute/turtle.png)!"},
        {'stream': Realm.DEFAULT_NOTIFICATION_STREAM_NAME,
         'topic': "second topic",
         'content': "This is a message in a second topic.\n\nTopics are similar to email subjects, "
         "in that each conversation should get its own topic. Keep them short, though; one "
         "or two words will do it! "
         "Type `c` or click on `New Topic` at the bottom of the "
         "screen to start a new topic."},
    ]  # type: List[Dict[str, str]]
    messages = [internal_prep_stream_message_by_name(
        realm, welcome_bot, message['stream'],
        message['topic'], message['content']
    ) for message in welcome_messages]
    message_ids = do_send_messages(messages)

    # We find the one of our just-sent messages with turtle.png in it,
    # and react to it.  This is a bit hacky, but works and is kinda a
    # 1-off thing.
    turtle_message = Message.objects.get(
        id__in=message_ids,
        content__icontains='cute/turtle.png')
    do_add_reaction_legacy(welcome_bot, turtle_message, 'turtle')
