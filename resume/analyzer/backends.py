from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username

        # Use filter().first() instead of get()
        user = User.objects.filter(email=email).order_by('id').first()

        if user and user.check_password(password):
            return user
        return None
