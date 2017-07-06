"""service URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.shortcuts import redirect
from django.conf.urls import include, url
from django.contrib import admin, staticfiles, messages
from registration.backends.hmac.views import RegistrationView

from web.forms import UserForm
from . import settings

def activation_complete(request):
    messages.success(request, "Congratulations, your account is now activated! Login and submit!")
    return redirect("auth_login")

def registration_complete(request):
    messages.success(request, "Thanks for registering! Please check your email to activate your account.")
    return redirect("home")

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^accounts/register/$', RegistrationView.as_view(form_class=UserForm, success_url='/submissions/'),
        name='registration_register',
       ),
    url(r'^accounts/register/complete/$', registration_complete, name='registration_complete',),
    url(r'^accounts/activate/complete/$', activation_complete, name='registration_activation_complete',),
    url(r'^accounts/', include('registration.backends.hmac.urls')),
    url(r'', include('web.urls')),
]
if settings.DEBUG and hasattr(staticfiles, 'views'):
    urlpatterns += [
        url(r'^static/(?P<path>.*)$', staticfiles.views.serve),
    ]
handler404 = 'web.views.handle404'
handler500 = 'web.views.handle500'
