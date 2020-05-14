import os
import uuid
import json
import subprocess
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.models import User
from django.shortcuts import redirect
from .models import Profile, LoginToken, Task, TaskStatuses, Container, Computing, KeyPair, ComputingSysConf, ComputingUserConf
from .utils import send_email, format_exception, timezonize, os_shell, booleanize, debug_param, get_tunnel_host, random_username
from .decorators import public_view, private_view
from .exceptions import ErrorMessage

# Setup logging
import logging
logger = logging.getLogger(__name__)

# Conf
SUPPORTED_CONTAINER_TYPES = ['docker', 'singularity']
SUPPORTED_REGISTRIES = ['docker_local', 'docker_hub', 'singularity_hub']
UNSUPPORTED_TYPES_VS_REGISTRIES = ['docker:singularity_hub']

# Task cache
_task_cache = {}


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
def register_view(request):

    data = {}
    data['title'] = "{} - Register".format(settings.DJANGO_PROJECT_NAME)

    # If authenticated user reloads the main URL
    if request.method == 'GET' and request.user.is_authenticated:
        return HttpResponseRedirect('/main/')

    # If unauthenticated register if post
    if request.method == 'POST':
        if not request.user.is_authenticated:
            email    = request.POST.get('email')
            password = request.POST.get('password')
            invitation = request.POST.get('invitation')
            
            if invitation != os.environ.get('INVITATION_CODE', 'Rosetta'):
                raise ErrorMessage('Wrong invitation code')

            if '@' not in email:
                raise ErrorMessage('Detected invalid email address')
            
            # Register the user
            user = User.objects.create_user(random_username(), password=password, email=email)

            # Is this necessary?
            user.save()
            
            data['user'] = user

            # Create profile
            logger.debug('Creating user profile for user "{}"'.format(user.email))
            Profile.objects.create(user=user)

            # Generate user keys
            out = os_shell('mkdir -p /data/resources/keys/', capture=True)
            if not out.exit_code == 0:
                logger.error(out)
                raise ErrorMessage('Something went wrong in creating user keys folder. Please contact support')
                
            command= "/bin/bash -c \"ssh-keygen -q -t rsa -N '' -f /data/resources/keys/{}_id_rsa 2>/dev/null <<< y >/dev/null\"".format(user.username)                        
            out = os_shell(command, capture=True)
            if not out.exit_code == 0:
                logger.error(out)
                raise ErrorMessage('Something went wrong in creating user keys. Please contact support')
                
            
            # Create key objects
            KeyPair.objects.create(user = user,
                                default = True,
                                private_key_file = '/data/resources/keys/{}_id_rsa'.format(user.username),
                                public_key_file = '/data/resources/keys/{}_id_rsa.pub'.format(user.username))
            

            # Manually set the auth backend for the user
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            
            data['status'] = 'activated'

    # All other cases, render the login page again with no other data than title
    return render(request, 'register.html', {'data': data})




@public_view
def entrypoint(request):
    return HttpResponseRedirect('/main/')

