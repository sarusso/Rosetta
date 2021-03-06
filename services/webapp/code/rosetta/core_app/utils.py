import os
import hashlib
import traceback
import hashlib
import random
import subprocess
import logging
from collections import namedtuple
import datetime, calendar, pytz
from dateutil.tz import tzoffset

from .exceptions import ErrorMessage

# Setup logging
logger = logging.getLogger(__name__)


# Colormap (See https://bhaskarvk.github.io/colormap/reference/colormap.html)
color_map = ["#440154", "#440558", "#450a5c", "#450e60", "#451465", "#461969",
             "#461d6d", "#462372", "#472775", "#472c7a", "#46307c", "#45337d",
             "#433880", "#423c81", "#404184", "#3f4686", "#3d4a88", "#3c4f8a",
             "#3b518b", "#39558b", "#37598c", "#365c8c", "#34608c", "#33638d",
             "#31678d", "#2f6b8d", "#2d6e8e", "#2c718e", "#2b748e", "#29788e",
             "#287c8e", "#277f8e", "#25848d", "#24878d", "#238b8d", "#218f8d",
             "#21918d", "#22958b", "#23988a", "#239b89", "#249f87", "#25a186",
             "#25a584", "#26a883", "#27ab82", "#29ae80", "#2eb17d", "#35b479",
             "#3cb875", "#42bb72", "#49be6e", "#4ec16b", "#55c467", "#5cc863",
             "#61c960", "#6bcc5a", "#72ce55", "#7cd04f", "#85d349", "#8dd544",
             "#97d73e", "#9ed93a", "#a8db34", "#b0dd31", "#b8de30", "#c3df2e",
             "#cbe02d", "#d6e22b", "#e1e329", "#eae428", "#f5e626", "#fde725"]

#======================
#  Utility functions
#======================

def booleanize(*args, **kwargs):
    # Handle both single value and kwargs to get arg name
    name = None
    if args and not kwargs:
        value=args[0]
    elif kwargs and not args:
        for item in kwargs:
            name  = item
            value = kwargs[item]
            break
    else:
        raise Exception('Internal Error')
    
    # Handle shortcut: an arg with its name equal to ist value is considered as True
    if name==value:
        return True
    
    if isinstance(value, bool):
        return value
    else:
        if value.upper() in ('TRUE', 'YES', 'Y', '1'):
            return True
        else:
            return False


def send_email(to, subject, text):

    # Importing here instead of on top avoids circular dependencies problems when loading booleanize in settings
    from django.conf import settings
    
    if settings.DJANGO_EMAIL_SERVICE == 'Sendgrid':
        import sendgrid
        from sendgrid.helpers.mail import Email,Content,Mail

        sg = sendgrid.SendGridAPIClient(apikey=settings.DJANGO_EMAIL_APIKEY)
        from_email = Email(settings.DJANGO_EMAIL_FROM)
        to_email = Email(to)
        subject = subject
        content = Content('text/plain', text)
        mail = Mail(from_email, subject, to_email, content)
        
        try:
            response = sg.client.mail.send.post(request_body=mail.get())

            #logger.debug(response.status_code)
            #logger.debug(response.body)
            #logger.debug(response.headers)
        except Exception as e:
            logger.error(e)
        
        #logger.debug(response)
    

def format_exception(e, debug=False):
    
    # Importing here instead of on top avoids circular dependencies problems when loading booleanize in settings
    from django.conf import settings

    if settings.DEBUG:
        # Cutting away the last char removed the newline at the end of the stacktrace 
        return str('Got exception "{}" of type "{}" with traceback:\n{}'.format(e.__class__.__name__, type(e), traceback.format_exc()))[:-1]
    else:
        return str('Got exception "{}" of type "{}" with traceback "{}"'.format(e.__class__.__name__, type(e), traceback.format_exc().replace('\n', '|')))


def log_user_activity(level, msg, request, caller=None):

    # Get the caller function name through inspect with some logic
    #import inspect
    #caller =  inspect.stack()[1][3]
    #if caller == "post":
    #    caller =  inspect.stack()[2][3]
    
    try:
        msg = str(caller) + " view - USER " + str(request.user.email) + ": " + str(msg)
    except AttributeError:
        msg = str(caller) + " view - USER UNKNOWN: " + str(msg)

    try:
        level = getattr(logging, level)
    except:
        raise
    
    logger.log(level, msg)


def username_hash(email):
    '''Create md5 base 64 (25 chrars) hash from user email:'''             
    m = hashlib.md5()
    m.update(email)
    username = m.hexdigest().decode('hex').encode('base64')[:-3]
    return username


