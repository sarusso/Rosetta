
# Python imports
import time
import uuid
import inspect
import json
import socket
import os
import subprocess

# Django imports
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash

# Project imports
from .models import Profile, LoginToken, Task, TaskStatuses, Container
from .utils import send_email, format_exception, random_username, log_user_activity, timezonize, os_shell, booleanize

# Setup logging
import logging
logger = logging.getLogger(__name__)

# Custom exceptions
from .exceptions import ErrorMessage, ConsistencyException

# Conf
SUPPORTED_CONTAINER_TYPES = ['docker', 'singularity']
SUPPORTED_REGISTRIES = ['docker_local', 'docker_hub', 'singularity_hub']
UNSUPPORTED_TYPES_VS_REGISTRIES = ['docker:singularity_hub']

TASK_DATA_DIR = "/data"

#=========================
#  Decorators
#=========================

# Public view
def public_view(wrapped_view):
    def public_view_wrapper(request, *argv, **kwargs):
        # -------------- START Public/private common code --------------
        try:
            log_user_activity("DEBUG", "Called", request, wrapped_view.__name__)

            # Try to get the templates from view kwargs
            # Todo: Python3 compatibility: https://stackoverflow.com/questions/2677185/how-can-i-read-a-functions-signature-including-default-argument-values

            argSpec=inspect.getargspec(wrapped_view)

            if 'template' in argSpec.args:
                template = argSpec.defaults[0]
            else:
                template = None

            # Call wrapped view
            data = wrapped_view(request, *argv, **kwargs)

            if not isinstance(data, HttpResponse):
                if template:
                    #logger.debug('using template + data ("{}","{}")'.format(template,data))
                    return render(request, template, {'data': data})
                else:
                    raise ConsistencyException('Got plain "data" output but no template defined in view')
            else:
                #logger.debug('using returned httpresponse')
                return data

        except Exception as e:
            if isinstance(e, ErrorMessage):
                error_text = str(e)
            else:

                # Raise te exception if we are in debug mode
                if settings.DEBUG:
                    raise

                # Otherwise,
                else:

                    # first log the exception
                    logger.error(format_exception(e))

                    # and then mask it.
                    error_text = 'something went wrong'

            data = {'user': request.user,
                    'title': 'Error',
                    'error' : 'Error: "{}"'.format(error_text)}

            if template:
                return render(request, template, {'data': data})
            else:
                return render(request, 'error.html', {'data': data})
        # --------------  END Public/private common code --------------
    return public_view_wrapper

# Private view
def private_view(wrapped_view):
    def private_view_wrapper(request, *argv, **kwargs):
        if request.user.is_authenticated:
            # -------------- START Public/private common code --------------
            log_user_activity("DEBUG", "Called", request, wrapped_view.__name__)
            try:

                # Try to get the templates from view kwargs
                # Todo: Python3 compatibility: https://stackoverflow.com/questions/2677185/how-can-i-read-a-functions-signature-including-default-argument-values

                argSpec=inspect.getargspec(wrapped_view)

                if 'template' in argSpec.args:
                    template = argSpec.defaults[0]
                else:
                    template = None

                # Call wrapped view
                data = wrapped_view(request, *argv, **kwargs)

                if not isinstance(data, HttpResponse):
                    if template:
                        #logger.debug('using template + data ("{}","{}")'.format(template,data))
                        return render(request, template, {'data': data})
                    else:
                        raise ConsistencyException('Got plain "data" output but no template defined in view')
                else:
                    #logger.debug('using returned httpresponse')
                    return data

            except Exception as e:
                if isinstance(e, ErrorMessage):
                    error_text = str(e)
                else:

                    # Raise te exception if we are in debug mode
                    if settings.DEBUG:
                        raise

                    # Otherwise,
                    else:

                        # first log the exception
                        logger.error(format_exception(e))

                        # and then mask it.
                        error_text = 'something went wrong'

                data = {'user': request.user,
                        'title': 'Error',
                        'error' : 'Error: "{}"'.format(error_text)}

                if template:
                    return render(request, template, {'data': data})
                else:
                    return render(request, 'error.html', {'data': data})
            # --------------  END  Public/private common code --------------

        else:
            log_user_activity("DEBUG", "Redirecting to login since not authenticated", request)
            return HttpResponseRedirect('/login')
    return private_view_wrapper




