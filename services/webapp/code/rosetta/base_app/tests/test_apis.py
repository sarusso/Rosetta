import json

from django.contrib.auth.models import User
        
from .common import BaseAPITestCase
from ..models import Profile

class ApiTests(BaseAPITestCase):

    def setUp(self):
        
        # Create test users
        self.user = User.objects.create_user('testuser', password='testpass')
        self.anotheruser = User.objects.create_user('anotheruser', password='anotherpass')

        # Create test profile
        Profile.objects.create(user=self.user, authtoken='ync719tce917tec197t29cn712eg')


    def test_api_web_auth(self):
        '''Test auth using login api''' 
         
        # No user at all
        resp = self.post('/api/v1/base/login/', data={})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(json.loads(resp.content), {"detail": "This is a private API. Login or provide username/password or auth token"})

        # Wrong user
        resp = self.post('/api/v1/base/login/', data={'username':'wronguser', 'password':'testpass'})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(json.loads(resp.content), {"detail": "Wrong username/password"})

        # Wrong pass
        resp = self.post('/api/v1/base/login/', data={'username':'testuser', 'password':'wrongpass'})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(json.loads(resp.content), {"detail": "Wrong username/password"})

        # Correct user
        resp = self.post('/api/v1/base/login/', data={'username': 'testuser', 'password':'testpass'})
        self.assertEqual(resp.status_code, 200)








        