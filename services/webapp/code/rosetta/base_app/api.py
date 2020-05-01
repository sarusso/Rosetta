import logging
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from rest_framework.response import Response
from rest_framework import status, serializers, viewsets
from rest_framework.views import APIView
from .utils import format_exception
from .models import Profile, Task, TaskStatuses
 
# Setup logging
logger = logging.getLogger(__name__)


#==============================
#  Common returns
#==============================
 
# Ok (with data)
def ok200(data=None):
    return Response({"results": data}, status=status.HTTP_200_OK)
 
# Error 400
def error400(data=None):
    return Response({"detail": data}, status=status.HTTP_400_BAD_REQUEST)
 
# Error 401
def error401(data=None):
    return Response({"detail": data}, status=status.HTTP_401_UNAUTHORIZED)
 
# Error 404
def error404(data=None):
    return Response({"detail": data}, status=status.HTTP_404_NOT_FOUND)
 
# Error 500
def error500(data=None):
    return Response({"detail": data}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


 
#==============================
#  Authentication helper
#==============================
 
def rosetta_authenticate(request):

    # Get data
    user      = request.user if request.user.is_authenticated else None
    username  = request.data.get('username', None)
    password  = request.data.get('password', None)
    authtoken = request.data.get('authtoken', None)

    # Try standard user authentication
    if user:
        return user

    # Try username/password  authentication
    elif username or password:
        
        # Check we got both
        if not username:
            return error400('Got empty username')
        if not password:
            return error400('Got empty password')
 
        # Authenticate
        user = authenticate(username=username, password=password)
        if not user:
            return error401('Wrong username/password')  
        else:
            login(request, user)
            return user

    # Try auth toekn authentication 
    elif authtoken:
        try:
            profile = Profile.objects.get(authtoken=authtoken)
        except Profile.DoesNotExist:
            return error400('Wrong auth token')
        login(request, profile.user)
        return profile.user
    else:
        return error401('This is a private API. Login or provide username/password or auth token')



#==============================
#  Base public API class
#==============================
 
class PublicPOSTAPI(APIView):
    '''Base public POST API class'''
 
    # POST
    def post(self, request):
        try:
            return self._post(request)
        except Exception as e:
            logger.error(format_exception(e))
            return error500('Got error in processing request: {}'.format(e))
 
class PublicGETAPI(APIView):
    '''Base public GET API class''' 
    # GET
    def get(self, request):
        try:
            return self._get(request)
        except Exception as e:
            logger.error(format_exception(e))
            return error500('Got error in processing request: {}'.format(e))



#==============================
#  Base private API class
#==============================
 
class PrivatePOSTAPI(APIView):
    '''Base private POST API class'''
 
    # POST
    def post(self, request):
        try:
            # Authenticate using rosetta authentication
            response = rosetta_authenticate(request)
             
            # If we got a response return it, otherwise set it as the user.
            if isinstance(response, Response):
                return response
            else:
                self.user = response
             
            # Call API logic
            return self._post(request)
        except Exception as e:
            logger.error(format_exception(e))
            return error500('Got error in processing request: {}'.format(e))
 
class PrivateGETAPI(APIView):
    '''Base private GET API class'''

    # GET  
    def get(self, request):
        try:
            # Authenticate using rosetta authentication
            response = rosetta_authenticate(request)
             
            # If we got a response return it, otherwise set it as the user.
            if isinstance(response, Response):
                return response
            else:
                self.user = response
             
            # Call API logic
            return self._get(request)
        except Exception as e:
            logger.error(format_exception(e))
            return error500('Got error in processing request: {}'.format(e))



#==============================
#  User & profile APIs
#==============================

class login_api(PrivateGETAPI, PrivatePOSTAPI):
    """
    get:
    Returns the auth token.

    post:
    Authorize and returns the auth token.
    """
         
    def _post(self, request):
        return ok200({'authtoken': self.user.profile.authtoken})

    def _get(self, request):
        return ok200({'authtoken': self.user.profile.authtoken}) 
 
 
class logout_api(PrivateGETAPI):
    """
    get:
    Logout the user
    """
         
    def _get(self, request):
        logout(request)
        return ok200()


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Users to be viewed or edited.
    """

    class UserSerializer(serializers.HyperlinkedModelSerializer):
        class Meta:
            model = User
            fields = ('url', 'username', 'email', 'groups')

    queryset = User.objects.all().order_by('-date_joined')    
    serializer_class = UserSerializer


class agent_api(PublicGETAPI):
    
    def _get(self, request):
        try:
            
            task_uuid = request.GET.get('task_uuid', None)
            if not task_uuid:
                return HttpResponse('MISSING task_uuid')
    
            from django.core.exceptions import ValidationError
    
            try:
                task = Task.objects.get(uuid=task_uuid)
            except (Task.DoesNotExist, ValidationError):
                return HttpResponse('Unknown task uuid "{}"'.format(task_uuid))

            import socket
            hostname = socket.gethostname()
            webapp_ip = socket.gethostbyname(hostname)

            host_conn_string = 'http://{}:8080'.format(webapp_ip)
            
            action = request.GET.get('action', None)
            
            if not action:
                # Return the agent code
                agent_code='''
import logging
import socket
try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

# Setup logging
logger = logging.getLogger('Agent')
logging.basicConfig(level=logging.INFO)

hostname = socket.gethostname()

# Task id set by the API
task_uuid = "'''+ task_uuid  +'''"

# Log
logger.info('Reporting for task uuid: "{}"'.format(task_uuid))

# Get IP
ip = socket.gethostbyname(hostname)
logger.info(' - ip: "{}"'.format(ip))

# Get port
from random import randint
while True:

    # Get a random ephimeral port
    port = randint(49152, 65535-2)

    # Check port is available
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result1 = sock.connect_ex(('127.0.0.1', port))
    result2 = sock.connect_ex(('127.0.0.1', port+1))
    result3 = sock.connect_ex(('127.0.0.1', port+2))
    if (result1 == 0) or (result2 == 0) or (result3 == 0):
        logger.info('Found not available ephemeral port triplet ({},{},{}) , choosing another one...'.format(port,port+1,port+2))
        import time
        time.sleep(1)
    else:
        break
logger.info(' - ports: "{},{},{}"'.format(port, port+1, port+2))

response = urlopen("'''+host_conn_string+'''/api/v1/base/agent/?task_uuid={}&action=set_ip_port&ip={}&port={}".format(task_uuid, ip, port))
response_content = response.read() 
if response_content != 'OK':
    logger.error(response_content)
    logger.info('Not everything OK, exiting with status code =1')
    sys.exit(1)
else:
    logger.info('Everything OK')
print(port)
'''
        
                return HttpResponse(agent_code)
    
    
            elif action=='set_ip_port':
                
                task_ip   = request.GET.get('ip', None)
                if not task_ip:
                    return HttpResponse('IP not valid (got "{}")'.format(task_ip))
                
                task_port = request.GET.get('port', None)
                if not task_port:
                    return HttpResponse('Port not valid (got "{}")'.format(task_port))
                
                try:
                    int(task_port)
                except (TypeError, ValueError):
                    return HttpResponse('Port not valid (got "{}")'.format(task_port))
                  
                # Set fields
                logger.info('Setting task "{}" to ip "{}" and port "{}"'.format(task.uuid, task_ip, task_port))
                task.status = TaskStatuses.running
                task.ip     = task_ip
                task.port   = int(task_port)
                task.save()
                return HttpResponse('OK')
                
    
            else:
                return HttpResponse('Unknown action "{}"'.format(action))
    

        except Exception as e:
            logger.error(e)


















