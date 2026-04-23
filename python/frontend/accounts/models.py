"""Custom User model — Django manages users, FastAPI references user.id via JWT."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model — Django table in creda_django.
    FastAPI domain rows use users.id in creda_api (UUID string), not Django's integer pk.
    Session keys backend_jwt + backend_user_id link the two (see accounts.views, middleware).
    """
    language = models.CharField(max_length=10, default="en")

    class Meta:
        db_table = "auth_user"