@public_view
def login_view(request):

    data = {}
    data['title'] = "{} - Login".format(settings.DJANGO_PROJECT_NAME)

    # If authenticated user reloads the main URL
    if request.method == 'GET' and request.user.is_authenticated:
        return HttpResponseRedirect('/main/')

    # If unauthenticated user tries to log in
    if request.method == 'POST':
        if not request.user.is_authenticated:
            username = request.POST.get('username')
            password = request.POST.get('password')
            # Use Django's machinery to attempt to see if the username/password
            # combination is valid - a User object is returned if it is.

            if "@" in username:
                # Get the username from the email
                try:
                    user = User.objects.get(email=username)
                    username = user.username
                except User.DoesNotExist:
                    if password:
                        raise ErrorMessage('Check email and password')
                    else:
                        # Return here, we don't want to give any hints about existing users
                        data['success'] = 'Ok, if we have your data you will receive a login link by email shortly.'
                        return render(request, 'success.html', {'data': data})

            if password:
                user = authenticate(username=username, password=password)
                if user:
                    login(request, user)
                    return HttpResponseRedirect('/main')
                else:
                    raise ErrorMessage('Check email and password')
            else:

                # If empty password, send mail with login token
                logger.debug('Sending login token via mail to {}'.format(user.email))

                token = uuid.uuid4()

                # Create token or update if existent (and never used)
                try:
                    loginToken = LoginToken.objects.get(user=user)
                except LoginToken.DoesNotExist:
                    LoginToken.objects.create(user=user, token=token)
                else:
                    loginToken.token = token
                    loginToken.save()
                try:
                    send_email(to=user.email, subject='{} login link'.format(settings.DJANGO_PROJECT_NAME), text='Hello,\n\nhere is your login link: {}/login/?token={}\n\nOnce logged in, you can go to "My Account" and change password (or just keep using the login link feature).\n\nThe {} Team.'.format(settings.DJANGO_PUBLIC_HTTP_HOST, token, settings.DJANGO_PROJECT_NAME))
                except Exception as e:
                    logger.error(format_exception(e))
                    raise ErrorMessage('Something went wrong. Please retry later.')

                # Return here, we don't want to give any hints about existing users
                data['success'] = 'Ok, if we have your data you will receive a login link by email shortly.'
                return render(request, 'success.html', {'data': data})


        else:
            # This should never happen.
            # User tried to log-in while already logged in: log him out and then render the login
            logout(request)

    else:
        # If we are logging in through a token
        token = request.GET.get('token', None)

        if token:

            loginTokens = LoginToken.objects.filter(token=token)

            if not loginTokens:
                raise ErrorMessage('Token not valid or expired')


            if len(loginTokens) > 1:
                raise Exception('Consistency error: more than one user with the same login token ({})'.format(len(loginTokens)))

            # Use the first and only token (todo: use the objects.get and correctly handle its exceptions)
            loginToken = loginTokens[0]

            # Get the user from the table
            user = loginToken.user

            # Set auth backend
            user.backend = 'django.contrib.auth.backends.ModelBackend'

            # Ok, log in the user
            login(request, user)
            loginToken.delete()

            # Now redirect to site
            return HttpResponseRedirect('/main/')


    # All other cases, render the login page again with no other data than title
    return render(request, 'login.html', {'data': data})


@private_view
def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')

@public_view
def entrypoint(request):
    return HttpResponseRedirect('/main/')

@public_view
def main_view(request):

    # Get action
    action = request.POST.get('action', None)

    # Set data
    data = {}
    data['action'] = action
    return render(request, 'main.html', {'data': data})


#====================
# Account view
#====================

@private_view
def account(request):

    data={}
    data['user'] = request.user
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    data['profile'] = profile
    data['title'] = "{} - Account".format(settings.DJANGO_PROJECT_NAME)

    # Set values from POST and GET
    edit = request.POST.get('edit', None)
    if not edit:
        edit = request.GET.get('edit', None)
        data['edit'] = edit
    value = request.POST.get('value', None)

    # Fix None
    if value and value.upper() == 'NONE':
        value = None
    if edit and edit.upper() == 'NONE':
        edit = None

    # Edit values
    if edit and value:
        try:
            logger.info('Setting "{}" to "{}"'.format(edit,value))

            # Timezone
            if edit=='timezone' and value:
                # Validate
                timezonize(value)
                profile.timezone = value
                profile.save()

            # Email
            elif edit=='email' and value:
                request.user.email=value
                request.user.save()

            # Password
            elif edit=='password' and value:
                request.user.set_password(value)
                request.user.save()

            # API key
            elif edit=='apikey' and value:
                profile.apikey=value
                profile.save()

            # Plan
            elif edit=='plan' and value:
                profile.plan=value
                profile.save()

            # Generic property
            elif edit and value:
                raise Exception('Attribute to change is not valid')


        except Exception as e:
            logger.error(format_exception(e))
            data['error'] = 'The property "{}" does not exists or the value "{}" is not valid.'.format(edit, value)
            return render(request, 'error.html', {'data': data})

    return render(request, 'account.html', {'data': data})




