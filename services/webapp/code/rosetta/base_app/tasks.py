from .models import TaskStatuses, Keys
from .utils import os_shell
from .exceptions import ErrorMessage, ConsistencyException

# Setup logging
import logging
logger = logging.getLogger(__name__)

# Conf
TASK_DATA_DIR = "/data"


def start_task(task):

    # Handle proper config
    if task.computing.type == 'local':

        # Get our ip address
        #import netifaces
        #netifaces.ifaddresses('eth0')
        #backend_ip = netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']

        # Init run command #--cap-add=NET_ADMIN --cap-add=NET_RAW
        run_command  = 'sudo docker run  --network=rosetta_default --name rosetta-task-{}'.format( task.id)

        # Pass if any
        if task.auth_pass:
            run_command += ' -eAUTH_PASS={} '.format(task.auth_pass)

        # Data volume
        run_command += ' -v {}/task-{}:/data'.format(TASK_DATA_DIR, task.id)

        # Set registry string
        if task.container.registry == 'local':
            registry_string = 'localhost:5000/'
        else:
            registry_string  = ''

        # Host name, image entry command
        run_command += ' -h task-{} -d -t {}{}'.format(task.id, registry_string, task.container.image)

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




    elif task.computing.type == 'remote':
        logger.debug('Starting a remote task "{}"'.format(task.computing))

        # Get computing host
        host = task.computing.get_conf_param('host')

        # Get user keys
        if task.computing.require_user_keys:
            user_keys = Keys.objects.get(user=task.user, default=True)
        else:
            raise NotImplementedError('Remote tasks not requiring keys are not yet supported')

        # 1) Run the container on the host (non blocking)
 
        if task.container.type == 'singularity':

            

            # Set pass if any
            if task.auth_pass:
                authstring = ' export SINGULARITYENV_AUTH_PASS={} && '.format(task.auth_pass)
            else:
                authstring = ''

            import socket
            hostname = socket.gethostname()
            my_ip = socket.gethostbyname(hostname)

            run_command  = 'ssh -i {} -4 -o StrictHostKeyChecking=no {} '.format(user_keys.private_key_file, host)
            run_command+= '"wget {}:8080/api/v1/base/agent/?task_uuid={} -O /tmp/agent_{}.py && TASK_PORT=$(python /tmp/agent_{}.py) && '.format(my_ip, task.uuid, task.uuid, task.uuid)
            run_command += 'export SINGULARITY_NOHTTPS=true && export SINGULARITYENV_TASK_PORT=$TASK_PORT && {} '.format(authstring)
            run_command += 'exec nohup singularity run --pid --writable-tmpfs --containall --cleanenv '
            
            # Set registry
            if task.container.registry == 'docker_local':
                registry = 'docker://dregistry:5000/'
            elif task.container.registry == 'docker_hub':
                registry = 'docker://'
            else:
                raise NotImplementedError('Registry {} not supported'.format(task.container.registry))
    
            run_command+='{}{} &> /tmp/{}.log & echo \$!"'.format(registry, task.container.image, task.uuid)
            logger.critical(run_command)
            
        else:
            raise NotImplementedError('Container {} not supported'.format(task.container.type))

        out = os_shell(run_command, capture=True)
        if out.exit_code != 0:
            raise Exception(out.stderr)
        
        logger.critical(out.stdout)
        logger.critical(out.stderr)

 
        # Save pid echoed by the command above
        task_pid = out.stdout

        # Set fields
        task.tid    = task.uuid
        #task.status = TaskStatuses.sumbitted
        task.pid    = task_pid
 
        # Save
        task.save()

    elif task.computing.type == 'remoteOLD':
        logger.debug('Starting a remote task "{}"'.format(task.computing))

        # Get computing host
        host = task.computing.get_conf_param('host')

        # Get user keys
        if task.computing.require_user_keys:
            user_keys = Keys.objects.get(user=task.user, default=True)
        else:
            raise NotImplementedError('Remote tasks not requiring keys are not yet supported')

        # 1) Run the container on the host (non blocking)
 
        if task.container.type == 'singularity':

            # Set pass if any
            if task.auth_pass:
                authstring = ' export SINGULARITYENV_AUTH_PASS={} && '.format(task.auth_pass)
            else:
                authstring = ''

            run_command  = 'ssh -i {} -4 -o StrictHostKeyChecking=no {} '.format(user_keys.private_key_file, host)
            run_command += '"export SINGULARITY_NOHTTPS=true && {} '.format(authstring)
            run_command += 'exec nohup singularity run --pid --writable-tmpfs --containall --cleanenv '
            
            # Set registry
            if task.container.registry == 'docker_local':
                registry = 'docker://dregistry:5000/'
            elif task.container.registry == 'docker_hub':
                registry = 'docker://'
            else:
                raise NotImplementedError('Registry {} not supported'.format(task.container.registry))
    
            run_command+='{}{} &> /tmp/{}.log & echo \$!"'.format(registry, task.container.image, task.uuid)
            
        else:
            raise NotImplementedError('Container {} not supported'.format(task.container.type))

        out = os_shell(run_command, capture=True)
        if out.exit_code != 0:
            raise Exception(out.stderr)
 
        # Save pid echoed by the command above
        task_pid = out.stdout

        # 2) Simulate the agent (i.e. report container IP and port port)
 
        # Get task IP address
        out = os_shell('sudo docker inspect --format \'{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}\' '+host+' | tail -n1', capture=True)
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
        raise Exception('Consistency exception: invalid computing resource "{}'.format(task.computing))


def stop_task(task):

    if task.computing.type == 'local':
    
        # Delete the Docker container
        standby_supported = False
        if standby_supported:
            stop_command = 'sudo docker stop {}'.format(task.tid)
        else:
            stop_command = 'sudo docker stop {} && sudo docker rm {}'.format(task.tid,task.tid)
    
        out = os_shell(stop_command, capture=True)
        if out.exit_code != 0:
            raise Exception(out.stderr)
    
    elif task.computing.type == 'remote':

        # Get user keys
        if task.computing.require_user_keys:
            user_keys = Keys.objects.get(user=task.user, default=True)
        else:
            raise NotImplementedError('Remote tasks not requiring keys are not yet supported')

        # Get computing host
        host = task.computing.get_conf_param('host')

        # Stop the task remotely
        stop_command = 'ssh -i {} -4 -o StrictHostKeyChecking=no {} "kill -9 {}"'.format(user_keys.private_key_file, host, task.pid)
        logger.debug(stop_command)
        out = os_shell(stop_command, capture=True)
        if out.exit_code != 0:
            if not 'No such process' in out.stderr:
                raise Exception(out.stderr)
    else:
        raise Exception('Don\'t know how to stop tasks on "{}" computing resource.'.format(task.computing))
    
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
