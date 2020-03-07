import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .utils import os_shell

if 'sqlite' in settings.DATABASES['default']['ENGINE']:
    from .fields import JSONField
else:
    from django.contrib.postgres.fields import JSONField

class ConfigurationError(Exception):
    pass

class ConsistencyError(Exception):
    pass


# Setup logging
import logging
logger = logging.getLogger(__name__)


# Task statuses
class TaskStatuses(object):
    created = 'created'
    running = 'running'
    stopped = 'stopped'
    exited = 'exited'


#=========================
#  Profile 
#=========================

class Profile(models.Model):
    uuid      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user      = models.OneToOneField(User, on_delete=models.CASCADE)
    timezone  = models.CharField('User Timezone', max_length=36, default='UTC')
    authtoken = models.CharField('User auth token', max_length=36, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.authtoken:
            self.authtoken = str(uuid.uuid4())
        super(Profile, self).save(*args, **kwargs)

    def __unicode__(self):
        return str('Profile of user "{}"'.format(self.user.username))


#=========================
#  Login Token 
#=========================

class LoginToken(models.Model):
    uuid  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user  = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.CharField('Login token', max_length=36)



#=========================
#  Containers
#=========================
class Container(models.Model):

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name='+', on_delete=models.CASCADE, null=True)  
    # If a container has no user, it will be available to anyone. Can be created, edited and deleted only by admins.

    name          = models.CharField('Container Name', max_length=255, blank=False, null=False)    
    image         = models.CharField('Container image', max_length=255, blank=False, null=False)
    type          = models.CharField('Container type', max_length=36, blank=False, null=False)
    registry      = models.CharField('Container registry', max_length=255, blank=False, null=False)
    service_ports = models.CharField('Container service ports', max_length=36, blank=True, null=True)
    #private       = models.BooleanField('Container is private and needs auth to be pulled from the registry')

    def __str__(self):
        return str('Container of type "{}" with image "{}" with service ports "{}" from registry "{}" of user "{}"'.format(self.type, self.image, self.service_ports, self.registry, self.user))

    @property
    def id(self):
        return str(self.uuid).split('-')[0]

    #@property
    #def name(self):
    #    return self.image.split(':')[0].replace('_',' ').replace('-', ' ').replace('/', ' ').title()

#=========================
#  Computing resources
#=========================

# TODO: this must be an abstract class. Or maybe not? Maybe Add ComputingConfiguration/Handler with the relevant fields and methods?
#       ...so that can be used as foreign key in the tasks as well? Examples: ComputingConfiguration ComputingType ComputingHandler

class Computing(models.Model):

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name='+', on_delete=models.CASCADE, null=True)
    # If a compute resource has no user, it will be available to anyone. Can be created, edited and deleted only by admins.
    
    name = models.CharField('Computing Name', max_length=255, blank=False, null=False)
    type = models.CharField('Computing Type', max_length=255, blank=False, null=False)

    requires_sys_conf  = models.BooleanField(default=False)
    requires_user_conf = models.BooleanField(default=False)

    def __str__(self):
        return str('Computing Resource "{}" of user "{}"'.format(self.name, self.user))

    @property
    def id(self):
        return str(self.uuid).split('-')[0]

    # Validate conf
    def validate_conf_data(self, sys_conf_data=None, user_conf_data=None):
        
        if self.type == 'local':
            pass
        
        elif self.type == 'remote':
            # Check that we have all the data for a remote computing resource

            # Look for host:
            host_found = False
            if sys_conf_data  and 'host' in sys_conf_data  and sys_conf_data['host']:  host_found=True
            if user_conf_data and 'host' in user_conf_data and user_conf_data['host']: host_found=True
            if not host_found:
                raise ConfigurationError('Missing host in conf')
            
            
            # Look for user:
            user_found = False
            if sys_conf_data  and 'user' in sys_conf_data  and sys_conf_data['user']:  user_found=True
            if user_conf_data and 'user' in user_conf_data and user_conf_data['user']: user_found=True
            if not user_found:
                raise ConfigurationError('Missing user in conf')               

            # Look for password/identity:
            password_found = False
            identity_found = False
            if sys_conf_data  and 'password' in sys_conf_data  and sys_conf_data['password']:  password_found=True
            if user_conf_data and 'password' in user_conf_data and user_conf_data['password']: password_found=True
            if sys_conf_data  and 'identity' in sys_conf_data  and sys_conf_data['identity']:  identity_found=True
            if user_conf_data and 'identity' in user_conf_data and user_conf_data['identity']: identity_found=True       
            if not password_found and not identity_found:
                raise ConfigurationError('Missing password or identity in conf')

        elif self.type == 'slurm':
            raise NotImplementedError('Not yet implemented for Slurm')

        else:
            raise ConsistencyError('Unknown computing type "{}"'.format(self.type))
    
    @property    
    def sys_conf_data(self):          
        return ComputingSysConf.objects.get(computing=self).data
    
    @property    
    def user_conf_data(self):
        try:
            return self._user_conf_data
        except AttributeError:
            raise AttributeError('User conf data is not yet attached, please attach it before accessing.')
    
    def attach_user_conf_data(self, user):
        if self.user and self.user != user:
            raise Exception('Cannot attach a conf data for another user (my user="{}", another user="{}"'.format(self.user, user)) 
        try:
            self._user_conf_data = ComputingUserConf.objects.get(computing=self, user=user).data
        except ComputingUserConf.DoesNotExist:
            self._user_conf_data = None

    # Get id_rsa file
    #@property
    #def id_rsa_file(self):
    #    try:
    #        id_rsa_file = self.user_conf_data['id_rsa']
    #    except (TypeError, KeyError, AttributeError):
    #        try:
    #            id_rsa_file = self.sys_conf_data['id_rsa']
    #        except:
    #            id_rsa_file = None
    #    return id_rsa_file

    def get_conf_param(self, param):
        try:
            param_value = self.sys_conf_data[param]
        except (TypeError, KeyError):
            param_value = self.user_conf_data[param]
        return param_value


