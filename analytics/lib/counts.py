from django.db import connection
from datetime import timedelta, datetime

from analytics.models import InstallationCount, RealmCount, UserCount, StreamCount, HuddleCount, BaseCount
from analytics.lib.interval import TimeInterval, timeinterval_range
from zerver.models import Realm, UserProfile, Message, Stream, models

from typing import Any, Optional, Type
from six import text_type

class CountStat(object):
    def __init__(self, property, zerver_table, filter_args, analytics_table, smallest_interval, frequency):
        # type: (text_type, models.Model, Dict[str, bool], Type[BaseCount], str, str) -> None
        self.property = property
        self.zerver_table = zerver_table
        # might have to do something different for bitfields
        self.filter_args = filter_args
        self.analytics_table = analytics_table
        self.smallest_interval = smallest_interval
        self.frequency = frequency

COUNT_TYPES = frozenset(['zerver_pull', 'time_aggregate', 'cross_table_aggregate'])

# todo: incorporate these two arguments into a universal do_pull function.


def count_query(stat):
    # type: (CountStat) -> str
    return {(UserProfile, RealmCount) : count_user_by_realm_query,
            (Message, UserCount) : count_message_by_user_query,
            (Message, StreamCount) : count_message_by_stream_query,
            (Message, HuddleCount): count_messages_by_huddle_query,
            (Stream, RealmCount) : count_stream_by_realm_query}[(stat.zerver_table, stat.analytics_table)]

# todo: collapse these three?


def process_count(table, count_type, stat, time_interval, **kwargs):
    # type: (Type[BaseCount], str, CountStat, TimeInterval, **Any) -> None
    if not table.objects.filter(property = stat.property,
                               end_time = time_interval.end,
                               interval = time_interval.interval).exists():
        if count_type == 'zerver_pull':
            kwargs['query'] = count_query(stat)
            do_pull_from_zerver(stat, time_interval, **kwargs)
        elif count_type == 'time_aggregate':
            kwargs['end_time'] = time_interval
            do_aggregate_hour_to_day(stat, **kwargs)
        elif count_type == 'cross_table_aggregate':
            do_aggregate_to_summary_table(stat, time_interval, **kwargs)
        else:
            raise ValueError('Unknown count_type')


def process_count_stat(stat, range_start, range_end):
    # type: (CountStat, datetime, datetime) -> None
    # stats that hit the prod database
    for time_interval in timeinterval_range(range_start, range_end, stat.smallest_interval, stat.frequency):
        process_count(stat.analytics_table, 'zerver_pull', stat, time_interval)

    # aggregate hour to day
    for time_interval in timeinterval_range(range_start, range_end, 'day', stat.frequency):
        if stat.smallest_interval == 'hour':
            process_count(stat.analytics_table, 'time_aggregate', stat, time_interval)

    # aggregate to summary tables
    for interval in ['hour', 'day', 'gauge']:
        for frequency in ['hour', 'day']:
            for time_interval in timeinterval_range(range_start, range_end, interval, frequency):
                if stat.smallest_interval <= interval and stat.frequency == frequency and \
                                stat.analytics_table in (UserCount, StreamCount):
                    process_count(RealmCount, 'cross_table_aggregate', stat, time_interval,
                                  from_table=stat.analytics_table, to_table=RealmCount)
                process_count(InstallationCount, 'cross_table_aggregate', stat, time_interval,
                              from_table=RealmCount, to_table=InstallationCount)


# only two summary tables at the moment: RealmCount and InstallationCount.
# will have to generalize this a bit if more are added

def do_aggregate_to_summary_table(stat, time_interval, from_table, to_table):
    # type: (CountStat, TimeInterval, Type[BaseCount], Type[BaseCount]) -> None
    if to_table == RealmCount:
        id_cols = 'realm_id,'
        group_by = 'GROUP BY realm_id'
    elif to_table == InstallationCount:
        id_cols = ''
        group_by = ''
    else:
        raise ValueError("%s is not a summary table" % (to_table,))

    query = """
        INSERT INTO %(to_table)s (%(id_cols)s value, property, end_time, interval)
        SELECT %(id_cols)s COALESCE (sum(value), 0), '%(property)s', %%(end_time)s, '%(interval)s'
        FROM %(from_table)s WHERE
        (
            property = '%(property)s' AND
            end_time = %%(end_time)s AND
            interval = '%(interval)s'
        )
        %(group_by)s
    """ % {'to_table': to_table._meta.db_table,
           'id_cols' : id_cols,
           'from_table' : from_table._meta.db_table,
           'property' : stat.property,
           'interval' : time_interval.interval,
           'group_by' : group_by}
    cursor = connection.cursor()
    # todo: check if cursor supports the %(key)s syntax
    cursor.execute(query, {'end_time': time_interval.end})
    cursor.close()

