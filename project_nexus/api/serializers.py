from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from drf_spectacular.utils import extend_schema_field

from email_validator import validate_email, EmailNotValidError

from rest_framework import serializers, validators
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import Genre, UserProfile, FavoriteMovie
from api.utils import get_movie_by_id
from api.movie_data_redis import get_trending_movies

User = get_user_model()


class RegisterUserSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Handles email and password validation during sign-up.
    """

    email = serializers.EmailField(
        validators=[
            validators.UniqueValidator(
                queryset=User.objects.all(),
                message="A user with the provided email already exists!",
            )
        ],
        error_messages={
            "invalid": "Please provide a valid email address "
                        "in the format user@example.com."
        },
    )
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "password", "password2"]

    def _create_jwt_pair_for_user(self, user):
        """Generate a JWT token pair for the given user."""
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    def validate_email(self, value):
        """Normalize and validate the email format and deliverability."""
        try:
            email_info = validate_email(value, check_deliverability=True)
            return email_info.normalized
        except EmailNotValidError as exc:
            raise serializers.ValidationError(f"Error: {exc}") from exc

    def validate_password(self, value):
        """Use Django’s password validators for stronger password rules."""
        try:
            validate_password(value, user=None)
        except Exception as exc:
            raise serializers.ValidationError(f"Invalid password: {exc}") from exc
        return value

    def validate(self, attrs):
        """Ensure both passwords match."""
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                "Passwords do not match.", code="invalid"
            )
        return attrs

    def to_representation(self, instance):
        """Optionally include JWT tokens in response if context flag is set."""
        data = super().to_representation(instance)
        if self.context.get("include_tokens", False):
            data["tokens"] = self._create_jwt_pair_for_user(instance)
        return data

    def create(self, validated_data):
        """Create a new user with validated email and password."""
        validated_data.pop("password2")
        password = validated_data.pop("password")
        email = validated_data.pop("email")
        return User.objects.create_user(
            password=password,
            email=email,
            username=email,
        )


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for requesting password reset."""

    email = serializers.EmailField()

    def validate_email(self, value):
        """Normalize and validate the email format."""
        try:
            email_info = validate_email(value, check_deliverability=True)
            return email_info.normalized
        except EmailNotValidError as exc:
            raise serializers.ValidationError(f"Error: {exc}") from exc


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing a password via UID + token."""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):
        """Ensure new and confirm passwords match."""
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                "Passwords do not match.", code="invalid"
            )
        return attrs


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for User model.
    Exposes ID, names, and email fields.
    """

    class Meta:
        model = User
        fields = ["user_id", "first_name", "last_name", "email"]
        read_only_fields = ["user_id"]

    def validate_email(self, value):
        """Normalize and validate the email format."""
        try:
            email_info = validate_email(value, check_deliverability=True)
            return email_info.normalized
        except EmailNotValidError as exc:
            raise serializers.ValidationError(f"Error: {exc}") from exc


class UserLightSerializer(serializers.ModelSerializer):
    """Lightweight user serializer exposing only email and full name."""

    fullname = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["email", "fullname"]
        read_only_fields = ("email",)

    @extend_schema_field(serializers.CharField)
    def get_fullname(self, obj):
        """Return either full_name property or fallback to first + last name."""
        return getattr(obj, "full_name", f"{obj.first_name} {obj.last_name}")