def random_username():
    '''Create a random string of 156 chars to be used as username'''             
    username = ''.join(random.choice('abcdefghilmnopqrtuvz') for _ in range(16))
    return username


def finalize_user_creation(user):

    from .models import Profile, KeyPair

    # Create profile
    logger.debug('Creating user profile for user "{}"'.format(user.email))
    Profile.objects.create(user=user)

    # Generate user keys
    out = os_shell('mkdir -p /data/resources/keys/', capture=True)
    if not out.exit_code == 0:
        logger.error(out)
        raise ErrorMessage('Something went wrong in creating user keys folder. Please contact support')
        
    command= "/bin/bash -c \"ssh-keygen -q -t rsa -N '' -f /data/resources/keys/{}_id_rsa 2>/dev/null <<< y >/dev/null\"".format(user.username)                        
    out = os_shell(command, capture=True)
    if not out.exit_code == 0:
        logger.error(out)
        raise ErrorMessage('Something went wrong in creating user keys. Please contact support')
        
    
    # Create key objects
    KeyPair.objects.create(user = user,
                          default = True,
                          private_key_file = '/data/resources/keys/{}_id_rsa'.format(user.username),
                          public_key_file = '/data/resources/keys/{}_id_rsa.pub'.format(user.username))
    

def sanitize_shell_encoding(text):
    return text.encode("utf-8", errors="ignore")


def format_shell_error(stdout, stderr, exit_code):
    
    string  = '\n#---------------------------------'
    string += '\n# Shell exited with exit code {}'.format(exit_code)
    string += '\n#---------------------------------\n'
    string += '\nStandard output: "'
    string += sanitize_shell_encoding(stdout)
    string += '"\n\nStandard error: "'
    string += sanitize_shell_encoding(stderr) +'"\n\n'
    string += '#---------------------------------\n'
    string += '# End Shell output\n'
    string += '#---------------------------------\n'

    return string


def os_shell(command, capture=False, verbose=False, interactive=False, silent=False):
    '''Execute a command in the OS shell. By default prints everything. If the capture switch is set,
    then it returns a namedtuple with stdout, stderr, and exit code.'''
    
    if capture and verbose:
        raise Exception('You cannot ask at the same time for capture and verbose, sorry')

    # Log command
    logger.debug('Shell executing command: "%s"', command)

    # Execute command in interactive mode    
    if verbose or interactive:
        exit_code = subprocess.call(command, shell=True)
        if exit_code == 0:
            return True
        else:
            return False

    # Execute command getting stdout and stderr
    # http://www.saltycrane.com/blog/2008/09/how-get-stdout-and-stderr-using-python-subprocess-module/
    
    process          = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (stdout, stderr) = process.communicate()
    exit_code        = process.wait()

    # Convert to str (Python 3)
    stdout = stdout.decode(encoding='UTF-8')
    stderr = stderr.decode(encoding='UTF-8')

    # Formatting..
    stdout = stdout[:-1] if (stdout and stdout[-1] == '\n') else stdout
    stderr = stderr[:-1] if (stderr and stderr[-1] == '\n') else stderr

    # Output namedtuple
    Output = namedtuple('Output', 'stdout stderr exit_code')

    if exit_code != 0:
        if capture:
            return Output(stdout, stderr, exit_code)
        else:
            print(format_shell_error(stdout, stderr, exit_code))      
            return False    
    else:
        if capture:
            return Output(stdout, stderr, exit_code)
        elif not silent:
            # Just print stdout and stderr cleanly
            print(stdout)
            print(stderr)
            return True
        else:
            return True


def get_md5(string):
    if not string:
        raise Exception("Colund not compute md5 of empty/None value")
    
    m = hashlib.md5()
    
    # Fix for Python3
    try:
        if isinstance(string,unicode):
            string=string.encode('utf-8')
    except NameError:
        string=string.encode('utf-8')
        
    m.update(string)
    md5 = str(m.hexdigest())
    return md5


#=========================
#   Time 
#=========================

def timezonize(timezone):
    '''Convert a string representation of a timezone to its pytz object or do nothing if the argument is already a pytz timezone'''
    
    # Check if timezone is a valid pytz object is hard as it seems that they are spread arount the pytz package.
    # Option 1): Try to convert if string or unicode, else try to
    # instantiate a datetiem object with the timezone to see if it is valid 
    # Option 2): Get all memebers of the pytz package and check for type, see
    # http://stackoverflow.com/questions/14570802/python-check-if-object-is-instance-of-any-class-from-a-certain-module
    # Option 3) perform a hand.made test. We go for this one, tests would fail if it gets broken
    
    if not 'pytz' in str(type(timezone)):
        timezone = pytz.timezone(timezone)
    return timezone