#=========================
#  Tasks view
#=========================

@private_view
def tasks(request):

    # Init data
    data={}
    data['user']  = request.user
    data['profile'] = Profile.objects.get(user=request.user)
    data['title'] = 'Tasks'

    # Get action if any
    action  = request.GET.get('action', None)
    uuid    = request.GET.get('uuid', None)
    details = booleanize(request.GET.get('details', None))
    
    # Setting var
    standby_supported = False

    # Do we have to operate on a specific task?
    if uuid:

        try:
            
            # Get the task (raises if none available including no permission)
            try:
                task = Task.objects.get(user=request.user, uuid=uuid)
            except Task.DoesNotExist:
                raise ErrorMessage('Task does not exists or no access rights')
            data['task'] = task
    
            #----------------
            #  Task actions
            #----------------

            if action=='delete':
                if task.status not in [TaskStatuses.stopped, TaskStatuses.exited]:
                    data['error'] = 'Can delete only tasks in the stopped state'
                    return render(request, 'error.html', {'data': data})
                try:
                    # Get the task (raises if none available including no permission)
                    task = Task.objects.get(user=request.user, uuid=uuid)
    
                    # Delete
                    task.delete()
                    
                    # Unset task
                    data['task'] = None    
    
                except Exception as e:
                    data['error'] = 'Error in deleting the task'
                    logger.error('Error in deleting task with uuid="{}": "{}"'.format(uuid, e))
                    return render(request, 'error.html', {'data': data})
    
            elif action=='stop': # or delete,a and if delete also remove object
                try:
                    if task.compute == 'local':
     
                        # Delete the Docker container
                        if standby_supported:
                            stop_command = 'sudo docker stop {}'.format(task.tid)
                        else:
                            stop_command = 'sudo docker stop {} && sudo docker rm {}'.format(task.tid,task.tid)
     
                        out = os_shell(stop_command, capture=True)
                        if out.exit_code != 0:
                            raise Exception(out.stderr)
     
                    elif task.compute == 'demoremote':
     
                        # Stop the task remotely
                        stop_command = 'ssh -4 -o StrictHostKeyChecking=no slurmclusterworker-one  "kill -9 {}"'.format(task.pid)
                        logger.debug(stop_command)
                        out = os_shell(stop_command, capture=True)
                        if out.exit_code != 0:
                            if not 'No such process' in out.stderr:
                                raise Exception(out.stderr)
     
                    else:
                        data['error']= 'Don\'t know how to stop tasks on "{}" compute resource.'.format(task.compute)
                        return render(request, 'error.html', {'data': data})
     
                    # Ok, save status as deleted
                    task.status = 'stopped'
                    task.save()
     
                    # Check if the tunnel is active and if so kill it
                    logger.debug('Checking if task "{}" has a running tunnel'.format(task.tid))
                    check_command = 'ps -ef | grep ":'+str(task.tunnel_port)+':'+str(task.ip)+':'+str(task.port)+'" | grep -v grep | awk \'{print $2}\''
                    logger.debug(check_command)
                    out = os_shell(check_command, capture=True)
                    logger.debug(out)
                    if out.exit_code == 0:
                        logger.debug('Task "{}" has a running tunnel, killing it'.format(task.tid))
                        tunnel_pid = out.stdout
                        # Kill Tunnel command
                        kill_tunnel_command= 'kill -9 {}'.format(tunnel_pid)
     
                        # Log
                        logger.debug('Killing tunnel with command: {}'.format(kill_tunnel_command))
     
                        # Execute
                        os_shell(kill_tunnel_command, capture=True)
                        if out.exit_code != 0:
                            raise Exception(out.stderr)
    
                except Exception as e:
                    data['error'] = 'Error in stopping the task'
                    logger.error('Error in stopping task with uuid="{}": "{}"'.format(uuid, e))
                    return render(request, 'error.html', {'data': data})
    
            elif action=='connect':
    
                # Create task tunnel
                if task.compute in ['local', 'demoremote']:
    
                    # If there is no tunnel port allocated yet, find one
                    if not task.tunnel_port:
    
                        # Get a free port fot the tunnel:
                        allocated_tunnel_ports = []
                        for other_task in Task.objects.all():
                            if other_task.tunnel_port and not other_task.status in [TaskStatuses.exited, TaskStatuses.stopped]:
                                allocated_tunnel_ports.append(other_task.tunnel_port)
    
                        for port in range(7000, 7006):
                            if not port in allocated_tunnel_ports:
                                tunnel_port = port
                                break
                        if not tunnel_port:
                            logger.error('Cannot find a free port for the tunnel for task "{}"'.format(task.tid))
                            raise ErrorMessage('Cannot find a free port for the tunnel to the task')
    
                        task.tunnel_port = tunnel_port
                        task.save()
    
    
                    # Check if the tunnel is active and if not create it
                    logger.debug('Checking if task "{}" has a running tunnel'.format(task.tid))
    
                    out = os_shell('ps -ef | grep ":{}:{}:{}" | grep -v grep'.format(task.tunnel_port, task.ip, task.port), capture=True)
    
                    if out.exit_code == 0:
                        logger.debug('Task "{}" has a running tunnel, using it'.format(task.tid))
                    else:
                        logger.debug('Task "{}" has no running tunnel, creating it'.format(task.tid))
    
                        # Tunnel command
                        tunnel_command= 'ssh -4 -o StrictHostKeyChecking=no -nNT -L 0.0.0.0:{}:{}:{} localhost & '.format(task.tunnel_port, task.ip, task.port)
                        background_tunnel_command = 'nohup {} >/dev/null 2>&1 &'.format(tunnel_command)
    
                        # Log
                        logger.debug('Opening tunnel with command: {}'.format(background_tunnel_command))
    
                        # Execute
                        subprocess.Popen(background_tunnel_command, shell=True)
    
                else:
                    raise ErrorMessage('Connecting to tasks on compute "{}" is not supported yet'.format(task.compute))
    
                # Ok, now redirect to the task through the tunnel
                from django.shortcuts import redirect
                return redirect('http://localhost:{}'.format(task.tunnel_port))

        except Exception as e:
            data['error'] = 'Error in getting the task or performing the required action'
            logger.error('Error in getting the task with uuid="{}" or performing the required action: "{}"'.format(uuid, e))
            return render(request, 'error.html', {'data': data})


    # Do we have to list all the tasks?
    if not uuid or (uuid and not details):

        #----------------
        #  Task list
        #----------------
    
        # Get all tasks
        try:
            tasks = Task.objects.filter(user=request.user).order_by('created') 
        except Exception as e:
            data['error'] = 'Error in getting Tasks info'
            logger.error('Error in getting Virtual Devices: "{}"'.format(e))
            return render(request, 'error.html', {'data': data})
    
        # Update task statuses
        for task in tasks:
            task.update_status()
    
        # Set task and tasks variables
        data['task']  = None   
        data['tasks'] = tasks

    return render(request, 'tasks.html', {'data': data})