class GenreSerializer(serializers.ModelSerializer):
    """Serializer for movie genres."""

    class Meta:
        model = Genre
        fields = ["id", "name"]
        read_only_fields = ["id", "name"]
        ordering = ["name"]


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profiles, including favorite genres and profile picture.
    Accepts genre names from users and validates them against the Genre table.
    """

    genres = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
    )
    genres_display = serializers.SerializerMethodField(read_only=True)
    user = UserLightSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "user",
            "profile_picture",
            "description",
            "genres",
            "genres_display",
        ]

    def validate_profile_picture(self, value):
        """Check that profile picture is of allowed formats."""
        if hasattr(value, "content_type"):
            if value.content_type not in ["image/jpeg", "image/png", "image/webp"]:
                raise serializers.ValidationError("Unsupported image format.")
        return value

    def validate_genres(self, value):
        """Ensure supplied genre names exist in the database."""
        available_genres = set(Genre.objects.values_list("name", flat=True))
        supplied_genres = set(value)

        invalid = supplied_genres - available_genres
        if invalid:
            raise serializers.ValidationError(
                {
                    "genres": (
                        f"Invalid genres: {', '.join(invalid)}. "
                        f"Available genres are: {', '.join(sorted(available_genres))}"
                    )
                }
            )
        return list(supplied_genres)

    def update(self, instance, validated_data):
        """Update profile and attach selected genres."""
        genre_names = validated_data.pop("genres", [])
        profile = super().update(instance, validated_data)
        if genre_names:
            genres = Genre.objects.filter(name__in=genre_names)
            profile.genres.set(genres)
        return profile

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_genres_display(self, obj):
        """Return saved genres as a list of names."""
        return list(obj.genres.values_list("name", flat=True))


class FavoriteMovieReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for favorite movies."""

    genres = serializers.SerializerMethodField()

    class Meta:
        model = FavoriteMovie
        fields = [
            "id",
            "movie_id",
            "title",
            "description",
            "release_date",
            "poster_url",
            "genres",
            "date_favorited",
        ]
        read_only_fields = [
            "id",
            "movie_id",
            "title",
            "description",
            "release_date",
            "poster_url",
            "date_favorited",
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_genres(self, obj):
        """Return genre names for the movie."""
        return list(obj.genres.values_list("name", flat=True))


class FavoriteMovieWriteSerializer(serializers.ModelSerializer):
    """
    Write serializer for favorite movies.
    Allows users to save a movie to their favorites by ID.
    """

    class Meta:
        model = FavoriteMovie
        fields = ["movie_id"]

    def validate_movie_id(self, value: int) -> int:
        """Ensure the movie exists in cache before allowing favorite."""
        movie_data = get_movie_by_id(
            value,
            results=get_trending_movies().get("results", []),
        )
        if not movie_data:
            raise serializers.ValidationError("Movie not found in cache.")
        return value

    def create(self, validated_data: dict):
        """Save a new favorite movie for the user."""
        user = self.context["request"].user
        data = self._extract_movie_data(validated_data)
        genre_ids = data.pop("genre_ids", [])

        catalogue, created = FavoriteMovie.objects.get_or_create(
            favorited_by=user,
            movie_id=data["movie_id"],
            defaults=data,
        )

        if created and genre_ids:
            found_genres = Genre.objects.filter(id__in=genre_ids)
            catalogue.genres.set(found_genres)

        return catalogue

    def _extract_movie_data(self, validated_data):
        """Helper to transform cached API data into model fields."""
        movie_data = get_movie_by_id(
            target_value=validated_data["movie_id"],
            results=get_trending_movies().get("results", []),
        )
        if not movie_data:
            raise serializers.ValidationError("Movie not found in cache.")

        base_url = "https://image.tmdb.org/t/p/w500"
        poster_path = movie_data.get("poster_path")

        return {
            "movie_id": movie_data.get("id"),
            "title": movie_data.get("title"),
            "description": movie_data.get("overview"),
            "release_date": movie_data.get("release_date"),
            "poster_url": f"{base_url}{poster_path}" if poster_path else None,
            "genre_ids": movie_data.get("genre_ids", []),
        }


class MovieOutputSerializer(serializers.Serializer):
    """Read serializer for movies returned from the API call."""

    movie_id = serializers.IntegerField(source="id")
    title = serializers.CharField()
    popularity = serializers.FloatField()
    release_date = serializers.CharField(allow_null=True)
    description = serializers.CharField(source="overview")
    poster_url = serializers.SerializerMethodField()
    genres = serializers.SerializerMethodField()

    class Meta:
        read_only_fields = [
            "movie_id",
            "title",
            "popularity",
            "release_date",
            "description",
            "poster_url",
            "genres",
        ]

    @extend_schema_field(serializers.URLField)
    def get_poster_url(self, obj):
        """Construct the full poster URL for the movie."""
        path = obj.get("poster_path")
        if not path:
            return None
        base = self.context.get(
            "image_base_url",
            "https://image.tmdb.org/t/p/w500",
        )
        return f"{base.rstrip('/')}/{path.lstrip('/')}"

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_genres(self, obj):
        """Return the genre names for the movie."""
        genre_ids = obj.get("genre_ids", [])
        return list(
            Genre.objects.filter(id__in=genre_ids).values_list("name", flat=True)
        )