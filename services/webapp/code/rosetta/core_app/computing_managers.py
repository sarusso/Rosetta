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
            task.port   = int(task.container.default_ports.split(',')[0])

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
 
        # Set task as stopped
        task.status = TaskStatuses.stopped
        task.save()

    
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
        user = task.computing.get_conf_param('user')

        # Get user keys
        if task.computing.require_user_keys:
            user_keys = Keys.objects.get(user=task.user, default=True)
        else:
            raise NotImplementedError('Remote tasks not requiring keys are not yet supported')

        # Get webapp conn string
        from.utils import get_webapp_conn_string
        webapp_conn_string = get_webapp_conn_string()
            

        # 1) Run the container on the host (non blocking)
 
        if task.container.type == 'singularity':

            task.tid    = task.uuid
            task.save()

            # Set pass if any
            if task.auth_pass:
                authstring = ' export SINGULARITYENV_AUTH_PASS={} && '.format(task.auth_pass)
            else:
                authstring = ''

            run_command  = 'ssh -i {} -4 -o StrictHostKeyChecking=no {}@{} '.format(user_keys.private_key_file, user, host)
            run_command += '/bin/bash -c \'"wget {}/api/v1/base/agent/?task_uuid={} -O /tmp/agent_{}.py &> /dev/null && export BASE_PORT=\$(python /tmp/agent_{}.py 2> /tmp/{}.log) && '.format(webapp_conn_string, task.uuid, task.uuid, task.uuid, task.uuid)
            run_command += 'export SINGULARITY_NOHTTPS=true && export SINGULARITYENV_BASE_PORT=\$BASE_PORT && {} '.format(authstring)
            run_command += 'exec nohup singularity run --pid --writable-tmpfs --containall --cleanenv '
            
            # ssh -i /rosetta/.ssh/id_rsa -4 -o StrictHostKeyChecking=no slurmclusterworker-one
            # "wget 172.21.0.2:8080/api/v1/base/agent/?task_uuid=15a4320a-88b6-4ffc-8dd0-c80f9d18b292 -O /tmp/agent_15a4320a-88b6-4ffc-8dd0-c80f9d18b292.py &> /dev/null &&
            # export BASE_PORT=\$(python /tmp/agent_15a4320a-88b6-4ffc-8dd0-c80f9d18b292.py) && export SINGULARITY_NOHTTPS=true && export SINGULARITYENV_BASE_PORT=\$BASE_PORT &&  export SINGULARITYENV_AUTH_PASS=testpass &&  
            # exec nohup singularity run --pid --writable-tmpfs --containall --cleanenv
            # docker://dregistry:5000/rosetta/metadesktop &> /tmp/15a4320a-88b6-4ffc-8dd0-c80f9d18b292.log & echo $!"
            
            
            # Set registry
            if task.container.registry == 'docker_local':
                registry = 'docker://dregistry:5000/'
            elif task.container.registry == 'docker_hub':
                registry = 'docker://'
            else:
                raise NotImplementedError('Registry {} not supported'.format(task.container.registry))
    
            run_command+='{}{} &>> /tmp/{}.log & echo \$!"\''.format(registry, task.container.image, task.uuid)
            
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
        #task.status = TaskStatuses.running
        task.pid = task_pid
 
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
        user = task.computing.get_conf_param('user')

        # Stop the task remotely
        stop_command = 'ssh -i {} -4 -o StrictHostKeyChecking=no {}@{} \'/bin/bash -c "kill -9 {}"\''.format(user_keys.private_key_file, user, host, task.pid)
        logger.debug(stop_command)
        out = os_shell(stop_command, capture=True)
        if out.exit_code != 0:
            if not 'No such process' in out.stderr:
                raise Exception(out.stderr)

        # Set task as stopped
        task.status = TaskStatuses.stopped
        task.save()


    def _get_task_log(self, task, **kwargs):
        
        # Get user keys
        if task.computing.require_user_keys:
            user_keys = Keys.objects.get(user=task.user, default=True)
        else:
            raise NotImplementedError('Remote tasks not requiring keys are not yet supported')

        # Get computing host
        host = task.computing.get_conf_param('master')
        user = task.computing.get_conf_param('user')

        # Stop the task remotely
        view_log_command = 'ssh -i {} -4 -o StrictHostKeyChecking=no {}@{} \'/bin/bash -c "cat /tmp/{}.log"\''.format(user_keys.private_key_file, user, host, task.uuid)

        out = os_shell(view_log_command, capture=True)
        if out.exit_code != 0:
            raise Exception(out.stderr)
        else:
            return out.stdout