def do_aggregate_hour_to_day(stat, end_time):
    # type: (CountStat, TimeInterval) -> None
    table = stat.analytics_table
    id_cols = ''.join([col + ', ' for col in table.extended_id()])
    group_by = 'GROUP BY %s' % id_cols if id_cols else ''
    query = """
        INSERT INTO %(table)s (%(id_cols)s value, property, end_time, interval)
        SELECT %(id_cols)s sum(value), '%(property)s', %%(end_time)s, 'day'
        FROM %(table)s WHERE
        (
            property = '%(property)s' AND
            end_time > %%(time_start)s AND
            end_time <= %%(time_end)s AND
            interval = 'hour'
        )
        %(group_by)s property
    """ % {'table': table._meta.db_table,
           'id_cols' : id_cols,
           'group_by' : group_by,
           'property': stat.property}
    cursor = connection.cursor()
    cursor.execute(query, {'end_time': end_time.end, 'time_start': end_time.end - timedelta(days=1), 'time_end': end_time.end})
    cursor.close()

## methods that hit the prod databases directly
# No left joins in Django ORM yet, so have to use raw SQL :(
# written in slightly more than needed generality, to reduce copy-paste errors
# as more of these are made / make it easy to extend to a pull_X_by_realm

def do_pull_from_zerver(stat, time_interval, query):
    # type: (CountStat, TimeInterval, str) -> None
    zerver_table = stat.zerver_table._meta.db_table
    join_args = ' '.join('AND %s.%s = %s' % (zerver_table, key, value) \
                         for key, value in stat.filter_args.items())

    # We do string replacement here because passing join_args as a param
    # may result in problems when running cursor.execute; we do
    # the string formatting prior so that cursor.execute runs it as sql
    query_ = query % {'zerver_table' : zerver_table,
                      'property' : stat.property,
                      'interval' : time_interval.interval,
                      'join_args' : join_args}
    cursor = connection.cursor()
    cursor.execute(query_, {'time_start': time_interval.start, 'time_end': time_interval.end})
    cursor.close()

count_user_by_realm_query = """
    INSERT INTO analytics_realmcount
        (realm_id, value, property, end_time, interval)
    SELECT
        zerver_realm.id, count(%(zerver_table)s),'%(property)s', %%(time_end)s, '%(interval)s'
    FROM zerver_realm
    LEFT JOIN zerver_userprofile
    ON
    (
        zerver_userprofile.realm_id = zerver_realm.id AND
        zerver_userprofile.date_joined >= %%(time_start)s AND
        zerver_userprofile.date_joined < %%(time_end)s
        %(join_args)s
    )
    WHERE
        zerver_realm.date_created < %%(time_end)s
    GROUP BY zerver_realm.id
"""

# currently .sender_id is only Message specific thing
count_message_by_user_query = """
    INSERT INTO analytics_usercount
        (user_id, realm_id, value, property, end_time, interval)
    SELECT
        zerver_userprofile.id, zerver_userprofile.realm_id, count(*), '%(property)s', %%(time_end)s, '%(interval)s'
    FROM zerver_userprofile
    JOIN zerver_message
    ON
    (
        zerver_message.sender_id = zerver_userprofile.id AND
        zerver_message.pub_date >= %%(time_start)s AND
        zerver_message.pub_date < %%(time_end)s
        %(join_args)s
    )
    WHERE
            zerver_userprofile.date_joined < %%(time_end)s
    GROUP BY zerver_userprofile.id
"""

count_message_by_stream_query = """
    INSERT INTO analytics_streamcount
        (stream_id, realm_id, value, property, end_time, interval)
    SELECT
        zerver_stream.id, zerver_stream.realm_id, count(*), '%(property)s', %%(time_end)s, '%(interval)s'
    FROM zerver_stream
    INNER JOIN zerver_recipient
    ON
    (
        zerver_recipient.type = 2 AND
        zerver_stream.id = zerver_recipient.type_id
    )
    INNER JOIN zerver_message
    ON
    (
        zerver_message.recipient_id = zerver_recipient.id AND
        zerver_message.pub_date >= %%(time_start)s AND
        zerver_message.pub_date < %%(time_end)s AND
        zerver_stream.date_created < %%(time_end)s
        %(join_args)s
    )
    GROUP BY zerver_stream.id
"""

count_stream_by_realm_query = """
        INSERT INTO analytics_realmcount
            (realm_id, value, property, end_time, interval)
    SELECT
        zerver_stream.realm_id, count(*), '%(property)s', %%(time_end)s, '%(interval)s'
    FROM zerver_stream
    LEFT JOIN zerver_recipient
    ON
    (
        zerver_recipient.type = 2 AND
        zerver_stream.id = zerver_recipient.type_id
    )
    GROUP BY zerver_stream.realm_id
"""

count_messages_by_huddle_query = '''
    INSERT INTO analytics_huddlecount
        (huddle_id, user_id, value, property, end_time, interval)
    SELECT
        zerver_message.recipient_id, zerver_message.sender_id, count(*), '%(property)s', %%(time_end)s, '%(interval)s'
    FROM zerver_message
    INNER JOIN zerver_recipient
    ON
    (
        zerver_recipient.type = 3 AND
        zerver_message.recipient_id = zerver_recipient.id AND
        zerver_message.pub_date >= %%(time_start)s AND
        zerver_message.pub_date < %%(time_end)s
        %(join_args)s
    )
    GROUP BY zerver_message.recipient_id, zerver_message.sender_id
'''
