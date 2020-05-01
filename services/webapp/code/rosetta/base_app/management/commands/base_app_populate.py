from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ...models import Profile, Container, Computing, ComputingSysConf, ComputingUserConf, Keys

class Command(BaseCommand):
    help = 'Adds the admin superuser with \'a\' password.'

    def handle(self, *args, **options):

        # Admin
        try:
            User.objects.get(username='admin')
            print('Not creating admin user as it already exist')
        except User.DoesNotExist:
            print('Creating admin user with default password')
            admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            Profile.objects.create(user=admin)
        
        # Testuser
        try:
            testuser = User.objects.get(username='testuser')
            print('Not creating test user as it already exist')
        
        except User.DoesNotExist:
            print('Creating test user with default password')
            testuser = User.objects.create_user('testuser', 'testuser@rosetta.platform', 'testpass')
            print('Making testuser admin')
            testuser.is_staff = True
            testuser.is_admin=True
            testuser.is_superuser=True
            testuser.save() 
            print('Creating testuser profile')
            Profile.objects.create(user=testuser, authtoken='129aac94-284a-4476-953c-ffa4349b4a50')

            # Create default keys
            print('Creating testuser defualt keys')
            Keys.objects.create(user = testuser,
                                default = True,
                                private_key_file = '/rosetta/.ssh/id_rsa',
                                public_key_file = '/rosetta/.ssh/id_rsa.pub')
            

        # Public containers
        public_containers = Container.objects.filter(user=None)
        if public_containers:
            print('Not creating public containers as they already exist')
        else:
            print('Creating public containers...')
            
            # MetaDesktop Docker
            Container.objects.create(user     = None,
                                     name     = 'MetaDesktop latest',
                                     image    = 'rosetta/metadesktop',
                                     type     = 'docker',
                                     registry = 'docker_local',
                                     ports    = '8590',
                                     supports_dynamic_ports = True,
                                     supports_user_auth     = False,
                                     supports_pass_auth     = True)

            # MetaDesktop Singularity
            Container.objects.create(user     = None,
                                     name     = 'MetaDesktop latest',
                                     image    = 'rosetta/metadesktop',
                                     type     = 'singularity',
                                     registry = 'docker_local',
                                     ports    = '8590',
                                     supports_dynamic_ports = True,
                                     supports_user_auth     = False,
                                     supports_pass_auth     = True)

            # Astrocook
            Container.objects.create(user     = None,
                                     name     = 'Astrocook b2b819e',
                                     image    = 'sarusso/astrocook:b2b819e',
                                     type     = 'docker',
                                     registry = 'docker_local',
                                     ports    = '8590',
                                     supports_dynamic_ports = False,
                                     supports_user_auth     = False,
                                     supports_pass_auth     = False)


        # Private containers
        testuser_containers = Container.objects.filter(user=testuser)
        if testuser_containers:
            print('Not creating testuser private containers as they already exist')
        else:
            print('Creating testuser private containers...')
            
            # JuPyter
            Container.objects.create(user     = testuser,
                                     name     = 'Jupyter Notebook latest',
                                     image    = 'jupyter/base-notebook',
                                     type     = 'docker',
                                     registry = 'docker_hub',
                                     ports    = '8888', 
                                     supports_dynamic_ports = False,
                                     supports_user_auth     = False,
                                     supports_pass_auth     = False)

        # Computing resources
        computing_resources = Computing.objects.all()
        if computing_resources:
            print('Not creating demo computing resources as they already exist')
        else:
            print('Creating demo computing resources containers...')

            #==============================
            #  Local remote computing
            #==============================
            Computing.objects.create(user = None,
                                     name = 'Local',
                                     type = 'local',
                                     require_sys_conf  = False,
                                     require_user_conf = False,
                                     require_user_keys = False)


            #==============================
            # Demo remote computing 
            #==============================    
            demo_remote_auth_computing = Computing.objects.create(user = None,
                                                             name = 'Demo remote',
                                                             type = 'remote',
                                                             require_sys_conf  = True,
                                                             require_user_conf = True,
                                                             require_user_keys = True)
    
            ComputingSysConf.objects.create(computing = demo_remote_auth_computing,
                                            data      = {'host': 'slurmclusterworker-one'})

            ComputingUserConf.objects.create(user      = testuser,
                                             computing = demo_remote_auth_computing,
                                             data      = {'user': 'slurmtestuser'})
         

            #==============================
            #  Demo Slurm computing
            #==============================
            demo_slurm_computing = Computing.objects.create(user = None,
                                                            name = 'Demo Slurm',
                                                            type = 'slurm',
                                                            require_sys_conf  = True,
                                                            require_user_conf = True,
                                                            require_user_keys = True)
    
            # Create demo slurm sys computing conf
            ComputingSysConf.objects.create(computing = demo_slurm_computing,
                                            data      = {'master': 'slurmclustermaster-main'})

            # Create demo slurm user computing conf
            ComputingUserConf.objects.create(user      = testuser,
                                             computing = demo_slurm_computing,
                                             data      = {'user': 'slurmtestuser'})


