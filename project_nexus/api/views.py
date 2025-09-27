from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.urls import get_resolver, reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)

from rest_framework import permissions, status, viewsets, views
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse

from api.models import Genre, FavoriteMovie, ServiceAPIKey
from api.utils import IsUser, StandardPagination, get_or_set_cache

from api.movie_data_redis import get_trending_movies, search_movies_from_tmdb
from api.movie_data_redis import get_movie_by_id

from api.serializers import (
    FavoriteMovieReadSerializer,
    FavoriteMovieWriteSerializer,
    GenreSerializer,
    MovieOutputSerializer,
    PasswordChangeSerializer,
    PasswordResetSerializer,
    RegisterUserSerializer,
    UserDetailSerializer,
    UserLightSerializer,
    UserProfileSerializer,
)


User = get_user_model()

#custom method to serialize movie data when not in cache
def serialize_trending_movies():
    """
    Fetch trending movies from TMDB and serialize them.
    """
    results = get_trending_movies().get("results", [])
    serializer = MovieOutputSerializer(
        results,
        many=True,
        context={"image_base_url": "https://image.tmdb.org/t/p/w500"},
    )
    return serializer.data


@extend_schema(
        responses={
            200: OpenApiResponse(description='Returns a list of all endpoints')
        }
)
@api_view(['GET'])
def endpoints(request, format=None):
    """
    Manual API root listing all endpoints with Swagger/Redoc links.
    """
    api_endpoints = {
        # Movies
        "Trending Movies": reverse('api:movies-list', request=request, format=format),
        "Movie Detail": reverse('api:movie-detail', request=request, format=format, kwargs={'movie_id': 1311031}),
        "Search Movie": reverse('api:search-movie', request=request, format=format),
        "Favorite a Movie": reverse('api:add-movie-favorite', request=request, format=format, kwargs={'movie_id': 1311031}),
        "Remove Favorite Movie": reverse('api:remove-favorite-movie', request=request, format=format, kwargs={'movie_id': 1311031}),

        # Genres
        "List Genres": reverse('api:genre-list', request=request, format=format),

        # Users
        "List or Register Users": reverse('api:users-list', request=request, format=format),
        "User Detail": reverse('api:users-detail', request=request, format=format, kwargs={'user_id': 'valid_uuid'}),
        "Edit Profile (GET/PUT/PATCH)": reverse('api:users-edit-profile', request=request, format=format),
        "Change Password": reverse('api:users-password-change', request=request, format=format),
        "Password Reset": reverse('api:users-password-reset', request=request, format=format),
        "Recommended Movies": reverse('api:users-recommended-movies', request=request, format=format),
        "View Catalogue": reverse('api:users-view-catalogue', request=request, format=format),

        # JWT Authentication
        "Create Token": reverse('api:token_obtain_pair', request=request, format=format),
        "Refresh Token": reverse('api:token_refresh', request=request, format=format),

        # API Key
        "Get API Key": reverse('api:get-api-key', request=request, format=format),
    }

    return Response({
        "project": "Project Nexus Movie API",
        "description": "An API providing movie data, search, genre info, and user account management.",
        "endpoints": api_endpoints,
        "docs": {
            "Swagger UI": reverse('swagger-ui', request=request, format=format),
            "Redoc": reverse('redoc', request=request, format=format),
        }
    })


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user accounts.

    Provides serializers and permission logic depending on the action.
    Supports user registration, profile editing, catalogue retrieval,
    movie recommendations, and password reset/change operations.
    """

    queryset = User.objects.all().order_by('date_joined')
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    lookup_field = 'user_id'


    def get_queryset(self):  # type: ignore
        """
        Restrict visible users based on role.

        - Admins: can see all users.
        - Regular users: only see their own profile.
        """
        if self.request.user.is_staff:
            return User.objects.all().order_by('date_joined')
        return User.objects.filter(pk=self.request.user.pk)


    def get_serializer_class(self):  # type: ignore
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == "create":
            return RegisterUserSerializer
        if self.action in ["update", "partial_update", "retrieve"]:
            return UserDetailSerializer
        if self.action == "list":
            return UserLightSerializer
        if self.action in ["edit_profile", "view_catalogue"]:
            return UserProfileSerializer
        if self.action == "password_reset":
            return PasswordResetSerializer
        if self.action == "password_change":
            return PasswordChangeSerializer
        return super().get_serializer_class()


    def get_serializer_context(self):
        """
        Extend serializer context.

        Adds `include_tokens` flag during user creation.
        """
        context = super().get_serializer_context()
        if self.action == "create":
            context["include_tokens"] = True
        return context


    def get_permissions(self):
        """
        Return the appropriate permission classes based on the action.
        """
        if self.action in [
            "create", "password_change", "password_reset"]:
            permission_classes = [permissions.AllowAny]
        elif self.action in [
            "update", "partial_update", "destroy"]:
            permission_classes = [IsUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [perm() for perm in permission_classes]


    @extend_schema(
        responses={200: UserProfileSerializer},
        methods=["GET", "PUT", "PATCH"],
    )
    @action(
        detail=False,
        methods=["GET", "PUT", "PATCH"],
        serializer_class=UserProfileSerializer,
        permission_classes=[IsUser],
    )
    def edit_profile(self, request):
        """
        Retrieve or update the profile of the logged-in user.
        """
        profile = request.user.profile

        if request.method == "GET":
            serializer = self.get_serializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)

        partial = request.method == "PATCH"
        serializer = self.get_serializer(
            profile, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


    @extend_schema(
        responses={200: FavoriteMovieReadSerializer(many=True)},
    )
    @method_decorator(vary_on_headers("Authorization"))
    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[IsUser],
    )
    def view_catalogue(self, request):
        """
        Retrieve a list of the logged-in user's favorite movies.
        """
        catalogue = request.user.favorites.all()
        if not catalogue:
            return Response({
                "message":"Browse and add movies to your favorites. "\
                "Your catalogue is currently empty"}, 
                status=status.HTTP_200_OK)
        serializer = FavoriteMovieReadSerializer(catalogue, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


    @extend_schema(
        responses={200: MovieOutputSerializer(many=True)},
    )
    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[IsUser],
    )
    def recommended_movies(self, request):
        """
        Retrieve a list of movies recommended for the logged-in user.

        - If the user has favorite genres, recommendations are filtered
            based on those genres.
        - If no favorite genres exist, trending movies are returned instead.
        """
        fav_genres_set = set(
            request.user.profile.genres.all().values_list("id", flat=True)
        )
        movies = get_trending_movies().get('results' or []) or []

        recommended = []

        if fav_genres_set:
            for movie in movies:
                genre_ids = set(movie.get("genre_ids", []))
                if genre_ids & fav_genres_set:
                    recommended.append(movie)
        else:
            recommended = movies


        paginator = self.paginator
        page = paginator.paginate_queryset(recommended, request)  # type: ignore

        serializer = MovieOutputSerializer(
            page,
            many=True,
            context={"image_base_url": "https://image.tmdb.org/t/p/w500"},
        )
        response = paginator.get_paginated_response(serializer.data)  # type: ignore
        response.data["message"] = (
            "Personalized recommendations based on your favorite genres."
            if fav_genres_set
            else "Showing trending movies. Add favorite genres to get "
                    "personalized recommendations."
        )
        return response


    @extend_schema(
        request=PasswordResetSerializer,
        responses={
            200: OpenApiResponse(description="Returns token and uid"),
            404: OpenApiResponse(description="Resource not found"),
            400: OpenApiResponse(description="Bad request"),
        },
    )
    @action(
        detail=False,
        methods=["POST"]
        )
    def password_reset(self, request):
        """
        Handle password reset request.

        Generates a reset token and UID for a given email address.

        Current implementation not safe.
        """
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        value = serializer.validated_data["email"]  # type: ignore
        try:
            user = User.objects.get(email__iexact=value)
        except User.DoesNotExist:
            return Response(
                {"error": "Sorry, user not found!"},
                status=status.HTTP_404_NOT_FOUND,
            )

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # TODO, email service for sending emails to user email with token 
        # make a background task with celery

        return Response(
            {"message": "Check your email for reset token and valid uid"},
            status=status.HTTP_200_OK,
        )


    @extend_schema(
        request=PasswordChangeSerializer,
        responses={
            204: OpenApiResponse(description="Password reset successful"),
            400: OpenApiResponse(description="Error messages"),
        },
    )
    @action(
        detail=False,
        methods=["POST"]
        )
    def password_change(self, request):
        """
        Handle password change request.

        Verifies the reset token and updates the user's password.
        """
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data["uid"]  # type: ignore
        token = serializer.validated_data["token"]  # type: ignore
        new_password = serializer.validated_data["new_password"]  # type: ignore

        try:
            decoded_uid = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=decoded_uid)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": "Invalid user"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"error": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()
        return Response(
            {"message": "Password reset successful."},
            status=status.HTTP_204_NO_CONTENT,
        )


@extend_schema(
    responses=MovieOutputSerializer(many=True),
    description="Retrieve a list of movies from the cached TMDB API response.",
)
@cache_page(3600)
@api_view(["GET"])
def movie_list(request):
    """
    Retrieve a list of trending movies from TMDB.
    Results are cached for performance.
    """
    cache_key = "movies:trending:serialized"

    # Fetch serialized data from cache or serialize if cache is empty
    serialized_data = get_or_set_cache(
        cache_key,
        lambda: serialize_trending_movies(),
        serialize = False,
        timeout=60*60*24,  # 24 hours
    )

    paginator = StandardPagination()
    page = paginator.paginate_queryset(serialized_data, request)
    return paginator.get_paginated_response(page)


@extend_schema(
    description="Retrieve details of a single movie by its TMDB ID.",
    responses={
        200: MovieOutputSerializer,
        404: OpenApiResponse(description="Movie not found"),
    },
)
@cache_page(3600)
@api_view(["GET"])
def movie_detail(request, movie_id: int):
    """
    Retrieve details of a movie by TMDB ID.
    """
    movie = get_movie_by_id(movie_id) # type: ignore

    if not movie:
        return Response(
            {"detail": "Sorry, movie not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = MovieOutputSerializer(
        movie,
        context={"image_base_url": "https://image.tmdb.org/t/p/w500"},
    )
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    description="Add a movie to the current user's favorites.",
    request=FavoriteMovieWriteSerializer,
    responses={
        201: FavoriteMovieReadSerializer,
        400: OpenApiResponse(description="Validation errors"),
    },
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def favorite_movie(request, movie_id: int):
    """
    Add a given movie to the current user's list of favorites.
    """
    serializer = FavoriteMovieWriteSerializer(
        data={"movie_id": movie_id},
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)

    favorite = serializer.save()
    read_serializer = FavoriteMovieReadSerializer(
        favorite,
        context={"request": request},
    )
    return Response(
        {
        'message':'Movie Added to favorites',
        'data':read_serializer.data
        }, 
            status=status.HTTP_201_CREATED
            )


@extend_schema(
    description="Remove a movie from the authenticated user's favorites catalogue.",
    responses={
        204: OpenApiResponse(description="Movie successfully removed"),
        404: OpenApiResponse(description="Movie not found in catalogue"),
    },
)
@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def remove_favorite(request, movie_id: int):
    """
    Remove a given movie from the user's favorite catalogue.
    """
    movie = FavoriteMovie.objects.filter(
        movie_id=movie_id,
        favorited_by=request.user
    ).first()

    if not movie:
        return Response(
            {"detail": "Movie not found in your catalogue."},
            status=status.HTTP_404_NOT_FOUND
        )

    movie.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    description="Search movies in TMDB by keyword or title.",
    parameters=[
        OpenApiParameter(
            name="q",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Search query string (movie title or keyword)",
        ),
        OpenApiParameter(
            name="page",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Page number for paginated results (default: 1)",
        ),
    ],
    responses={200: MovieOutputSerializer(many=True)},
)
@cache_page(timeout=3600)
@api_view(["GET"])
def search_movie(request):
    """
    Search TMDB for movies by query string.
    Supports pagination.
    """
    search_query = request.GET.get("q")
    page_num = int(request.GET.get("page", 1))
    paginator = StandardPagination()

    if not search_query:
        return Response(
            {"error": "Query parameter 'q' is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = search_movies_from_tmdb(search_query, page=page_num)

    if "error" in data:
        return Response(
            {"error": data["error"]},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    page = paginator.paginate_queryset(data.get("results", []), request)
    serializer = MovieOutputSerializer(
        page,
        many=True,
        context={"image_base_url": "https://image.tmdb.org/t/p/w500"},
    )
    if not serializer.data:
        return Response({"message":f"Movie: {search_query} Not found"}, status=status.HTTP_404_NOT_FOUND)
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    description="Retrieve list of available movie genres.",
    responses={200: GenreSerializer(many=True)},
)
@cache_page(timeout=3600)
@api_view(["GET"])
def genre_list(request):
    """
    Retrieve all available movie genres.
    """
    genres = Genre.objects.all().order_by("name")
    paginator = StandardPagination()
    page = paginator.paginate_queryset(genres, request)
    serializer = GenreSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


# NOTE: not necessary or within project scope
from api.serializers import GeneralSerializer
@extend_schema(
    description="Return an api key for services to access some protected views",
    responses={
        200:OpenApiResponse(description='returns api key to be used')
    }
)
@api_view(["POST"])
def get_api_key(request):
    """
    Generate API key for server-side clients (one-time view).
    """
    serializer = GeneralSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    service_name = serializer.validated_data["service_name"] # type: ignore

    api_key, key = ServiceAPIKey.objects.create_key(name=service_name) # type: ignore

    return Response(
        {
            "message": "API key created successfully",
            "name": service_name,
            "api_key": key,
        },
        status=status.HTTP_201_CREATED,
    )
