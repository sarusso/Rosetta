import uuid
import enum

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from .utils import os_shell

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
    
    image         = models.CharField('Container image', max_length=255, blank=False, null=False)
    type          = models.CharField('Container type', max_length=36, blank=False, null=False)
    registry      = models.CharField('Container registry', max_length=255, blank=False, null=False)
    service_ports = models.CharField('Container service ports', max_length=36, blank=True, null=True)
    #private       = models.BooleanField('Container is private and needs auth to be pulled from the registry')

    def __str__(self):
        return str('Container of type "{}" with image "{}" from registry "{}" of user "{}"'.format(self.type, self.image, self.registry, self.user))

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
    
    name  = models.CharField('Computing Name', max_length=255, blank=False, null=False)

    def __str__(self):
        return str('Computing Resource "{}" of user "{}"'.format(self.name, self.user))

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
    computing = models.ForeignKey(Computing, related_name='+', on_delete=models.CASCADE)
    pid       = models.IntegerField('Task pid', blank=True, null=True)
    port      = models.IntegerField('Task port', blank=True, null=True)
    ip        = models.CharField('Task ip address', max_length=36, blank=True, null=True)
    tunnel_port = models.IntegerField('Task tunnel port', blank=True, null=True)

    # Links
    container    = models.ForeignKey('Container', on_delete=models.CASCADE, related_name='+')

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




