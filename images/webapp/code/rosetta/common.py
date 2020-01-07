import pytz
import time
import calendar
import logging
from datetime import datetime
import traceback
from rest_framework import serializers

try:
    from dateutil.tz import tzoffset
except ImportError:
    tzoffset = None
    
class ConsistencyException(Exception):
    pass

class AlreadyExistentException(Exception):
    pass

class DoNotCommitTransactionException(Exception):
    pass

def format_exception(e):
    return 'Exception: ' + str(e) + '; Traceback: ' + traceback.format_exc().replace('\n','|')

class HyperlinkedModelSerializerWithId(serializers.HyperlinkedModelSerializer):
    """Extend the HyperlinkedModelSerializer to add IDs as well for the best of
    both worlds.
    """
    id = serializers.ReadOnlyField()


# def setup_logger(logger, loglevel):
#     handler = logging.StreamHandler()
#     formatter = logging.Formatter('%(name)s - %(levelname)s: %(message)s')
#     handler.setFormatter(formatter)
#     logger.addHandler(handler)
#     logger.setLevel(loglevel)
#     return logger


#===================================
#  Time management
#===================================

# Note: most of the following routines are extrapolated from the
# time package of the Luna project (https://github.com/sarusso/Luna)
# by courtesy of Stefano Alberto Russo. If you find and fix any bug,
# please open a pull request with the fix for Luna as well. Thank you!

def timezonize(timezone):
    if not 'pytz' in str(type(timezone)):
        timezone = pytz.timezone(timezone)
    return timezone

def t_now():
    return time.time()  


def dt(*args, **kwargs):
    '''Initialize a datetime object in the proper way. Using the standard datetime leads to a lot of
     problems with the tz package. Also, it forces UTC timezone if no timezone is specified'''
    
    if 'tz' in kwargs:
        tzinfo = kwargs.pop('tz')
    else:
        tzinfo  = kwargs.pop('tzinfo', None)
        
    offset_s  = kwargs.pop('offset_s', None)   
    trustme   = kwargs.pop('trustme', None)
    
    if kwargs:
        raise Exception('Unhandled arg: "{}".'.format(kwargs))
        
    if (tzinfo is None):
        # Force UTC if None
        timezone = timezonize('UTC')
        
    else:
        timezone = timezonize(tzinfo)
    
    if offset_s:
        # Special case for the offset
        if not tzoffset:
            raise Exception('For ISO date with offset please install dateutil')
        time_dt = datetime(*args, tzinfo=tzoffset(None, offset_s))
    else:
        # Standard  timezone
        time_dt = timezone.localize(datetime(*args))

    # Check consistency    
    if not trustme and timezone != pytz.UTC:
        if not check_dt_consistency(time_dt):
            raise Exception('Sorry, time {} does not exists on timezone {}'.format(time_dt, timezone))

    return  time_dt

def dt_from_s(timestamp_s, tz=None):
    if not tz:
        tz = "UTC"
    try:
        timestamp_dt = datetime.utcfromtimestamp(float(timestamp_s))
    except TypeError:
        raise Exception('timestamp_s argument must be string or number, got {}'.format(type(timestamp_s)))

    pytz_tz = timezonize(tz)
    timestamp_dt = timestamp_dt.replace(tzinfo=pytz.utc).astimezone(pytz_tz)
    
    return timestamp_dt

def s_from_dt(dt):
    if not (isinstance(dt, datetime)):
        raise Exception('s_from_dt function called without datetime argument, got type "{}" instead.'.format(dt.__class__.__name__))
    microseconds_part = (dt.microsecond/1000000.0) if dt.microsecond else 0
    return  ( calendar.timegm(dt.utctimetuple()) + microseconds_part)

def check_dt_consistency(date_dt):
    if date_dt.tzinfo is None:
        return True
    else: 
        if date_dt.utcoffset() != dt_from_s(s_from_dt(date_dt), tz=date_dt.tzinfo).utcoffset():
            return False
        else:
            return True

def dt_from_str(string, timezone=None):

    # Supported formats on UTC
    # 1) YYYY-MM-DDThh:mm:ssZ
    # 2) YYYY-MM-DDThh:mm:ss.{u}Z

    # Supported formats with offset    
    # 3) YYYY-MM-DDThh:mm:ss+ZZ:ZZ
    # 4) YYYY-MM-DDThh:mm:ss.{u}+ZZ:ZZ
    
    # Also:
    # 5) YYYY-MM-DDThh:mm:ss (without the trailing Z, and assume it on UTC)

    # Split and parse standard part
    date, time = string.split('T')
    
    if time.endswith('Z'):
        # UTC
        offset_s = 0
        time = time[:-1]
        
    elif ('+') in time:
        # Positive offset
        time, offset = time.split('+')
        # Set time and extract positive offset
        if ':' in offset:
            offset_s = (int(offset[0:2])*60 + int(offset[3:5]))* 60
        else:
            offset_s = (int(offset[0:2])*60 + int(offset[2:4]))* 60
               
        
    elif ('-') in time:
        # Negative offset
        time, offset = time.split('-')
        # Set time and extract negative offset
        if ':' in offset:
            offset_s = -1 * (int(offset[0:2])*60 + int(offset[3:5]))* 60
        else:
            offset_s = -1 * (int(offset[0:2])*60 + int(offset[2:4]))* 60
    
    
    else:
        # Assume UTC
        offset_s = 0
        #raise InputException('Format error')
    
    # Handle time
    hour, minute, second = time.split(':')
    
    # Now parse date (easy)
    year, month, day = date.split('-') 

    # Convert everything to int
    year    = int(year)
    month   = int(month)
    day     = int(day)
    hour    = int(hour)
    minute  = int(minute)
    if '.' in second:
        usecond = int(second.split('.')[1])
        second  = int(second.split('.')[0])
    else:
        second  = int(second)
        usecond = 0
    
    return dt(year, month, day, hour, minute, second, usecond, offset_s=offset_s)


def dt_to_str(dt):
    '''Return the ISO representation of the datetime as argument'''
    return dt.isoformat()
