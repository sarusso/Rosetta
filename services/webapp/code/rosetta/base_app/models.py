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
    sumbitted = 'sumbitted'
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

    name     = models.CharField('Container Name', max_length=255, blank=False, null=False)    
    image    = models.CharField('Container image', max_length=255, blank=False, null=False)
    type     = models.CharField('Container type', max_length=36, blank=False, null=False)
    registry = models.CharField('Container registry', max_length=255, blank=False, null=False)
    ports    = models.CharField('Container service ports', max_length=36, blank=True, null=True)

    # Capabilities
    supports_dynamic_ports = models.BooleanField(default=False)
    supports_user_auth = models.BooleanField(default=False)
    supports_pass_auth = models.BooleanField(default=False)


    def __str__(self):
        return str('Container of type "{}" with image "{}" and  ports "{}" from registry "{}" of user "{}"'.format(self.type, self.image, self.ports, self.registry, self.user))


    @property
    def id(self):
        return str(self.uuid).split('-')[0]



#=========================
#  Computing resources
#=========================

class Computing(models.Model):

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name='+', on_delete=models.CASCADE, null=True)
    # If a compute resource has no user, it will be available to anyone. Can be created, edited and deleted only by admins.
    
    name = models.CharField('Computing Name', max_length=255, blank=False, null=False)
    type = models.CharField('Computing Type', max_length=255, blank=False, null=False)

    require_sys_conf  = models.BooleanField(default=False)
    require_user_conf = models.BooleanField(default=False)
    require_user_keys = models.BooleanField(default=False)


    def __str__(self):
        if self.user:
            return str('Computing Resource "{}" of user "{}"'.format(self.name, self.user))
        else:
            return str('Computing Resource "{}"'.format(self.name))


    @property
    def id(self):
        return str(self.uuid).split('-')[0]


    @property    
    def sys_conf_data(self):
        try:
            return ComputingSysConf.objects.get(computing=self).data
        except ComputingSysConf.DoesNotExist:
            return None
    
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


    def get_conf_param(self, param):
        try:
            param_value = self.sys_conf_data[param]
        except (TypeError, KeyError):
            param_value = self.user_conf_data[param]
        return param_value


    @property
    def manager(self):
        from . import computing_managers
        ComputingManager = getattr(computing_managers, '{}ComputingManager'.format(self.type.title()))
        return ComputingManager()



class ComputingSysConf(models.Model):

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    computing = models.ForeignKey(Computing, related_name='+', on_delete=models.CASCADE)
    data = JSONField(blank=True, null=True)


    @property
    def id(self):
        return str(self.uuid).split('-')[0]


    def __str__(self):
        return str('Computing sys conf for {} with id "{}"'.format(self.computing, self.id))



class ComputingUserConf(models.Model):

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name='+', on_delete=models.CASCADE, null=True)
    computing = models.ForeignKey(Computing, related_name='+', on_delete=models.CASCADE)
    data = JSONField(blank=True, null=True)


    @property
    def id(self):
        return str('Computing sys conf for {} with id "{}" of user "{}"'.format(self.computing, self.id, self.user))



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
    auth_pass     = models.CharField('Task auth pass', max_length=36, blank=True, null=True)
    access_method = models.CharField('Task access method', max_length=36, blank=True, null=True)

    # Computing options
    computing_options = JSONField(blank=True, null=True)

    def save(self, *args, **kwargs):
        
        try:
            getattr(TaskStatuses, str(self.status))
        except AttributeError:
            raise Exception('Invalid status "{}"'.format(self.status))

        # Call parent save
        super(Task, self).save(*args, **kwargs)

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


    def __str__(self):
        return str('Task "{}" of user "{}" running on "{}" in status "{}" created at "{}"'.format(self.name, self.user, self.computing, self.status, self.created))



#=========================
#  Keys 
#=========================

class Keys(models.Model):

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name='+', on_delete=models.CASCADE, null=False)  

    private_key_file = models.CharField('Private key file', max_length=4096, blank=False, null=False)
    public_key_file  = models.CharField('Public key file', max_length=4096, blank=False, null=False)

    default = models.BooleanField('Default keys?', default=False)


    def __str__(self):
        return str('Keys with id "{}" of user "{}"'.format(self.id, self.user))


    @property
    def id(self):
        return str(self.uuid).split('-')[0]