@public_view
def main_view(request):

    # Set data & render
    data = {}
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

    # Set data.default_public_key
    with open(KeyPair.objects.get(user=request.user, default=True).public_key_file) as f:
        data['default_public_key'] = f.read()

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
    fromlist = request.GET.get('fromlist', False)
    details = booleanize(request.GET.get('details', None))
    

    # Do we have to operate on a specific task?
    if uuid:

        try:
            
            # Get the task (raises if none available including no permission)
            try:
                task = Task.objects.get(user=request.user, uuid=uuid)
            except Task.DoesNotExist:
                raise ErrorMessage('Task does not exists or no access rights')
            data['task'] = task
    
            # Attach user config to computing
            task.computing.attach_user_conf_data(task.user)
    
            #----------------
            #  Task actions
            #----------------

            if action=='delete':
                if task.status not in [TaskStatuses.stopped, TaskStatuses.exited]:
                    try:
                        task.computing.manager.stop_task(task)
                    except:
                        pass
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
                task.computing.manager.stop_task(task)

            elif action=='connect':

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
                        logger.error('Cannot find a free port for the tunnel for task "{}"'.format(task))
                        raise ErrorMessage('Cannot find a free port for the tunnel to the task')

                    task.tunnel_port = tunnel_port
                    task.save()


                # Check if the tunnel is active and if not create it
                logger.debug('Checking if task "{}" has a running tunnel'.format(task))

                out = os_shell('ps -ef | grep ":{}:{}:{}" | grep -v grep'.format(task.tunnel_port, task.ip, task.port), capture=True)

                if out.exit_code == 0:
                    logger.debug('Task "{}" has a running tunnel, using it'.format(task))
                else:
                    logger.debug('Task "{}" has no running tunnel, creating it'.format(task))

                    # Tunnel command
                    if task.computing.type == 'remotehop':           
                                  
                        # Get computing params
                        first_host = task.computing.get_conf_param('first_host')
                        first_user = task.computing.get_conf_param('first_user')
                        #second_host = task.computing.get_conf_param('second_host')
                        #second_user = task.computing.get_conf_param('second_user')
                        #setup_command = task.computing.get_conf_param('setup_command')
                        #base_port = task.computing.get_conf_param('base_port')
                                        
                        tunnel_command= 'ssh -4 -o StrictHostKeyChecking=no -nNT -L 0.0.0.0:{}:{}:{} {}@{} & '.format(task.tunnel_port, task.ip, task.port, first_user, first_host)
                    
                    else:
                        tunnel_command= 'ssh -4 -o StrictHostKeyChecking=no -nNT -L 0.0.0.0:{}:{}:{} localhost & '.format(task.tunnel_port, task.ip, task.port)
                    
                    background_tunnel_command = 'nohup {} >/dev/null 2>&1 &'.format(tunnel_command)

                    # Log
                    logger.debug('Opening tunnel with command: {}'.format(background_tunnel_command))

                    # Execute
                    subprocess.Popen(background_tunnel_command, shell=True)

                # Ok, now redirect to the task through the tunnel
                tunnel_host = get_tunnel_host()
                return redirect('http://{}:{}'.format(tunnel_host,task.tunnel_port))

        except Exception as e:
            data['error'] = 'Error in getting the task or performing the required action'
            logger.error('Error in getting the task with uuid="{}" or performing the required action: "{}"'.format(uuid, e))
            return render(request, 'error.html', {'data': data})

        # Ok, redirect if there was an action
        if action:
            if fromlist:
                return redirect('/tasks')
            else:
                if not task.uuid:
                    # it has just been deleted
                    return redirect('/tasks')
                else:
                    return redirect('/tasks/?uuid={}'.format(task.uuid))


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

    # Step if any
    step = request.POST.get('step', None)

    # Container uuid if any
    container_uuid = request.GET.get('task_container_uuid', None)
    if container_uuid:
        try:
            data['task_container'] = Container.objects.get(uuid=container_uuid, user=request.user)
        except Container.DoesNotExist:
            data['task_container'] = Container.objects.get(uuid=container_uuid, user=None)
    else:
        # Get containers
        data['containers'] = list(Container.objects.filter(user=None)) + list(Container.objects.filter(user=request.user))
    
    # Get computings 
    data['computings'] = list(Computing.objects.filter(user=None)) + list(Computing.objects.filter(user=request.user))


    # Handle step
    if step:

        # Task name
        task_name = request.POST.get('task_name', None)
        if not task_name:
            raise ErrorMessage('Missing task name')
        data['task_name'] = task_name

        # Task container
        task_container_uuid = request.POST.get('task_container_uuid', None)
        try:
            task_container = Container.objects.get(uuid=task_container_uuid, user=None)
        except Container.DoesNotExist:
            try:
                task_container =  Container.objects.get(uuid=task_container_uuid, user=request.user)
            except Container.DoesNotExist:
                raise Exception('Consistency error, container with uuid "{}" does not exists or user "{}" does not have access rights'.format(task_container_uuid, request.user.email))
        data['task_container'] = task_container

        # Task computing
        task_computing_uuid = request.POST.get('task_computing_uuid', None)
        try:
            task_computing = Computing.objects.get(uuid=task_computing_uuid, user=None)
        except Computing.DoesNotExist:
            try:
                task_computing =  Computing.objects.get(uuid=task_computing_uuid, user=request.user)
            except Computing.DoesNotExist:
                raise Exception('Consistency error, computing with uuid "{}" does not exists or user "{}" does not have access rights'.format(task_computing_uuid, request.user.email))
        data['task_computing'] = task_computing
            
        # Handle step one/two
        if step == 'one':
    
            # Set step and task uuid
            data['step'] = 'two'
            
        elif step == 'two':

            # Generate the task uuid
            task_uuid = str(uuid.uuid4())

            # Create the task object
            task = Task(uuid      = task_uuid,
                        user      = request.user,
                        name      = task_name,
                        status    = TaskStatuses.created,
                        container = task_container,
                        computing = task_computing)

            # Add auth
            task.auth_user     = request.POST.get('auth_user', None)
            task.auth_pass     = request.POST.get('auth_password', None)
            task.access_method = request.POST.get('access_method', None)
            task_base_port     = request.POST.get('task_base_port', None)
            
            if task_base_port:
                task.port = task_base_port
            
            # Checks
            if task.auth_pass and len(task.auth_pass) < 6:
                raise ErrorMessage('Task password must be at least 6 chars') 
            
            # Computing options # TODO: This is hardcoded thinking about Slurm and Singularity
            computing_cpus = request.POST.get('computing_cpus', None)
            computing_memory = request.POST.get('computing_memory', None)
            computing_partition = request.POST.get('computing_partition', None)
            extra_volumes = request.POST.get('extra_volumes', None)
            
            computing_options = {}
            if computing_cpus:
                try:
                    int(computing_cpus)
                except:
                    raise Exception('Cannot convert computing_cpus to int')
                computing_options['cpus'] = int(computing_cpus)
    
            if computing_memory:
                computing_options['memory'] = computing_memory
    
            if computing_partition:
                computing_options['partition'] = computing_partition        
            
            if computing_options:
                task.computing_options = computing_options
                        
            # Attach user config to computing
            task.computing.attach_user_conf_data(task.user)

            # Set port if not dynamic ports
            if not task.container.supports_dynamic_ports:
                if task.container.ports:
                    task.port = task.container.port
        
            # Set exttra volumes if any:
            task.extra_volumes = extra_volumes

            # Save the task before starting it, or the computing manager will not be able to work properly
            task.save()
    
            # Start the task
            try:
                task.computing.manager.start_task(task)
            except:
                # Delete the task if could not start it
                task.delete()
                
                # ..and re-raise
                raise

            # Set step        
            data['step'] = 'created'

    else:
        
        # Set step
        data['step'] = 'one'

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

    # Attach user conf in any
    task.computing.attach_user_conf_data(request.user) 

    # Get the log
    try:

        data['log'] = task.computing.manager.get_task_log(task)

    except Exception as e:
        data['error'] = 'Error in viewing task log'
        logger.error('Error in viewing task log with uuid="{}": "{}"'.format(uuid, e))
        raise

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
    uuid   = request.GET.get('uuid', None)
    action = request.GET.get('action', None)

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

    # Get containers
    data['containers'] = list(Container.objects.filter(user=None)) + list(Container.objects.filter(user=request.user))

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

        # Container name
        container_name = request.POST.get('container_name', None)

        # Container service ports. TODO: support multiple ports? 
        container_ports = request.POST.get('container_ports', None)
        
        if container_ports:       
            try:
                for container_service_port in container_ports.split(','):
                    int(container_service_port)
            except:
                raise ErrorMessage('Invalid container port(s) in "{}"'.format(container_ports))


        # Capabilities
        container_supports_dynamic_ports = request.POST.get('container_supports_dynamic_ports', None)
        if container_supports_dynamic_ports and container_supports_dynamic_ports == 'True':
            container_supports_dynamic_ports = True
        else:
            container_supports_dynamic_ports = False

        container_supports_user_auth = request.POST.get('container_supports_user_auth', None)
        if container_supports_user_auth and container_supports_user_auth == 'True':
            container_supports_user_auth = True
        else:
            container_supports_user_auth = False

        container_supports_pass_auth = request.POST.get('container_supports_pass_auth', None)
        if container_supports_pass_auth and container_supports_pass_auth == 'True':
            container_supports_pass_auth = True
        else:
            container_supports_pass_auth = False

        # Log
        logger.debug('Creating new container object with image="{}", type="{}", registry="{}", ports="{}"'.format(container_image, container_type, container_registry, container_ports))

        # Create
        Container.objects.create(user     = request.user,
                                 image    = container_image,
                                 name     = container_name,
                                 type     = container_type,
                                 registry = container_registry,
                                 ports    = container_ports,
                                 supports_dynamic_ports = container_supports_dynamic_ports,
                                 supports_user_auth     = container_supports_user_auth,
                                 supports_pass_auth     = container_supports_pass_auth,
                                 )
        # Set added switch
        data['added'] = True

    return render(request, 'add_container.html', {'data': data})



