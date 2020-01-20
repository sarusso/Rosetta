
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
from .models import Profile, LoginToken, Task, TaskStatuses
from .utils import send_email, format_exception, random_username, log_user_activity, timezonize, os_shell

# Setup logging
import logging
logger = logging.getLogger(__name__)

# Custom exceptions
from .exceptions import ErrorMessage, ConsistencyException

# Conf
SUPPORTED_TASK_TYPES = ['metadesktop', 'astrocook', 'gadgetviewer']
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
    action = request.GET.get('action', None)
    uuid = request.GET.get('uuid', None)

    # Setting var
    standby_supported = False

    # Perform actions if required:
    if action and uuid:

        # Get the task (raises if none available including no permission)
        task = Task.objects.get(user=request.user, uuid=uuid)

        if action=='delete':
            if task.status not in [TaskStatuses.stopped, TaskStatuses.exited]:
                data['error'] = 'Can delete only tasks in the stopped state'
                return render(request, 'error.html', {'data': data})  
            try:
                # Get the task (raises if none available including no permission)
                task = Task.objects.get(user=request.user, uuid=uuid)
                
                # Delete
                task.delete()

                # Unset uuid to load the list again
                uuid = None

            except Exception as e:
                data['error'] = 'Error in deleting the task'
                logger.error('Error in deleting task with uuid="{}": "{}"'.format(uuid, e))
                return render(request, 'error.html', {'data': data})  
        
        elif action=='stop': # or delete,a and if delete also remove object
            try:

                if task.compute == 'local':
                    str_shortuuid = task.uuid.split('-')[0]
    
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

            # Unset uuid to load the list again
            uuid = None
            
        elif action=='connect':
            
            # Get the task (raises if none available including no permission)
            task = Task.objects.get(user=request.user, uuid=uuid)
            
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

    # Get all task(s)
    if uuid:
        try:
            tasks = [Task.objects.get(user=request.user, uuid=uuid)]
        except Exception as e:
            data['error'] = 'Error in getting info for Task "{}"'.format(uuid)
            logger.error('Error in getting Virtual Device with uuid="{}": "{}"'.format(uuid, e))
            return render(request, 'error.html', {'data': data})   
    else:
        try:
            tasks = Task.objects.filter(user=request.user).order_by('created')
        except Exception as e:
            data['error'] = 'Error in getting Virtual Devices info'
            logger.error('Error in getting Virtual Devices: "{}"'.format(e))
            return render(request, 'error.html', {'data': data})   

    # Update task statuses
    for task in tasks:
        task.update_status()

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
    data['name']    = request.POST.get('name',None)
    
    if data['name']:
        
        # Type
        data['container'] = request.POST.get('container', None)
        if not data['container']:
            data['error'] = 'No container given'
            return render(request, 'error.html', {'data': data})

        if not data['container'] in SUPPORTED_TASK_TYPES:
            data['error'] = 'No valid task container'
            return render(request, 'error.html', {'data': data})
        
        compute = request.POST.get('compute', None)

        logger.debug(compute)

        if compute not in ['local', 'demoremote']:
            data['error'] = 'Unknown compute resource "{}'.format(compute)
            return render(request, 'error.html', {'data': data})
        
        # Generate the task uuid
        str_uuid = str(uuid.uuid4())
        str_shortuuid = str_uuid.split('-')[0]
        
        # Create the task object
        task = Task.objects.create(uuid      = str_uuid,
                                   user      = request.user,
                                   name      = data['name'],
                                   status    = TaskStatuses.created,
                                   container = data['container'],
                                   compute   = compute)
        
        # Actually start tasks
        try:
            if compute == 'local':            

                # Get our ip address             
                #import netifaces
                #netifaces.ifaddresses('eth0')
                #backend_ip = netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']       
    
                # Init run command #--cap-add=NET_ADMIN --cap-add=NET_RAW 
                run_command  = 'sudo docker run  --network=rosetta_default --name rosetta-task-{}'.format( str_shortuuid)
    
                # Data volume
                run_command += ' -v {}/task-{}:/data'.format(TASK_DATA_DIR, str_shortuuid)
    
                # Host name, image entry command
                task_container = 'task-{}'.format(data['container'])
                run_command += ' -h task-{} -d -t localhost:5000/rosetta/metadesktop'.format(str_shortuuid, task_container)
    
                # Create the model
                task = Task.objects.create(user=request.user, name=data['name'], status=TaskStatuses.created, container=data['container'])
                    
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
                    task.port   = 8590
                
                    # Save
                    task.save()

            elif compute == 'demoremote':
                logger.debug('Using Demo Remote as compute resource')


                # 1) Run the singularity container on slurmclusterworker-one (non blocking)
                run_command = 'ssh -4 -o StrictHostKeyChecking=no slurmclusterworker-one  "export SINGULARITY_NOHTTPS=true && exec nohup singularity run --pid --writable-tmpfs --containall --cleanenv docker://dregistry:5000/rosetta/metadesktop &> /dev/null & echo \$!"'
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
                task.port   = 8590
                
                # Save
                task.save()
                

            else:
                raise Exception('Consistency exception: invalid compute resource "{}'.format(compute))

        except Exception as e:
            data['error'] = 'Error in creating new Task.'
            logger.error(e)
            return render(request, 'error.html', {'data': data})
    

    return render(request, 'create_task.html', {'data': data})