def now_t():
    '''Return the current time in epoch seconds'''
    return now_s()

def now_s():
    '''Return the current time in epoch seconds'''
    return calendar.timegm(now_dt().utctimetuple())

def now_dt(tzinfo='UTC'):
    '''Return the current time in datetime format'''
    if tzinfo != 'UTC':
        raise NotImplementedError()
    return datetime.datetime.utcnow().replace(tzinfo = pytz.utc)

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
        time_dt = datetime.datetime(*args, tzinfo=tzoffset(None, offset_s))
    else:
        # Standard  timezone
        time_dt = timezone.localize(datetime.datetime(*args))

    # Check consistency    
    if not trustme and timezone != pytz.UTC:
        if not check_dt_consistency(time_dt):
            raise Exception('Sorry, time {} does not exists on timezone {}'.format(time_dt, timezone))

    return  time_dt

def get_tz_offset_s(time_dt):
    '''Get the time zone offset in seconds'''
    return s_from_dt(time_dt.replace(tzinfo=pytz.UTC)) - s_from_dt(time_dt)

def check_dt_consistency(date_dt):
    '''Check that the timezone is consistent with the datetime (some conditions in Python lead to have summertime set in winter)'''

    # https://en.wikipedia.org/wiki/Tz_database
    # https://www.iana.org/time-zones
    
    if date_dt.tzinfo is None:
        return True
    else:
        
        # This check is quite heavy but there is apparently no other way to do it.
        if date_dt.utcoffset() != dt_from_s(s_from_dt(date_dt), tz=date_dt.tzinfo).utcoffset():
            return False
        else:
            return True

def correct_dt_dst(datetime_obj):
    '''Check that the dst is correct and if not change it'''

    # https://en.wikipedia.org/wiki/Tz_database
    # https://www.iana.org/time-zones

    if datetime_obj.tzinfo is None:
        return datetime_obj

    # Create and return a New datetime object. This corrects the DST if errors are present.
    return dt(datetime_obj.year,
              datetime_obj.month,
              datetime_obj.day,
              datetime_obj.hour,
              datetime_obj.minute,
              datetime_obj.second,
              datetime_obj.microsecond,
              tzinfo=datetime_obj.tzinfo)

def change_tz(dt, tz):
    return dt.astimezone(timezonize(tz))

def dt_from_t(timestamp_s, tz=None):
    '''Create a datetime object from an epoch timestamp in seconds. If no timezone is given, UTC is assumed'''
    # TODO: check if uniform everything on this one or not.
    return dt_from_s(timestamp_s=timestamp_s, tz=tz)
    
def dt_from_s(timestamp_s, tz=None):
    '''Create a datetime object from an epoch timestamp in seconds. If no timezone is given, UTC is assumed'''

    if not tz:
        tz = "UTC"
    try:
        timestamp_dt = datetime.datetime.utcfromtimestamp(float(timestamp_s))
    except TypeError:
        raise Exception('timestamp_s argument must be string or number, got {}'.format(type(timestamp_s)))

    pytz_tz = timezonize(tz)
    timestamp_dt = timestamp_dt.replace(tzinfo=pytz.utc).astimezone(pytz_tz)
    
    return timestamp_dt

def s_from_dt(dt):
    '''Returns seconds with floating point for milliseconds/microseconds.'''
    if not (isinstance(dt, datetime.datetime)):
        raise Exception('s_from_dt function called without datetime argument, got type "{}" instead.'.format(dt.__class__.__name__))
    microseconds_part = (dt.microsecond/1000000.0) if dt.microsecond else 0
    return  ( calendar.timegm(dt.utctimetuple()) + microseconds_part)

def dt_from_str(string, timezone=None):

    # Supported formats on UTC
    # 1) YYYY-MM-DDThh:mm:ssZ
    # 2) YYYY-MM-DDThh:mm:ss.{u}Z

    # Supported formats with offset    
    # 3) YYYY-MM-DDThh:mm:ss+ZZ:ZZ
    # 4) YYYY-MM-DDThh:mm:ss.{u}+ZZ:ZZ

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
        offset_s = (int(offset.split(':')[0])*60 + int(offset.split(':')[1]) )* 60   
        
    elif ('-') in time:
        # Negative offset
        time, offset = time.split('-')
        # Set time and extract negative offset
        offset_s = -1 * (int(offset.split(':')[0])*60 + int(offset.split(':')[1])) * 60      
    
    else:
        raise Exception('Format error')
    
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

