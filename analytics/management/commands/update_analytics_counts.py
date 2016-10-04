from argparse import ArgumentParser
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from analytics.models import RealmCount, UserCount
from analytics.lib.counts import CountStat, process_count_stat, \
    zerver_count_user_by_realm, zerver_count_message_by_user, \
    zerver_count_message_by_stream, zerver_count_stream_by_realm, \
    zerver_count_message_by_huddle
from zerver.lib.timestamp import datetime_to_string, is_timezone_aware
from zerver.models import UserProfile, Message

from typing import Any

class Command(BaseCommand):
    help = """Fills Analytics tables.

    Run as a cron job that runs every hour."""

    def add_arguments(self, parser):
        # type: (ArgumentParser) -> None
        parser.add_argument('--range-start', '-s',
                            type=str,
                            help="Time to backfill from.")
        parser.add_argument('--range-end', '-e',
                            type=str,
                            help='Time to backfill to.',
                            default=datetime_to_string(timezone.now()))
        parser.add_argument('--utc',
                            type=bool,
                            help="Interpret --range-start and --range-end as times in UTC.",
                            default=False)

    def handle(self, *args, **options):
        # type: (*Any, **Any) -> None
        range_start = parse_datetime(options['range_start'])
        if 'range_end' in options:
            range_end = parse_datetime(options['range_end'])
        else:
            range_end = range_start - timedelta(seconds = 3600)

        # throw error if start time is greater than end time
        if range_start > range_end:
            raise ValueError("--range-start cannot be greater than --range-end.")

        if options['utc'] is True:
            range_start = range_start.replace(tzinfo=timezone.utc)
            range_end = range_end.replace(tzinfo=timezone.utc)

        if not (is_timezone_aware(range_start) and is_timezone_aware(range_end)):
            raise ValueError("--range-start and --range-end must be timezone aware. Maybe you meant to use the --utc option?")

        stats = [
            CountStat('active_humans', zerver_count_user_by_realm, {'is_bot': False, 'is_active': True},
                      'gauge', 'day'),
            CountStat('active_bots', zerver_count_user_by_realm, {'is_bot': True, 'is_active': True},
                      'gauge', 'day'),
            CountStat('messages_sent', zerver_count_message_by_user, {}, 'hour', 'hour')]

        # process analytics counts for stats
        for stat in stats:
            process_count_stat(stat, range_start, range_end)
