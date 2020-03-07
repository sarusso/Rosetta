from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ...models import Profile, Container, Computing, ComputingSysConf, ComputingUserConf

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
            

        # Public containers
        public_containers = Container.objects.filter(user=None)
        if public_containers:
            print('Not creating public containers as they already exist')
        else:
            print('Creating public containers...')
            
            # MetaDesktop Docker
            Container.objects.create(user          = None,
                                     name          = 'MetaDesktop latest',
                                     image         = 'rosetta/metadesktop',
                                     type          = 'docker',
                                     registry      = 'docker_local',
                                     service_ports = '8590')

            # MetaDesktop Singularity
            Container.objects.create(user          = None,
                                     name          = 'MetaDesktop latest',
                                     image         = 'rosetta/metadesktop',
                                     type          = 'singularity',
                                     registry      = 'docker_local',
                                     service_ports = '8590')

            # Astrocook
            Container.objects.create(user          = None,
                                     name          = 'Astrocook b2b819e',
                                     image         = 'sarusso/astrocook:b2b819e',
                                     type          = 'docker',
                                     registry      = 'docker_local',
                                     service_ports = '8590')


        # Public containers
        testuser_containers = Container.objects.filter(user=testuser)
        if testuser_containers:
            print('Not creating testuser containers as they already exist')
        else:
            print('Creating testuser containers...')
            
            # JuPyter
            Container.objects.create(user          = testuser,
                                     name          = 'Jupyter Notebook latest',
                                     image         = 'jupyter/base-notebook',
                                     type          = 'docker',
                                     registry      = 'docker_hub',
                                     service_ports = '8888')

        # Computing resources
        computing_resources = Computing.objects.all()
        if computing_resources:
            print('Not creating demo computing resources as they already exist')
        else:
            print('Creating demo computing resources containers...')

            # Local computing resource
            Computing.objects.create(user = None,
                                     name = 'Local',
                                     type = 'local')
    
            # Demo remote computing resource
            demo_remote_computing = Computing.objects.create(user = None,
                                     name = 'Demo remote',
                                     type = 'remote',
                                     requires_sys_conf  = True,
                                     requires_user_conf = False)
    
            # Create demo remote sys computing conf
            ComputingSysConf.objects.create(computing = demo_remote_computing,
                                            data      = {'host': 'slurmclusterworker-one'})

            # Create demo remote user computing conf
            ComputingUserConf.objects.create(user      = testuser,
                                             computing = demo_remote_computing,
                                             data      = {'user': 'testuser',
                                                          'id_rsa': '/rosetta/.ssh/id_rsa',
                                                          'id_rsa.pub': 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC2n4wiLiRmE1sla5+w0IW3wwPW/mqhhkm7IyCBS+rGTgnts7xsWcxobvamNdD6KSLNnjFZbBb7Yaf/BvWrwQgdqIFVU3gRWHYzoU6js+lKtBjd0e2DAVGivWCKEkSGLx7zhx7uH/Jt8kyZ4NaZq0p5+SFHBzePdR/1rURd8G8+G3OaCPKqP+JQT4RMUQHC5SNRJLcK1piYdmhDiYEyuQG4FlStKCWLCXeUY2EVirNMeQIfOgbUHJsVjH07zm1y8y7lTWDMWVZOnkG6Ap5kB+n4l1eWbslOKgDv29JTFOMU+bvGvYZh70lmLK7Hg4CMpXVgvw5VF9v97YiiigLwvC7wasBHaASwH7wUqakXYhdGFxJ23xVMSLnvJn4S++4L8t8bifRIVqhT6tZCPOU4fdOvJKCRjKrf7gcW/E33ovZFgoOCJ2vBLIh9N9ME0v7tG15JpRtgIBsCXwLcl3tVyCZJ/eyYMbc3QJGsbcPGb2CYRjDbevPCQlNavcMdlyrNIke7VimM5aW8OBJKVh5wCNRpd9XylrKo1cZHYxu/c5Lr6VUZjLpxDlSz+IuTn4VE7vmgHNPnXdlxRKjLHG/FZrZTSCWFEBcRoSa/hysLSFwwDjKd9nelOZRNBvJ+NY48vA8ixVnk4WAMlR/5qhjTRam66BVysHeRcbjJ2IGjwTJC5Q== rosetta@rosetta.platform'})



            # Demo slurm computing resource
            demo_slurm_computing = Computing.objects.create(user = None,
                                     name = 'Demo Slurm',
                                     type = 'slurm',
                                     requires_sys_conf  = True,
                                     requires_user_conf = True)
    
            # Create demo slurm sys computing conf
            ComputingSysConf.objects.create(computing = demo_slurm_computing,
                                            data      = {'master': 'slurmclusterworker-master'})

            # Create demo slurm user computing conf
            ComputingUserConf.objects.create(user      = testuser,
                                             computing = demo_slurm_computing,
                                             data      = {'user': 'testuser',
                                                          'id_rsa': '/rosetta/.ssh/id_rsa',
                                                          'id_rsa.pub': 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC2n4wiLiRmE1sla5+w0IW3wwPW/mqhhkm7IyCBS+rGTgnts7xsWcxobvamNdD6KSLNnjFZbBb7Yaf/BvWrwQgdqIFVU3gRWHYzoU6js+lKtBjd0e2DAVGivWCKEkSGLx7zhx7uH/Jt8kyZ4NaZq0p5+SFHBzePdR/1rURd8G8+G3OaCPKqP+JQT4RMUQHC5SNRJLcK1piYdmhDiYEyuQG4FlStKCWLCXeUY2EVirNMeQIfOgbUHJsVjH07zm1y8y7lTWDMWVZOnkG6Ap5kB+n4l1eWbslOKgDv29JTFOMU+bvGvYZh70lmLK7Hg4CMpXVgvw5VF9v97YiiigLwvC7wasBHaASwH7wUqakXYhdGFxJ23xVMSLnvJn4S++4L8t8bifRIVqhT6tZCPOU4fdOvJKCRjKrf7gcW/E33ovZFgoOCJ2vBLIh9N9ME0v7tG15JpRtgIBsCXwLcl3tVyCZJ/eyYMbc3QJGsbcPGb2CYRjDbevPCQlNavcMdlyrNIke7VimM5aW8OBJKVh5wCNRpd9XylrKo1cZHYxu/c5Lr6VUZjLpxDlSz+IuTn4VE7vmgHNPnXdlxRKjLHG/FZrZTSCWFEBcRoSa/hysLSFwwDjKd9nelOZRNBvJ+NY48vA8ixVnk4WAMlR/5qhjTRam66BVysHeRcbjJ2IGjwTJC5Q== rosetta@rosetta.platform'})




