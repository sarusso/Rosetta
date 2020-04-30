from .models import TaskStatuses, Keys, Task
from .utils import os_shell
from .exceptions import ErrorMessage, ConsistencyException

# Setup logging
import logging
logger = logging.getLogger(__name__)

# Conf
TASK_DATA_DIR = "/data"


class ComputingManager(object):
    
    def start_task(self, task, **kwargs):
        
        # Check for run task logic implementation
        try:
            self._start_task
        except AttributeError:
            raise NotImplementedError('Not implemented')
        
        # Call actual run task logic
        self._start_task(task, **kwargs)


    def stop_task(self, task, **kwargs):
        
        # Check for stop task logic implementation
        try:
            self._stop_task
        except AttributeError:
            raise NotImplementedError('Not implemented')
        
        # Call actual stop task logic
        self._stop_task(task, **kwargs)
        
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


    def get_task_log(self, task, **kwargs):
        
        # Check for get task log logic implementation
        try:
            self._get_task_log
        except AttributeError:
            raise NotImplementedError('Not implemented')
        
        # Call actual get task log logic
        return self._get_task_log(task, **kwargs)


class LocalComputingManager(ComputingManager):
    
    def _start_task(self, task):

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

        # Debug
        logger.debug('Running new task with command="{}"'.format(run_command))
        
        # Run the task 
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


    def _stop_task(self, task):

        # Delete the Docker container
        standby_supported = False
        if standby_supported:
            stop_command = 'sudo docker stop {}'.format(task.tid)
        else:
            stop_command = 'sudo docker stop {} && sudo docker rm {}'.format(task.tid,task.tid)
    
        out = os_shell(stop_command, capture=True)
        if out.exit_code != 0:
            raise Exception(out.stderr)
    
    def _get_task_log(self, task, **kwargs):

        # View the Docker container log (attach)
        view_log_command = 'sudo docker logs {}'.format(task.tid,)
        logger.debug(view_log_command)
        out = os_shell(view_log_command, capture=True)
        if out.exit_code != 0:
            raise Exception(out.stderr)
        else:
            return out.stdout


class RemoteComputingManager(ComputingManager):
    
    def _start_task(self, task, **kwargs):
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

            task.tid    = task.uuid
            task.save()

            # Set pass if any
            if task.auth_pass:
                authstring = ' export SINGULARITYENV_AUTH_PASS={} && '.format(task.auth_pass)
            else:
                authstring = ''

            import socket
            hostname = socket.gethostname()
            webapp_ip = socket.gethostbyname(hostname)

            run_command  = 'ssh -i {} -4 -o StrictHostKeyChecking=no {} '.format(user_keys.private_key_file, host)
            run_command+= '"wget {}:8080/api/v1/base/agent/?task_uuid={} -O /tmp/agent_{}.py &> /dev/null && export TASK_PORT=\$(python /tmp/agent_{}.py 2> /tmp/{}.log) && '.format(webapp_ip, task.uuid, task.uuid, task.uuid, task.uuid)
            run_command += 'export SINGULARITY_NOHTTPS=true && export SINGULARITYENV_TASK_PORT=\$TASK_PORT && {} '.format(authstring)
            run_command += 'exec nohup singularity run --pid --writable-tmpfs --containall --cleanenv '
            
            # ssh -i /rosetta/.ssh/id_rsa -4 -o StrictHostKeyChecking=no slurmclusterworker-one
            # "wget 172.21.0.2:8080/api/v1/base/agent/?task_uuid=15a4320a-88b6-4ffc-8dd0-c80f9d18b292 -O /tmp/agent_15a4320a-88b6-4ffc-8dd0-c80f9d18b292.py &> /dev/null &&
            # export TASK_PORT=\$(python /tmp/agent_15a4320a-88b6-4ffc-8dd0-c80f9d18b292.py) && export SINGULARITY_NOHTTPS=true && export SINGULARITYENV_TASK_PORT=\$TASK_PORT &&  export SINGULARITYENV_AUTH_PASS=testpass &&  
            # exec nohup singularity run --pid --writable-tmpfs --containall --cleanenv
            # docker://dregistry:5000/rosetta/metadesktop &> /tmp/15a4320a-88b6-4ffc-8dd0-c80f9d18b292.log & echo $!"
            
            
            # Set registry
            if task.container.registry == 'docker_local':
                registry = 'docker://dregistry:5000/'
            elif task.container.registry == 'docker_hub':
                registry = 'docker://'
            else:
                raise NotImplementedError('Registry {} not supported'.format(task.container.registry))
    
            run_command+='{}{} &>> /tmp/{}.log & echo \$!"'.format(registry, task.container.image, task.uuid)
            
        else:
            raise NotImplementedError('Container {} not supported'.format(task.container.type))

        out = os_shell(run_command, capture=True)
        if out.exit_code != 0:
            raise Exception(out.stderr)
        
        # Log        
        logger.debug('Shell exec output: "{}"'.format(out))

        # Load back the task to avoid  concurrency problems in the agent call
        task_uuid = task.uuid
        task = Task.objects.get(uuid=task_uuid)

        # Save pid echoed by the command above
        task_pid = out.stdout

        # Set fields

        #task.status = TaskStatuses.sumbitted
        task.pid    = task_pid
 
        # Save
        task.save()


    def _stop_task(self, task, **kwargs):

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


    def _get_task_log(self, task, **kwargs):
        # Get computing host
        host = task.computing.get_conf_param('host')

        # Get id_rsa
        if task.computing.require_user_keys:
            user_keys = Keys.objects.get(user=task.user, default=True)
            id_rsa_file = user_keys.private_key_file
        else:
            raise NotImplementedError('temote with no keys not yet')

        # View the Singularity container log
        view_log_command = 'ssh -i {} -4 -o StrictHostKeyChecking=no {}  "cat /tmp/{}.log"'.format(id_rsa_file, host, task.uuid)
        logger.debug(view_log_command)
        out = os_shell(view_log_command, capture=True)
        if out.exit_code != 0:
            raise Exception(out.stderr)
        else:
            return out.stdout



