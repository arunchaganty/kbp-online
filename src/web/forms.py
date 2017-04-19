from registration.forms import RegistrationForm
from .models import User 

class UserForm(RegistrationForm):
    class Meta:
        model = User
        fields = ["first_name","last_name", "affiliation", "username", "email"]
