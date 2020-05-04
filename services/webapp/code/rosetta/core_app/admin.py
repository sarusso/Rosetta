from django.contrib import admin

from .models import Profile, LoginToken, Task, Container, Computing, ComputingSysConf, ComputingUserConf, Keys

admin.site.register(Profile)
admin.site.register(LoginToken)
admin.site.register(Task)
admin.site.register(Container)
admin.site.register(Computing)
admin.site.register(ComputingSysConf)
admin.site.register(ComputingUserConf)
admin.site.register(Keys)