class SlurmComputingManager(ComputingManager):
    
    def _start_task(self, task, **kwargs):
        logger.debug('Starting a remote task "{}"'.format(task.computing))

        # Get computing host #Key Error ATM
        host = 'slurmclustermaster-main' #task.computing.get_conf_param('host')

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
            webapp_ip = socket.gethostbyname(hostname)

            run_command = 'ssh -i {} -4 -o StrictHostKeyChecking=no {} '.format(user_keys.private_key_file, host)

            run_command += '"echo \\"#!/bin/bash\nwget {}:8080/api/v1/base/agent/?task_uuid={} -O /tmp/agent_{}.py &> /dev/null && export TASK_PORT=\\\\\\$(python /tmp/agent_{}.py 2> /tmp/{}.log) && '.format(webapp_ip, task.uuid, task.uuid, task.uuid, task.uuid)
            run_command += 'export SINGULARITY_NOHTTPS=true && export SINGULARITYENV_TASK_PORT=\\\\\\$TASK_PORT && {} '.format(authstring)
            run_command += 'exec nohup singularity run --pid --writable-tmpfs --containall --cleanenv '


            # Double to escape for python six for shell (double times three as \\\ escapes a single slash in shell)

            # ssh -i /rosetta/.ssh/id_rsa -4 -o StrictHostKeyChecking=no slurmclustermaster-main "echo \"wget 172.18.0.5:8080/api/v1/base/agent/?task_uuid=558c65c3-8b72-4d6b-8119-e1dcf6f81177 -O /tmp/agent_558c65c3-8b72-4d6b-8119-e1dcf6f81177.py &> /dev/null
            #  && export TASK_PORT=\\\$(python /tmp/agent_558c65c3-8b72-4d6b-8119-e1dcf6f81177.py 2> /tmp/558c65c3-8b72-4d6b-8119-e1dcf6f81177.log) && export SINGULARITY_NOHTTPS=true && export SINGULARITYENV_TASK_PORT=\\\$TASK_PORT &&  export SINGULARITYENV_AUTH_PASS=testpass 
            #  && exec nohup singularity run --pid --writable-tmpfs --containall --cleanenv docker://dregistry:5000/rosetta/metadesktop &> /tmp/558c65c3-8b72-4d6b-8119-e1dcf6f81177.log\" > /tmp/558c65c3-8b72-4d6b-8119-e1dcf6f81177.sh"

            
            # Set registry
            if task.container.registry == 'docker_local':
                registry = 'docker://dregistry:5000/'
            elif task.container.registry == 'docker_hub':
                registry = 'docker://'
            else:
                raise NotImplementedError('Registry {} not supported'.format(task.container.registry))
    
            run_command+='{}{} &> /tmp/{}.log\\" > /tmp/{}.sh && sbatch -p partition1 /tmp/{}.sh"'.format(registry, task.container.image, task.uuid, task.uuid, task.uuid)

            
        else:
            raise NotImplementedError('Container {} not supported'.format(task.container.type))

        out = os_shell(run_command, capture=True)
        if out.exit_code != 0:
            raise Exception(out.stderr)


    def _stop_task(self, task, **kwargs):
        raise NotImplementedError('Not implemented')


    def _get_task_log(self, task, **kwargs):
        raise NotImplementedError('Not implemented')









