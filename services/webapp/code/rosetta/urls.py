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
from rosetta.base_app import api as base_app_api
from rosetta.base_app import views as base_app_views

# REST Framework & Swagger
from rest_framework import routers
from rest_framework.documentation import include_docs_urls
from rest_framework_swagger.views import get_swagger_view

base_app_api_router = routers.DefaultRouter()
base_app_api_router.register(r'users', base_app_api.UserViewSet)

urlpatterns = [
               
    # Webpages
    url(r'^$', base_app_views.entrypoint),
    path('main/', base_app_views.main_view),
    path('login/', base_app_views.login_view),
    path('logout/', base_app_views.logout_view),
    url(r'^account/$', base_app_views.account),
    url(r'^tasks/$', base_app_views.tasks),
    url(r'^create_task/$', base_app_views.create_task),
    url(r'^task_log/$', base_app_views.task_log),
    url(r'^computings/$', base_app_views.computings),
    url(r'^add_computing/$', base_app_views.add_computing),
    url(r'^containers/$', base_app_views.containers),
    url(r'^add_container/$', base_app_views.add_container),

    # Modules
    path('admin/', admin.site.urls),
    path('api/v1/doc/', get_swagger_view(title="Swagger Documentation")),
    
    # ViewSet APIs
    path('api/v1/base/login/', base_app_api.login_api.as_view(), name='login_api'),
    path('api/v1/base/logout/', base_app_api.logout_api.as_view(), name='logout_api'),

    # Custom APIs
    path('api/v1/base/agent/', base_app_api.agent_api.as_view(), name='agent_api'),
 
]

# This message here is quite useful when developing in autoreload mode
logger.info('Loaded URLs')