class ComputingSysConf(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    computing = models.ForeignKey(Computing, related_name='+', on_delete=models.CASCADE)
    data = JSONField(blank=True, null=True)

    @property
    def id(self):
        return str(self.uuid).split('-')[0]


class ComputingUserConf(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name='+', on_delete=models.CASCADE, null=True)
    computing = models.ForeignKey(Computing, related_name='+', on_delete=models.CASCADE)
    data = JSONField(blank=True, null=True)

    @property
    def id(self):
        return str(self.uuid).split('-')[0]


#=========================
#  Tasks 
#=========================
class Task(models.Model):
    uuid      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user      = models.ForeignKey(User, related_name='+', on_delete=models.CASCADE)
    tid       = models.CharField('Task ID', max_length=64, blank=False, null=False)
    name      = models.CharField('Task name', max_length=36, blank=False, null=False)
    status    = models.CharField('Task status', max_length=36, blank=True, null=True)
    created   = models.DateTimeField('Created on', default=timezone.now)
    pid       = models.IntegerField('Task pid', blank=True, null=True)
    port      = models.IntegerField('Task port', blank=True, null=True)
    ip        = models.CharField('Task ip address', max_length=36, blank=True, null=True)
    tunnel_port = models.IntegerField('Task tunnel port', blank=True, null=True)

    # Links
    computing = models.ForeignKey(Computing, related_name='+', on_delete=models.CASCADE)
    container = models.ForeignKey('Container', on_delete=models.CASCADE, related_name='+')

    # Auth
    auth_user     = models.CharField('Task auth user', max_length=36, blank=True, null=True)
    auth_password = models.CharField('Task auth password', max_length=36, blank=True, null=True)
    access_method = models.CharField('Task access method', max_length=36, blank=True, null=True)

    def save(self, *args, **kwargs):
        
        try:
            getattr(TaskStatuses, str(self.status))
        except AttributeError:
            raise Exception('Invalid status "{}"'.format(self.status))

        # Call parent save
        super(Task, self).save(*args, **kwargs)


    def __str__(self):
        return str('Task "{}" of user "{}" in status "{}" (TID "{}")'.format(self.name, self.user.email, self.status, self.tid))


    def update_status(self):
        if self.computing == 'local':
            
            check_command = 'sudo docker inspect --format \'{{.State.Status}}\' ' + self.tid # or, .State.Running
            out = os_shell(check_command, capture=True)
            logger.debug('Status: "{}"'.format(out.stdout))
            if out.exit_code != 0: 
                if (('No such' in out.stderr) and (self.tid in out.stderr)):
                    logger.debug('Task "{}" is not running in reality'.format(self.tid))
                self.status = TaskStatuses.exited
            else:
                if out.stdout == 'running':
                    self.status = TaskStatuses.running
                    
                elif out.stdout == 'exited':
                    self.status = TaskStatuses.exited
                    
                else:
                    raise Exception('Unknown task status: "{}"'.format(out.stdout))
                
            self.save()                   

    @property
    def id(self):
        return str(self.uuid).split('-')[0]




