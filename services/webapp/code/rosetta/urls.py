"""rosetta URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf.urls import url
import logging

logger = logging.getLogger(__name__)

# Base App
from rosetta.core_app import api as core_app_api
from rosetta.core_app import views as core_app_views

# REST Framework & Swagger
from rest_framework import routers
from rest_framework.documentation import include_docs_urls
from rest_framework_swagger.views import get_swagger_view

core_app_api_router = routers.DefaultRouter()
core_app_api_router.register(r'users', core_app_api.UserViewSet)

urlpatterns = [
               
    # Webpages
    url(r'^$', core_app_views.entrypoint),
    path('main/', core_app_views.main_view),
    path('login/', core_app_views.login_view),
    path('logout/', core_app_views.logout_view),
    url(r'^register/$', core_app_views.register_view),
    url(r'^account/$', core_app_views.account),
    url(r'^tasks/$', core_app_views.tasks),
    url(r'^create_task/$', core_app_views.create_task),
    url(r'^task_log/$', core_app_views.task_log),
    url(r'^computings/$', core_app_views.computings),
    url(r'^add_computing/$', core_app_views.add_computing),
    url(r'^edit_computing_conf/$', core_app_views.edit_computing_conf),
    url(r'^containers/$', core_app_views.containers),
    url(r'^add_container/$', core_app_views.add_container),

    # Modules
    path('admin/', admin.site.urls),
    path('api/v1/doc/', get_swagger_view(title="Swagger Documentation")),
    
    # ViewSet APIs
    path('api/v1/base/login/', core_app_api.login_api.as_view(), name='login_api'),
    path('api/v1/base/logout/', core_app_api.logout_api.as_view(), name='logout_api'),

    # Custom APIs
    path('api/v1/base/agent/', core_app_api.agent_api.as_view(), name='agent_api'),
 
]

# This message here is quite useful when developing in autoreload mode
logger.info('Loaded URLs')