#=========================
#  Create Task view
#=========================

@private_view
def create_task(request):

    # Init data
    data={}
    data['user']    = request.user
    data['profile'] = Profile.objects.get(user=request.user)
    data['title']   = 'New Task'

    # Get containers configured on the platform, both private to this user and public
    data['user_containers'] = Container.objects.filter(user=request.user)
    data['platform_containers'] = Container.objects.filter(user=None)

    # Task name if any
    task_name = request.POST.get('task_name', None)

    if task_name:

        # Task container
        task_container_uuid = request.POST.get('task_container_uuid', None)

        # Get the container object, first try as public and then as private
        try:
            task_container = Container.objects.get(uuid=task_container_uuid, user=None)
        except Container.DoesNotExist:
            try:
                task_container =  Container.objects.get(uuid=task_container_uuid, user=request.user)
            except Container.DoesNotExist:
                raise Exception('Consistency error, container with uuid "{}" does not exists or user "{}" does not have access rights'.format(task_container_uuid, request.user.email))

        # Compute
        task_compute = request.POST.get('task_compute', None)
        if task_compute not in ['local', 'demoremote']:
            raise ErrorMessage('Unknown compute resource "{}')

        # Generate the task uuid
        str_uuid = str(uuid.uuid4())
        str_shortuuid = str_uuid.split('-')[0]

        # Create the task object
        task = Task.objects.create(uuid      = str_uuid,
                                   user      = request.user,
                                   name      = task_name,
                                   status    = TaskStatuses.created,
                                   container = task_container,
                                   compute   = task_compute)


        # Actually start tasks
        try:
            if task_compute == 'local':

                # Get our ip address
                #import netifaces
                #netifaces.ifaddresses('eth0')
                #backend_ip = netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']

                # Init run command #--cap-add=NET_ADMIN --cap-add=NET_RAW
                run_command  = 'sudo docker run  --network=rosetta_default --name rosetta-task-{}'.format( str_shortuuid)

                # Data volume
                run_command += ' -v {}/task-{}:/data'.format(TASK_DATA_DIR, str_shortuuid)

                # Set registry string
                if task.container.registry == 'local':
                    registry_string = 'localhost:5000/'
                else:
                    registry_string  = ''

                # Host name, image entry command
                run_command += ' -h task-{} -d -t {}{}'.format(str_shortuuid, registry_string, task.container.image)

                # Run the task Debug
                logger.debug('Running new task with command="{}"'.format(run_command))
                out = os_shell(run_command, capture=True)
                if out.exit_code != 0:
                    raise Exception(out.stderr)
                else:
                    task_tid = out.stdout
                    logger.debug('Created task with id: "{}"'.format(task_tid))


                    # Get task IP address
                    out = os_shell('sudo docker inspect --format \'{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}\' ' + task_tid + ' | tail -n1', capture=True)
                    if out.exit_code != 0:
                        raise Exception('Error: ' + out.stderr)
                    task_ip = out.stdout

                    # Set fields
                    task.tid    = task_tid
                    task.status = TaskStatuses.running
                    task.ip     = task_ip
                    task.port   = int(task.container.service_ports.split(',')[0])

                    # Save
                    task.save()

            elif task_compute == 'demoremote':
                logger.debug('Using Demo Remote as compute resource')


                # 1) Run the singularity container on slurmclusterworker-one (non blocking)
                run_command = 'ssh -4 -o StrictHostKeyChecking=no slurmclusterworker-one  "export SINGULARITY_NOHTTPS=true && exec nohup singularity run --pid --writable-tmpfs --containall --cleanenv docker://dregistry:5000/rosetta/metadesktop &> /tmp/{}.log & echo \$!"'.format(task.uuid)
                out = os_shell(run_command, capture=True)
                if out.exit_code != 0:
                    raise Exception(out.stderr)

                # Save pid echoed by the command above
                task_pid = out.stdout

                # 2) Simulate the agent (i.e. report container IP and port port)

                # Get task IP address
                out = os_shell('sudo docker inspect --format \'{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}\' slurmclusterworker-one | tail -n1', capture=True)
                if out.exit_code != 0:
                    raise Exception('Error: ' + out.stderr)
                task_ip = out.stdout

                # Set fields
                task.tid    = task.uuid
                task.status = TaskStatuses.running
                task.ip     = task_ip
                task.pid    = task_pid
                task.port   = int(task.container.service_ports.split(',')[0])

                # Save
                task.save()


            else:
                raise Exception('Consistency exception: invalid compute resource "{}'.format(task_compute))

        except Exception as e:
            data['error'] = 'Error in creating new Task.'
            logger.error(e)
            return render(request, 'error.html', {'data': data})

        # Set created switch
        data['created'] = True

    return render(request, 'create_task.html', {'data': data})


