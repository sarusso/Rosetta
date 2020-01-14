import uuid

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from .utils import os_shell

# Setup logging
import logging
logger = logging.getLogger(__name__)


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
    user     = models.ForeignKey(User, related_name='+', on_delete=models.CASCADE)
    tid      = models.CharField('Task ID', max_length=64, blank=False, null=False)
    uuid     = models.CharField('Task UUID', max_length=36, blank=False, null=False)
    name     = models.CharField('Task name', max_length=36, blank=False, null=False)
    type     = models.CharField('Task type', max_length=36, blank=False, null=False)
    status   = models.CharField('Task status', max_length=36, blank=True, null=True)
    created  = models.DateTimeField('Created on', default=timezone.now)
    compute  = models.CharField('Task compute', max_length=36, blank=True, null=True)

    tunneled    = models.BooleanField('Task tunneled', default=False)
    tunnel_port = models.IntegerField('Task tunnel port', blank=True, null=True)


    def __str__(self):
        return str('Task "{}" of user "{}" in status "{}" (TID "{}")'.format(self.name, self.user.email, self.status, self.tid))

    @property
    def ip_addr(self):
        # TODO: if self.computing (or self.type) == "local":
        out = os_shell('sudo docker inspect --format \'{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}\' ' + self.tid + ' | tail -n1', capture=True)
        if out.exit_code != 0:
            raise Exception('Error: ' + out.stderr)
        return out.stdout
        







