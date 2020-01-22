from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ...models import Profile, Container

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
            User.objects.get(username='testuser')
            print('Not creating test user as it already exist')
        except User.DoesNotExist:
            print('Creating test user with default password')
            testuser = User.objects.create_user('testuser', 'testuser@rosetta.platform', 'testpass')
            Profile.objects.create(user=testuser, authtoken='129aac94-284a-4476-953c-ffa4349b4a50')

        # public containers
        public_containers = Container.objects.filter(user=None)
        if public_containers:
            print('Not creating public containers as they already exist')
        else:
            print('Creating public containers...')
            
            # MetaDesktop Docker
            Container.objects.create(user          = None,
                                     image         = 'rosetta/metadesktop',
                                     type          = 'docker',
                                     registry      = 'docker_local',
                                     service_ports = '8590')

            # Astrocook
            Container.objects.create(user          = None,
                                     image         = 'sarusso/astrocook:b2b819e',
                                     type          = 'docker',
                                     registry      = 'docker_local',
                                     service_ports = '8590')