#=========================
#  Computings view
#=========================

@private_view
def computings(request):

    # Init data
    data={}
    data['user']    = request.user
    data['profile'] = Profile.objects.get(user=request.user)
    data['title']   = 'Computing resources'
    data['name']    = request.POST.get('name',None)

    # Get action/details if any
    uuid    = request.GET.get('uuid', None)
    action  = request.GET.get('action', None)
    details = booleanize(request.GET.get('details', None))
    computing_uuid = request.GET.get('uuid', None)
    data['details'] = details
    data['action'] = action
    
    if details and computing_uuid:
        try:
            data['computing'] = Computing.objects.get(uuid=computing_uuid, user=request.user)
        except Computing.DoesNotExist:
            data['computing'] = Computing.objects.get(uuid=computing_uuid, user=None)

        # Attach user conf in any
        data['computing'].attach_user_conf_data(request.user)
            
    
    else:
        data['computings'] = list(Computing.objects.filter(user=None)) + list(Computing.objects.filter(user=request.user))
        
        # Attach user conf in any
        for computing in data['computings']:
            computing.attach_user_conf_data(request.user)

    return render(request, 'computings.html', {'data': data})


#=========================
#  Add Computing view
#=========================

@private_view
def add_computing(request):

    # Init data
    data={}
    data['user']    = request.user
    data['profile'] = Profile.objects.get(user=request.user)
    data['title']   = 'Add computing'
    data['name']    = request.POST.get('name',None)


    return render(request, 'add_computing.html', {'data': data})



