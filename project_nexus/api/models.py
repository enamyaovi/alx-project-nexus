"""
Django models for the Movie Recommendation WebApp.

This module defines the core database schema:
- Genres
- Users (custom user model extending AbstractUser)
- UserProfile (extra attributes for Users)
- FavoriteMovies (user favorited catalogue)
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model


class Genre(models.Model):
    """
    Represents a movie genre (aligned with TMDB genres).
    """

    id = models.IntegerField(
        primary_key=True,
        help_text="TMDB genre ID."
    )
    name = models.CharField(
        max_length=100,
        help_text="Name of the genre."
    )

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    """
    Custom user model using email as the unique identifier.
    """

    username = None  # Remove username field from AbstractUser
    user_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Primary key: UUID for user."
    )
    email = models.EmailField(
        unique=True,
        help_text="User email, used for authentication."
    )
    first_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="User first name."
    )
    last_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="User last name."
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # No username required

    def __str__(self) -> str:
        return f"{self.email}"


class UserProfile(models.Model):
    """
    Extended user profile storing additional attributes.
    """

    user = models.OneToOneField(
        to=get_user_model(),
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="One-to-one link to User."
    )
    profile_picture = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
        help_text="Profile picture (optional)."
    )
    description = models.TextField(
        blank=True,
        help_text="User bio or description."
    )
    favorite_genres = models.ManyToManyField(
        to=Genre,
        blank=True,
        help_text="Preferred genres for recommendations."
    )

    def __str__(self) -> str:
        return f"Profile of {self.user.email}"


class FavoriteMovie(models.Model):
    """
    Represents a movie favorited by a user.
    """

    id = models.AutoField(
        primary_key=True,
        help_text="Internal auto-increment ID."
    )
    movie_id = models.IntegerField(
        help_text="TMDB movie ID."
    )
    title = models.CharField(
        max_length=255,
        help_text="Movie title."
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Movie description/overview."
    )
    release_date = models.DateField(
        help_text="Date of movie release."
    )
    poster_url = models.URLField(
        help_text="URL of the movie poster."
    )
    date_favorited = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the movie was added to favorites."
    )
    favorited_by = models.ForeignKey(
        to=get_user_model(),
        on_delete=models.CASCADE,
        related_name="favorites",
        help_text="User who favorited the movie."
    )
    genres = models.ManyToManyField(
        to=Genre,
        blank=True,
        help_text="Genres associated with the movie."
    )

    def __str__(self) -> str:
        return f"{self.title} (favorited by {self.favorited_by.email})"