class dt_range(object):

    def __init__(self, from_dt, to_dt, timeSlotSpan):

        self.from_dt      = from_dt
        self.to_dt        = to_dt
        self.timeSlotSpan = timeSlotSpan

    def __iter__(self):
        self.current_dt = self.from_dt
        return self

    def __next__(self):

        # Iterator logic
        if self.current_dt > self.to_dt:
            raise StopIteration
        else:
            prev_current_dt = self.current_dt
            self.current_dt = self.current_dt + self.timeSlotSpan
            return prev_current_dt

    # Python 2.x
    def next(self):
        return self.__next__()


#================================
#  Others
#================================

def debug_param(**kwargs):
    for item in kwargs:
        logger.critical('Param "{}": "{}"'.format(item, kwargs[item]))

def get_my_ip():
    import socket
    hostname = socket.gethostname()
    my_ip = socket.gethostbyname(hostname)
    return my_ip

def get_webapp_conn_string():
    webapp_host = os.environ.get('ROSETTA_WEBAPP_HOST', get_my_ip())
    webapp_port = os.environ.get('ROSETTA_WEBAPP_PORT', '8080')
    webapp_conn_string = 'http://{}:{}'.format(webapp_host, webapp_port)
    return webapp_conn_string

def get_local_docker_registry_conn_string():
    local_docker_registry_host = os.environ.get('LOCAL_DOCKER_REGISTRY_HOST', 'dregistry')
    local_docker_registry_port = os.environ.get('LOCAL_DOCKER_REGISTRY_PORT', '5000')
    local_docker_registry_conn_string = '{}:{}'.format(local_docker_registry_host, local_docker_registry_port)
    return local_docker_registry_conn_string
    
def get_tunnel_host():
    tunnel_host = os.environ.get('ROSETTA_TUNNEL_HOST', 'localhost')
    return tunnel_host

def hash_string_to_int(string):
    #int_hash = 0 
    #for char in string:
    #    int_hash += ord(char)
    #return int_hash
    return int(hashlib.sha1(string.encode('utf8')).hexdigest(), 16) #% (10 ** 8)



#================================
#  Tunnel setup
#================================

def setup_tunnel(task):

    # Importing here instead of on top avoids circular dependencies problems when loading booleanize in settings
    from .models import Task, KeyPair, TaskStatuses
    
    # If there is no tunnel port allocated yet, find one
    if not task.tunnel_port:

        # Get a free port fot the tunnel:
        allocated_tunnel_ports = []
        for other_task in Task.objects.all():
            if other_task.tunnel_port and not other_task.status in [TaskStatuses.exited, TaskStatuses.stopped]:
                allocated_tunnel_ports.append(other_task.tunnel_port)

        for port in range(7000, 7021):
            if not port in allocated_tunnel_ports:
                tunnel_port = port
                break
        if not tunnel_port:
            logger.error('Cannot find a free port for the tunnel for task "{}"'.format(task))
            raise ErrorMessage('Cannot find a free port for the tunnel to the task')

        task.tunnel_port = tunnel_port
        task.save()


    # Check if the tunnel is active and if not create it
    logger.debug('Checking if task "{}" has a running tunnel'.format(task))

    out = os_shell('ps -ef | grep ":{}:{}:{}" | grep -v grep'.format(task.tunnel_port, task.ip, task.port), capture=True)

    if out.exit_code == 0:
        logger.debug('Task "{}" has a running tunnel, using it'.format(task))
    else:
        logger.debug('Task "{}" has no running tunnel, creating it'.format(task))

        # Get user keys
        user_keys = KeyPair.objects.get(user=task.user, default=True)

        # Tunnel command
        if task.computing.type == 'remotehop':           
            
            # Get computing params
            first_host = task.computing.get_conf_param('first_host')
            first_user = task.computing.get_conf_param('first_user')
            #second_host = task.computing.get_conf_param('second_host')
            #second_user = task.computing.get_conf_param('second_user')
            #setup_command = task.computing.get_conf_param('setup_command')
            #base_port = task.computing.get_conf_param('base_port')
                     
            tunnel_command= 'ssh -4 -i {} -o StrictHostKeyChecking=no -nNT -L 0.0.0.0:{}:{}:{} {}@{} & '.format(user_keys.private_key_file, task.tunnel_port, task.ip, task.port, first_user, first_host)

        else:
            tunnel_command= 'ssh -4 -o StrictHostKeyChecking=no -nNT -L 0.0.0.0:{}:{}:{} localhost & '.format(task.tunnel_port, task.ip, task.port)
        
        background_tunnel_command = 'nohup {} >/dev/null 2>&1 &'.format(tunnel_command)

        # Log
        logger.debug('Opening tunnel with command: {}'.format(background_tunnel_command))

        # Execute
        subprocess.Popen(background_tunnel_command, shell=True)