#=========================
#  Task log
#=========================

@private_view
def task_log(request):

    # Init data
    data={}
    data['user']  = request.user
    data['profile'] = Profile.objects.get(user=request.user)
    data['title'] = 'Tasks'

    # Get uuid and refresh if any
    uuid    = request.GET.get('uuid', None)
    refresh = request.GET.get('refresh', None)

    if not uuid:
        return render(request, 'error.html', {'data': 'uuid not set'})

    # Get the task (raises if none available including no permission)
    task = Task.objects.get(user=request.user, uuid=uuid)

    # Set back task and refresh
    data['task']    = task 
    data['refresh'] = refresh

    # Get the log
    try:

        if task.compute == 'local':

            # View the Docker container log (attach)
            view_log_command = 'sudo docker logs {}'.format(task.tid,)
            logger.debug(view_log_command)
            out = os_shell(view_log_command, capture=True)
            if out.exit_code != 0:
                raise Exception(out.stderr)
            else:
                data['log'] = out.stdout

        elif task.compute == 'demoremote':

            # View the Singularity container log
            view_log_command = 'ssh -4 -o StrictHostKeyChecking=no slurmclusterworker-one  "cat /tmp/{}.log"'.format(task.uuid)
            logger.debug(view_log_command)
            out = os_shell(view_log_command, capture=True)
            if out.exit_code != 0:
                raise Exception(out.stderr)
            else:
                data['log'] = out.stdout

        else:
            data['error']= 'Don\'t know how to view task logs on "{}" compute resource.'.format(task.compute)
            return render(request, 'error.html', {'data': data})

    except Exception as e:
        data['error'] = 'Error in viewing task log'
        logger.error('Error in viewing task log with uuid="{}": "{}"'.format(uuid, e))
        return render(request, 'error.html', {'data': data})

    return render(request, 'task_log.html', {'data': data})





