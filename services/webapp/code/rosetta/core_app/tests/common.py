import json
from django.test import TestCase
from rest_framework.test import APIClient as Client
from django.test.client import MULTIPART_CONTENT
from rest_framework import status
from rest_framework.reverse import reverse
from django.contrib.auth.models import User

class APIClient(Client):
    # Add patch to test client object
    def patch(self, path, data='', content_type=MULTIPART_CONTENT, follow=False, **extra):
        return self.generic('PATCH', path, data, content_type, **extra)

    # Add options to test client object
    def options(self, path, data='', content_type=MULTIPART_CONTENT, follow=False, **extra):
        return self.generic('OPTIONS', path, data, content_type, **extra)


class BaseAPITestCase(TestCase):

    def __init__(self, *args, **kwargs):
        self.maxDiff = None
        super(TestCase, self).__init__(*args, **kwargs)

    def send_request(self, request_method, *args, **kwargs):

        request_func = getattr(self.client, request_method)
        status_code  = None
       
        if 'multipart' in kwargs and kwargs['multipart'] is True:
            # Do nothing, this is a "special", multipart request 
            pass
        else:
            if 'content_type' not in kwargs and request_method != 'get':
                kwargs['content_type'] = 'application/json'
            
            if 'data' in kwargs and request_method != 'get' and kwargs['content_type'] == 'application/json':
                data = kwargs.get('data', '')
                kwargs['data'] = json.dumps(data)

        if 'status_code' in kwargs:
            status_code = kwargs.pop('status_code')

        self.response = request_func(*args, **kwargs)

        # Parse response
        is_json = False

        if 'content-type' in self.response._headers:
            is_json = bool(filter(lambda x: 'json' in x, self.response._headers['content-type']))

        try:
            if is_json and self.response.content:
                self.response.content_dict = json.loads(self.response.content)
            else:
                self.response.content_dict = {}
            
        except:
            self.response.content_dict = {}
        
        if status_code:
            if not self.response.status_code == status_code:
                raise Exception('Error with response:' + str(self.response))
        return self.response

    def post(self, *args, **kwargs):
        return self.send_request('post', *args, **kwargs)

    def get(self, *args, **kwargs):
        return self.send_request('get', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.send_request('put', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.send_request('delete', *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self.send_request('patch', *args, **kwargs)

    def init(self):
        self.client = APIClient()

    def assertRedirects(self, *args, **kwargs):
        super(BaseAPITestCase, self).assertRedirects(*args, **kwargs)








