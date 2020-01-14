from django.contrib import admin

from .models import Profile, LoginToken, Task

admin.site.register(Profile)
admin.site.register(LoginToken)
admin.site.register(Task)