#=========================
#  Containers
#=========================

@private_view
def containers(request):

    # Init data
    data={}
    data['user']    = request.user
    data['profile'] = Profile.objects.get(user=request.user)

    # Get action if any
    action = request.GET.get('action', None)
    uuid   = request.GET.get('uuid', None)

    # Do we have to operate on a specific container?
    if uuid:

        try:

            # Get the container (raises if none available including no permission)
            try:
                container = Container.objects.get(uuid=uuid)
            except Container.DoesNotExist:
                raise ErrorMessage('Container does not exists or no access rights')                
            if container.user and container.user != request.user:
                raise ErrorMessage('Container does not exists or no access rights')
            data['container'] = container

            #-------------------
            # Container actions
            #-------------------

            if action and action=='delete':

                # Delete
                container.delete()

        except Exception as e:
            data['error'] = 'Error in getting the container or performing the required action'
            logger.error('Error in getting the container with uuid="{}" or performing the required action: "{}"'.format(uuid, e))
            return render(request, 'error.html', {'data': data})

    #----------------
    # Container list
    #----------------

    # Get containers configured on the platform, both private to this user and public
    data['user_containers'] = Container.objects.filter(user=request.user)
    data['platform_containers'] = Container.objects.filter(user=None)

    return render(request, 'containers.html', {'data': data})



#=========================
#  Add Container view
#=========================

@private_view
def add_container(request):

    # Init data
    data={}
    data['user']    = request.user
    data['profile'] = Profile.objects.get(user=request.user)
    data['title']   = 'Add container'

    # Container image if any
    container_image = request.POST.get('container_image',None)

    if container_image:

        # Container type
        container_type = request.POST.get('container_type', None)
        if not container_type:
            raise ErrorMessage('No container type given')
        if not container_type in SUPPORTED_CONTAINER_TYPES:
            raise ErrorMessage('No valid container type, got "{}"'.format(container_type))

        # Container registry
        container_registry = request.POST.get('container_registry', None)
        if not container_registry:
            raise ErrorMessage('No registry type given')
        if not container_registry in SUPPORTED_REGISTRIES:
            raise ErrorMessage('No valid container registry, got "{}"'.format(container_registry))

        # Check container type vs container registry compatibility
        if container_type+':'+container_registry in UNSUPPORTED_TYPES_VS_REGISTRIES:
            raise ErrorMessage('Sorry, container type "{}" is not compatible with registry type "{}"'.format(container_type, container_registry))

        # Container service ports
        container_service_ports = request.POST.get('container_service_ports', None)

        try:
            for container_service_port in container_service_ports:
                int(container_service_port)
        except:
            raise ErrorMessage('Invalid service port "{}"'.format(container_service_port))

        # Log
        logger.debug('Creating new container object with image="{}", type="{}", registry="{}", service_ports="{}"'.format(container_image, container_type, container_registry, container_service_ports))

        # Create
        Container.objects.create(user          = request.user,
                                 image         = container_image,
                                 type          = container_type,
                                 registry      = container_registry,
                                 service_ports = container_service_ports)
        # Set added switch
        data['added'] = True

    return render(request, 'add_container.html', {'data': data})



#=========================
#  Computes view
#=========================

@private_view
def computes(request):

    # Init data
    data={}
    data['user']    = request.user
    data['profile'] = Profile.objects.get(user=request.user)
    data['title']   = 'Add compute'
    data['name']    = request.POST.get('name',None)


    return render(request,  'computes.html', {'data': data})

#=========================
#  Add Compute view
#=========================

@private_view
def add_compute(request):

    # Init data
    data={}
    data['user']    = request.user
    data['profile'] = Profile.objects.get(user=request.user)
    data['title']   = 'Add compute'
    data['name']    = request.POST.get('name',None)


    return render(request, 'add_compute.html', {'data': data})
