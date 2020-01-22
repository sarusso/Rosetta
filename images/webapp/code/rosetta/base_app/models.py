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
    user  = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.CharField('Login token', max_length=36)


#=========================
#  Tasks 
#=========================
class Task(models.Model):
    user      = models.ForeignKey(User, related_name='+', on_delete=models.CASCADE)
    tid       = models.CharField('Task ID', max_length=64, blank=False, null=False)
    uuid      = models.CharField('Task UUID', max_length=36, blank=False, null=False)
    name      = models.CharField('Task name', max_length=36, blank=False, null=False)
    status    = models.CharField('Task status', max_length=36, blank=True, null=True)
    created   = models.DateTimeField('Created on', default=timezone.now)
    compute   = models.CharField('Task compute', max_length=36, blank=True, null=True)
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
        if self.compute == 'local':
            
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
    def short_uuid(self):
        return self.uuid.split('-')[0]


#=========================
#  Containers
#=========================
class Container(models.Model):

    #uuid           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user           = models.ForeignKey(User, related_name='+', on_delete=models.CASCADE, null=True)
    # If a container has no user, it will be available to anyone. Can be created, edited and deleted only by admins.
    image         = models.CharField('Container image', max_length=255, blank=False, null=False)
    type          = models.CharField('Container type', max_length=36, blank=False, null=False)
    registry      = models.CharField('Container registry', max_length=255, blank=False, null=False)
    service_ports = models.CharField('Container service ports', max_length=36, blank=True, null=True)
    #private       = models.BooleanField('Container is private and needs auth to be pulled from the registry')

    def __str__(self):
        return str('Container of type "{}" with image "{}" from registry "{}" of user "{}"'.format(self.type, self.image, self.registry, self.user))


