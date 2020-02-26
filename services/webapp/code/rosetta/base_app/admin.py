from django.contrib import admin

from .models import Profile, LoginToken, Task, Container

admin.site.register(Profile)
admin.site.register(LoginToken)
admin.site.register(Task)
admin.site.register(Container)
