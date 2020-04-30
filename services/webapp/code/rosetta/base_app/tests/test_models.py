import json

from django.contrib.auth.models import User
        
from .common import BaseAPITestCase
from ..models import Profile, Computing, ComputingSysConf

class Modeltest(BaseAPITestCase):

    def setUp(self):
        
        # Create test users
        self.user = User.objects.create_user('testuser', password='testpass')
        self.anotheruser = User.objects.create_user('anotheruser', password='anotherpass')

        # Create test profile
        Profile.objects.create(user=self.user, authtoken='ync719tce917tec197t29cn712eg')


    def test_computing(self):
        '''Test Computing and their Conf models''' 
         
        computing = Computing.objects.create(name='MyComp', type='remote')
        
        computingSysConf = ComputingSysConf.objects.create(computing=computing, data={'myvar':42})
        
        self.assertEqual(ComputingSysConf.objects.all()[0].data, {'myvar':42})
        

