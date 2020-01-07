from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout

# Setup logging
import logging
logger = logging.getLogger(__name__)

class ErrorMessage(Exception):
    pass


def main_view(request):
    return render(request, 'main.html')
 

def login_view(request):

    data={}

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if (not username) or (not password):
            data['error'] = 'Empty username or password'
        
        if request.user.is_authenticated:
            logout(request)
            
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return HttpResponseRedirect('/')
        else:
            data['error'] = 'Check username and password'

    
    # Render the login page again with no other data than title
    return render(request, 'login.html', {'data': data})



def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')









