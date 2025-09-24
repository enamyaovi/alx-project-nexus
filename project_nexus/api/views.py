from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)

from rest_framework import permissions, status, viewsets, views
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from api.models import Genre
from api.movie_data_redis import get_trending_movies, search_movies_from_tmdb
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
from api.utils import IsUser, StandardPagination, get_movie_by_id

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user accounts.

    Provides serializers and permission logic depending on the action.
    Supports user registration, profile editing, catalogue retrieval,
    movie recommendations, and password reset/change operations.
    """

    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination


    def get_queryset(self):  # type: ignore
        """
        Restrict visible users based on role.

        - Admins: can see all users.
        - Regular users: only see their own profile.
        """
        if self.request.user.is_staff:
            return User.objects.all()
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
        if self.action in ["create", "list"]:
            permission_classes = [permissions.AllowAny]
        elif self.action in [
            "update",
            "partial_update",
            "destroy",
            "edit_profile",
            "view_catalogue",
        ]:
            permission_classes = [IsUser]
        elif self.action in ["password_reset", "password_change"]:
            permission_classes = [permissions.AllowAny]
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
        permission_classes=[permissions.IsAuthenticated],
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
        serializer.is_valid(raise_exceptions=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


    @extend_schema(
        responses={200: FavoriteMovieReadSerializer(many=True)},
    )
    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def view_catalogue(self, request):
        """
        Retrieve a list of the logged-in user's favorite movies.
        """
        catalogue = request.user.favorites.all()
        serializer = FavoriteMovieReadSerializer(catalogue, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


    @extend_schema(
        responses={200: MovieOutputSerializer(many=True)},
    )
    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[permissions.IsAuthenticated],
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
        movies = get_trending_movies(max_pages=5).get("results", []) or []

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
        methods=["POST"],
        permission_classes=[permissions.AllowAny],
    )
    def password_reset(self, request):
        """
        Handle password reset request.

        Generates a reset token and UID for a given email address.
        """
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]  # type: ignore
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Sorry, user not found!"},
                status=status.HTTP_404_NOT_FOUND,
            )

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        #will implement email service for sending emails to user email

        return Response(
            {"uid": uid, "token": token},
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
        methods=["POST"],
        permission_classes=[permissions.AllowAny],
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
@api_view(["GET"])
def movie_list(request):
    """
    Retrieve a list of trending movies from TMDB.
    Results are cached for performance.
    """
    results = get_trending_movies().get("results", [])
    paginator = StandardPagination()
    page = paginator.paginate_queryset(results, request)
    serializer = MovieOutputSerializer(
        page,
        many=True,
        context={"image_base_url": "https://image.tmdb.org/t/p/w500"},
    )
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    description="Retrieve details of a single movie by its TMDB ID.",
    responses={
        200: MovieOutputSerializer,
        404: OpenApiResponse(description="Movie not found"),
    },
)
@api_view(["GET"])
def movie_detail(request, movie_id: int):
    """
    Retrieve details of a movie by TMDB ID.
    """
    movie = get_movie_by_id(
        movie_id,
        results=get_trending_movies(max_pages=4).get("results", []),
    )
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
    return Response(read_serializer.data, status=status.HTTP_201_CREATED)


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
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    description="Retrieve list of available movie genres.",
    responses={200: GenreSerializer(many=True)},
)
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