#=========================
# Edit Computing conf view
#=========================

@private_view
def edit_computing_conf(request):

    # Init data
    data={}
    data['user']    = request.user
    data['profile'] = Profile.objects.get(user=request.user)
    data['title']   = 'Add computing'

    # Get computing conf type
    computing_conf_type = request.GET.get('type', request.POST.get('type', None))
    if not computing_conf_type:
        raise Exception('Missing type')
    
    # Get computing uuid
    computing_uuid = request.GET.get('computing_uuid', request.POST.get('computing_uuid', None))
    if not computing_uuid:
        raise Exception('Missing computing_uuid')

    new_conf = request.POST.get('new_conf', None)


    if computing_conf_type == 'sys':
        
        data['type'] = 'sys'
        
        if not request.user.is_superuser:
            raise Exception('Cannot edit sys conf as not superuser')
    
        # Get computing
        try:
            computing = Computing.objects.get(uuid=computing_uuid)
            data['computing'] = computing
        except ComputingSysConf.DoesNotExist:
            raise Exception('Unknown computing "{}"'.format(computing_uuid))
        
        # Get computing conf
        computingSysConf, _ = ComputingSysConf.objects.get_or_create(computing=computing)   
        
        # Edit conf?
        if new_conf:
            new_conf_data = json.loads(new_conf)
            logger.debug('Setting new conf data for sys conf "{}": "{}"'.format(computingSysConf.uuid, new_conf_data))
            computingSysConf.data = new_conf_data
            computingSysConf.save()
            data['saved'] = True
            return HttpResponseRedirect('/computings')


        # Dump conf data for the webpage
        if computingSysConf.data:
            data['computing_conf_data'] = computingSysConf.data
            data['computing_conf_data_json'] = json.dumps(computingSysConf.data)
    
    elif computing_conf_type == 'user':

        data['type'] = 'user'
        
        # Get computing
        try:
            computing = Computing.objects.get(uuid=computing_uuid)
            data['computing'] = computing
        except ComputingUserConf.DoesNotExist:
            raise Exception('Unknown computing "{}"'.format(computing_uuid))

        # Get computing conf
        computingUserConf, _ = ComputingUserConf.objects.get_or_create(computing=computing, user=request.user)

        # Edit conf?
        if new_conf:
            new_conf_data = json.loads(new_conf)
            logger.debug('Setting new conf data for user conf "{}": "{}"'.format(computingUserConf.uuid, new_conf_data))
            computingUserConf.data = new_conf_data
            computingUserConf.save()
            data['saved'] = True
            return HttpResponseRedirect('/computings')
        
        # Dump conf data for the webpage
        if computingUserConf.data:
            data['computing_conf_data'] = computingUserConf.data
            data['computing_conf_data_json'] = json.dumps(computingUserConf.data)

           
    else:
        raise Exception('Unknown computing conf type "{}"'.format(computing_conf_type))
    

    return render(request, 'edit_computing_conf.html', {'data': data})




























