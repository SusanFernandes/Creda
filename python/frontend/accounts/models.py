"""Custom User model — Django manages users, FastAPI references user.id via JWT."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model. Django owns this table (creda_django database).
    The user.id becomes user_id in every FastAPI model (creda_api database).
    JWT is the link between the two databases.
    """
    language = models.CharField(max_length=10, default="en")

    class Meta:
        db_table = "auth_user"
