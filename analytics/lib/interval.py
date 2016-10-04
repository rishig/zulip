from django.utils import timezone
from datetime import datetime, timedelta, MINYEAR

from zerver.lib.timestamp import is_timezone_aware
from six import text_type

MIN_TIME = datetime(MINYEAR, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

# Name isn't great .. fixedinterval? timerange? Trying to distinguish
# generic intervals like 'hour' or 'quarter' from fixed intervals like
# 'Aug 3 2016 from 9-10am'
class TimeInterval(object):
    def __init__(self, interval, end = timezone.now(), floor_to_boundary = 'hour'):
        # type: (str, datetime, str) -> None
        # Not the best logic for when we have intervals like 'quarter', but okay for now
        if not is_timezone_aware(end):
            raise ValueError("end must be timezone aware")
        if floor_to_boundary is None:
            self.end = end
        else:
            self.end = floor_to_interval_boundary(end, floor_to_boundary)
        self.interval = interval
        if interval == 'gauge':
            self.start = MIN_TIME
        else:
            self.start = subtract_interval(self.end, interval)

# Perhaps the right way to do the next two functions is to have an interval class
# (subclassed to hourinterval, dayinterval, etc) with methods like floor,
# subtract, and subinterval. Seems like overkill for now, though.
def floor_to_interval_boundary(datetime_object, interval):
    # type: (datetime, text_type) -> datetime
    # datetime objects are (year, month, day, hour, minutes, seconds, microseconds)
    if interval == 'day':
        return datetime(*datetime_object.timetuple()[:3]).replace(tzinfo=datetime_object.tzinfo)
    elif interval == 'hour':
        return datetime(*datetime_object.timetuple()[:4]).replace(tzinfo=datetime_object.tzinfo)
    elif interval == '15min': # unused
        timetuple = datetime_object.timetuple()
        return datetime(*timetuple[:4], minute = timetuple[5] - timetuple[5] % 15,
                        tzinfo=datetime_object.tzinfo)
    else:
        raise ValueError("Unknown or unfloorable interval", interval)

# Don't have to worry about leap seconds, since datetime doesn't support it
def subtract_interval(datetime_object, interval):
    # type: (datetime, str) -> datetime
    if interval == 'day':
        return datetime_object - timedelta(days = 1)
    elif interval == 'hour':
        return datetime_object - timedelta(seconds = 3600)
    else:
        raise ValueError("Unknown or unarithmetic interval", interval)

def subintervals(interval):
    # type: (str) -> List[str]
    if interval == 'day':
        return ['day', 'hour']
    elif interval == 'hour':
        return ['hour',]
    elif interval == 'gauge':
        return ['gauge',]
    else:
        raise ValueError("Unknown interval", interval)

def timeinterval_range(first, last, interval, step_interval):
    # type: (datetime, datetime, str, str) -> List[TimeInterval]
    end = floor_to_interval_boundary(last, step_interval)
    ans = []
    while end >= first:
        ans.append(TimeInterval(interval, end, floor_to_boundary=None))
        end = subtract_interval(end, step_interval)
    ans.reverse()
    return ans

# TODO: add sum smallest_interval
