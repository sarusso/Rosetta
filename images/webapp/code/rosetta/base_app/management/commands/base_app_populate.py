from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ...models import Profile

class Command(BaseCommand):
    help = 'Adds the admin superuser with \'a\' password.'

    def handle(self, *args, **options):

        try:
            User.objects.get(username='admin')
            print('Not creating admin user as it already exist')
        except User.DoesNotExist:
            print('Creating admin user with default password')
            admin = User.objects.create_superuser('admin', 'admin@example.com', 'a')
            Profile.objects.create(user=admin)

        try:
            User.objects.get(username='testuser')
            print('Not creating test user as it already exist')
        except User.DoesNotExist:
            print('Creating test user with default password')
            testuser = User.objects.create_user('testuser', 'testuser@rosetta.platform', 'testpass')
            Profile.objects.create(user=testuser, authtoken='129aac94-284a-4476-953c-ffa4349b4a50')
            