class SlurmComputingManager(ComputingManager):
    
    def _start_task(self, task, **kwargs):
        logger.debug('Starting a remote task "{}"'.format(task.computing))

        # Get computing host #Key Error ATM
        host = task.computing.get_conf_param('master')
        user = task.computing.get_conf_param('user')
        
        # Get user keys
        if task.computing.require_user_keys:
            user_keys = Keys.objects.get(user=task.user, default=True)
        else:
            raise NotImplementedError('Remote tasks not requiring keys are not yet supported')

        # Get webapp conn string
        from.utils import get_webapp_conn_string
        webapp_conn_string = get_webapp_conn_string()
            
        # Get task computing parameters and set sbatch args
        sbatch_args = ''
        if task.computing_options:
            task_partition = task.computing_options.get('partition', None)
            task_cpus = task.computing_options.get('cpus', None)
            task_memory = task.computing_options.get('memory', None)

            # Set sbatch args
            sbatch_args = ''
            if task_partition:
                sbatch_args += '-p {} '.format(task_partition)
            #if task_cpus:
            #    sbatch_args += '-c {} '.format()
            #if task_memory:
            #    sbatch_args += '-m {} '.format()
        
        # Set output and error files
        sbatch_args += ' --output=\$HOME/{}.log --error=\$HOME/{}.log '.format(task.uuid, task.uuid)


        # 1) Run the container on the host (non blocking)
        if task.container.type == 'singularity':

            if not task.container.supports_dynamic_ports:
                raise Exception('This task does not support dynamic port allocation and is therefore not supported using singularity on Slurm')

            # Set pass if any
            if task.auth_pass:
                authstring = ' export SINGULARITYENV_AUTH_PASS={} && '.format(task.auth_pass)
            else:
                authstring = ''

            bindings = task.computing.get_conf_param('bindings', from_sys_only=True )
            if not bindings:
                bindings = ''
            else:
                bindings = '-B {}'.format(bindings)

            run_command = 'ssh -i {} -4 -o StrictHostKeyChecking=no {}@{} '.format(user_keys.private_key_file, user, host)

            run_command += '\'bash -c "echo \\"#!/bin/bash\nwget {}/api/v1/base/agent/?task_uuid={} -O \$HOME/agent_{}.py &> \$HOME/{}.log && export BASE_PORT=\\\\\\$(python \$HOME/agent_{}.py 2> \$HOME/{}.log) && '.format(webapp_conn_string, task.uuid, task.uuid, task.uuid, task.uuid, task.uuid)
            run_command += 'export SINGULARITY_NOHTTPS=true && export SINGULARITYENV_BASE_PORT=\\\\\\$BASE_PORT && {} '.format(authstring)
            run_command += 'exec nohup singularity run {} --pid --writable-tmpfs --containall --cleanenv '.format(bindings)
            
            # Double to escape for python six for shell (double times three as \\\ escapes a single slash in shell)

            # Set registry
            if task.container.registry == 'docker_local':
                # Get local Docker registry conn string
                from.utils import get_local_docker_registry_conn_string
                local_docker_registry_conn_string = get_local_docker_registry_conn_string()
                registry = 'docker://{}/'.format(local_docker_registry_conn_string)
            elif task.container.registry == 'docker_hub':
                registry = 'docker://'
            else:
                raise NotImplementedError('Registry {} not supported'.format(task.container.registry))
    
            run_command+='{}{} &> \$HOME/{}.log\\" > \$HOME/{}.sh && sbatch {} \$HOME/{}.sh"\''.format(registry, task.container.image, task.uuid, task.uuid, sbatch_args, task.uuid)

            
        else:
            raise NotImplementedError('Container {} not supported'.format(task.container.type))

        out = os_shell(run_command, capture=True)
        if out.exit_code != 0:
            raise Exception(out.stderr)

        # Log        
        logger.debug('Shell exec output: "{}"'.format(out))

        # Parse sbatch output. Example: Output(stdout='Submitted batch job 3', stderr='', exit_code=0)
        job_id = out.stdout.split(' ')[-1]
        try:
            int(job_id)
        except:
            raise Exception('Cannot find int job id from output string "{}"'.format(out.stdout))
        
        # Load back the task to avoid concurrency problems in the agent call
        task_uuid = task.uuid
        task = Task.objects.get(uuid=task_uuid)

        # Save job id as task pid
        task.pid = job_id
        
        # Set status (only fi we get here before the agent which sets the status as running via the API)
        if task.status != TaskStatuses.running:
            task.status = TaskStatuses.sumbitted
        
        # Save
        task.save()


    def _stop_task(self, task, **kwargs):
        
        # Get user keys
        if task.computing.require_user_keys:
            user_keys = Keys.objects.get(user=task.user, default=True)
        else:
            raise NotImplementedError('Remote tasks not requiring keys are not yet supported')

        # Get computing host
        host = task.computing.get_conf_param('master')
        user = task.computing.get_conf_param('user')

        # Stop the task remotely
        stop_command = 'ssh -i {} -4 -o StrictHostKeyChecking=no {}@{} \'/bin/bash -c "scancel {}"\''.format(user_keys.private_key_file, user, host, task.pid)
        logger.debug(stop_command)
        out = os_shell(stop_command, capture=True)
        if out.exit_code != 0:
            raise Exception(out.stderr)
        
        # Set task as topped
        task.status = TaskStatuses.stopped
        task.save()


    def _get_task_log(self, task, **kwargs):
        
        # Get user keys
        if task.computing.require_user_keys:
            user_keys = Keys.objects.get(user=task.user, default=True)
        else:
            raise NotImplementedError('Remote tasks not requiring keys are not yet supported')

        # Get computing host
        host = task.computing.get_conf_param('master')
        user = task.computing.get_conf_param('user')

        # Stop the task remotely
        view_log_command = 'ssh -i {} -4 -o StrictHostKeyChecking=no {}@{} \'/bin/bash -c "cat \$HOME/{}.log"\''.format(user_keys.private_key_file, user, host, task.uuid)

        out = os_shell(view_log_command, capture=True)
        if out.exit_code != 0:
            raise Exception(out.stderr)
        else:
            return out.stdout









