# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Optional, Text

from argparse import ArgumentParser
from django.db.models import F
from django.core.management.base import BaseCommand

from zerver.lib.actions import bulk_add_subscriptions, bulk_remove_subscriptions, \
    create_stream_if_needed, create_streams_if_needed, do_add_reaction_legacy, \
    do_change_avatar_fields, do_create_realm, do_create_user, do_send_messages, \
    internal_prep_stream_message
from zerver.lib.upload import upload_avatar_image
from zerver.models import Message, UserProfile, get_realm, Stream, Realm, Client, \
    UserPresence, UserMessage

from .lorem_data import lorem_words
from datetime import timedelta
import random

class Command(BaseCommand):
    help = """Add a mock conversation to the development environment.

Usage: ./manage.py add_mock_conversation

After running the script:

From browser (ideally on high resolution screen):
* Refresh to get the rendered tweet
* Check that the whale emoji reaction comes before the thumbs_up emoji reaction
* Remove the blue box (it's a box shadow on .selected_message .messagebox-content;
  inspecting the selected element will find it fairly quickly)
* Change the color of the stream to #a6c7e5
* Shrink screen till the mypy link only just fits
* Take screenshot that does not include the timestamps or bottom edge

From image editing program:
* Remove mute (and edit) icons from recipient bar
"""

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument('--keep_users', action="store_true", default=False,
                            help="Don't recreate users.")
        parser.add_argument('--keep_streams', action="store_true", default=False,
                            help="Don't recreate streams.")

    def set_avatar(self, user: UserProfile, filename: str) -> None:
        upload_avatar_image(open(filename, 'rb'), user, user)
        do_change_avatar_fields(user, UserProfile.AVATAR_FROM_USER)

    def add_message_formatting_conversation(self) -> None:
        realm = get_realm('zulip')
        stream, _ = create_stream_if_needed(realm, 'zulip features')

        UserProfile.objects.filter(email__contains='stage').delete()
        starr = do_create_user('1@stage.example.com', 'password', realm, 'Ada Starr', '')
        self.set_avatar(starr, 'static/images/features/starr.png')
        fisher = do_create_user('2@stage.example.com', 'password', realm, 'Bel Fisher', '')
        self.set_avatar(fisher, 'static/images/features/fisher.png')
        twitter_bot = do_create_user('3@stage.example.com', 'password', realm, 'Twitter Bot', '',
                                     bot_type=UserProfile.DEFAULT_BOT)
        self.set_avatar(twitter_bot, 'static/images/features/twitter.png')

        bulk_add_subscriptions([stream], list(UserProfile.objects.filter(realm=realm)))

        staged_messages = [
            {'sender': starr,
             'content': "Hey @**Bel Fisher**, check out Zulip's Markdown formatting! "
             "You can have:\n* bulleted lists\n  * with sub-bullets too\n"
             "* **bold**, *italic*, and ~~strikethrough~~ text\n"
             "* LaTeX for mathematical formulas, both inline -- $$O(n^2)$$ -- and displayed:\n"
             "```math\n\\int_a^b f(t)\, dt=F(b)-F(a)\n```"},
            {'sender': fisher,
             'content': "My favorite is the syntax highlighting for code blocks\n"
             "```python\ndef fib(n: int) -> int:\n    # returns the n-th Fibonacci number\n"
             "    return fib(n-1) + fib(n-2)\n```"},
            {'sender': starr,
             'content': "I think you forgot your base case there, Bel :laughing:\n"
             "```quote\n```python\ndef fib(n: int) -> int:\n    # returns the n-th Fibonacci number\n"
             "    return fib(n-1) + fib(n-2)\n```\n```"},
            {'sender': fisher,
             'content': "I'm also a big fan of inline link, tweet, video, and image previews. "
             "Check out this picture of Çet Whalin[](/static/images/features/whale.png)!"},
            {'sender': starr,
             'content': "I just set up a custom linkifier, "
                        "so `#1234` becomes [#1234](github.com/zulip/zulip/1234), "
             "a link to the corresponding GitHub issue."},
            {'sender': twitter_bot,
             'content': 'https://twitter.com/gvanrossum/status/786661035637772288'},
            {'sender': fisher,
             'content': "Oops, the Twitter bot I set up shouldn't be posting here. Let me go fix that."},
        ]  # type: List[Dict[str, Any]]

        messages = [internal_prep_stream_message(
            realm, message['sender'], stream.name, 'message formatting', message['content']
        ) for message in staged_messages]

        message_ids = do_send_messages(messages)

        preview_message = Message.objects.get(id__in=message_ids, content__icontains='image previews')
        do_add_reaction_legacy(starr, preview_message, 'whale')

        twitter_message = Message.objects.get(id__in=message_ids, content__icontains='gvanrossum')
        # Setting up a twitter integration in dev is a decent amount of work. If you need
        # to update this tweet, either copy the format below, or send the link to the tweet
        # to chat.zulip.org and ask an admin of that server to get you the rendered_content.
        twitter_message.rendered_content = (
            '<p><a>https://twitter.com/gvanrossum/status/786661035637772288</a></p>\n'
            '<div class="inline-preview-twitter"><div class="twitter-tweet">'
            '<a><img class="twitter-avatar" '
            'src="https://pbs.twimg.com/profile_images/424495004/GuidoAvatar_bigger.jpg"></a>'
            '<p>Great blog post about Zulip\'s use of mypy: '
            '<a>http://blog.zulip.org/2016/10/13/static-types-in-python-oh-mypy/</a></p>'
            '<span>- Guido van Rossum (@gvanrossum)</span></div></div>')
        twitter_message.save(update_fields=['rendered_content'])

        # Put a short pause between the whale reaction and this, so that the
        # thumbs_up shows up second
        do_add_reaction_legacy(starr, preview_message, 'thumbs_up')

    def get_or_create_user(self, email: Text, realm: Realm, name: Text,
                           is_realm_admin: bool=False,
                           avatar_url: Optional[str]=None):
        try:
            return UserProfile.objects.filter(email=email, realm=realm).get()
        except UserProfile.DoesNotExist:
            user = do_create_user(email, 'password', realm, name, '', is_realm_admin=is_realm_admin)
            if avatar_url is not None:
                self.set_avatar(user, 'static/images/features/starr.png')
            return user

    def add_topics_and_threading_conversation(self, options: Dict[str, Any]) -> None:
        realm = Realm.objects.filter(string_id='topics').first()
        if realm is None:
            realm = do_create_realm('topics', 'topics')

        if not options['keep_users']:
            UserProfile.objects.filter(email__contains='stage').delete()
        starr = self.get_or_create_user('1@stage.example.com', realm, 'Ada Starr',
                                        is_realm_admin=True,
                                        avatar_url='static/images/features/starr.png')
        fisher = self.get_or_create_user('2@stage.example.com', realm, 'Bel Fisher',
                                    avatar_url='static/images/features/fisher.png')
        coral = self.get_or_create_user('3@stage.example.com', realm, 'Crazy Coral')
        dolphin = self.get_or_create_user('4@stage.example.com', realm, 'Dewey Dolphin')
        eel = self.get_or_create_user('5@stage.example.com', realm, 'Enigmatic Eel')

        # turn off hotspots
        starr.tutorial_status = UserProfile.TUTORIAL_FINISHED
        starr.save(update_fields=['tutorial_status'])

        bulk_remove_subscriptions([starr], Stream.objects.filter(realm=realm))

        stream_names = ['design', 'engineering', 'general', 'marketing', 'sf office']

        for stream_name in stream_names:
            create_stream_if_needed(realm, stream_name)
        bulk_add_subscriptions(Stream.objects.filter(realm=realm, name__in=stream_names),
                               [starr])

        random.seed(42)
        changes = [2]*4 + [1]*5 + [0]*10
        random.shuffle(changes)

        topics = ['/team page', 'logo border', 'narrow icon', 'linkify on paste', 'link shortcut key']
        topic_indices = [3]*2 + [2]*10 + [1]*3 + [0]*5

        # for i in range(len(changes)):
        #     if changes[i] < 2:
        #         topic_indices.append(topic_indices[-1])
        #     else:
        #         topic_indices.append(random.randint(0, len(topics)-1))

        users = [starr, fisher, coral, dolphin, eel]
        user_indices = [0]
        for i in range(len(changes)):
            if changes[i] < 1:
                user_indices.append(user_indices[-1])
            else:
                user_indices.append(random.randint(0, len(users)-1))

        messages = [internal_prep_stream_message(
            realm, users[0], stream.name, 'keep alive', random.choice(lorem_words)
        ) for stream in Stream.objects.filter(invite_only=False)]
        do_send_messages(messages)

        messages = [internal_prep_stream_message(
            realm, users[0], 'design', topics[-1], random.choice(lorem_words))]
        do_send_messages(messages)

        UserMessage.objects.all().update(flags=F('flags').bitor(UserMessage.flags.read))

        messages = [internal_prep_stream_message(
            realm, users[user_indices[i]], 'design', topics[topic_indices[i]], random.choice(lorem_words)
        ) for i in range(len(changes)+1)]
        do_send_messages(messages)

        messages = [internal_prep_stream_message(
            realm, users[-1], 'general', 'bump unread count', 'message text') for i in range(3)]
        do_send_messages(messages)

        messages = [internal_prep_stream_message(
            realm, users[-1], 'marketing', 'bump unread count', 'message text') for i in range(1)]
        do_send_messages(messages)

        client = Client.objects.first()
        for user in users:
            UserPresence.objects.get_or_create(
                user_profile=user, client=client, defaults={
                    'status': UserPresence.ACTIVE,
                    'timestamp': user.date_joined + timedelta(days=1000)})

        # UserProfile.objects.all().update(pointer=0)


    def handle(self, *args: Any, **options: str) -> None:
        # self.add_topics_and_threading_conversation()
        self.add_topics_and_threading_conversation(options)
