from django.contrib.auth import get_user_model
from rest_framework import permissions, viewsets, status, views
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiResponse

from api.models import Genre
from api.serializers import (
    FavoriteMovieReadSerializer, FavoriteMovieWriteSerializer, GenreSerializer,
    MovieOutputSerializer,
    RegisterUserSerializer, UserDetailSerializer, UserLightSerializer,
    UserProfileSerializer
)
from api.utils import IsUser, StandardPagination

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination


    def get_queryset(self):  # type: ignore
        """
        Limit users visible to non-admins.
        Admins can see all users.
        Regular users only see themselves.
        """
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(pk=self.request.user.pk)


    def get_serializer_class(self):  # type: ignore
        if self.action == 'create':
            return RegisterUserSerializer
        if self.action in ['update', 'partial_update', 'retrieve']:
            return UserDetailSerializer
        if self.action == 'list':
            return UserLightSerializer
        if self.action in ['edit_profile', 'view_catalogue']:
            return UserProfileSerializer
        return super().get_serializer_class()
    

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'create':
            context['include_tokens'] = True
        return context


    def get_permissions(self):
        if self.action in ['create', 'list']:
            permission_classes = [permissions.AllowAny]
        elif self.action in [
            'update', 'partial_update', 'destroy',
            'edit_profile', 'view_catalogue']:
            permission_classes = [IsUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [perm() for perm in permission_classes]


    @extend_schema(
        responses={200: UserProfileSerializer},
        methods=["GET", "PUT", "PATCH"]
    )
    @action(detail=False, methods=['GET', 'PUT', 'PATCH'],
            serializer_class=UserProfileSerializer,
            permission_classes=[permissions.IsAuthenticated])
    def edit_profile(self, request):
        """
        Retrieve or update the profile of the logged-in user.
        """
        profile = request.user.profile

        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)

        partial = request.method == 'PATCH'
        serializer = self.get_serializer(profile, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @extend_schema(
        responses={200: FavoriteMovieReadSerializer},
        methods=["GET"]
    )
    @action(detail=False, methods=['GET'],
            permission_classes=[permissions.IsAuthenticated])
    def view_catalogue(self, request):
        """
        Retrieve a list of the logged-in user's favorite movies.
        """
        catalogue = request.user.favorites.all()
        serializer = FavoriteMovieReadSerializer(catalogue, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

    @extend_schema(
            responses={200: MovieOutputSerializer(many=True)},
            methods=["GET"]
    )
    @action(detail=False, methods=['GET'],
            permission_classes=[permissions.IsAuthenticated])
    def recommended_movies(self, request):
        """
        Retrieve a list of movies recommended based on user's favorite genres
        """


        fav_genres_set = set(request.user.profile.genres.all().values_list('id', flat=True))
        movies = get_trending_movies(max_pages=5).get('results', []) or []

        recommended = []

        if fav_genres_set:
            for movie in movies:
                genre_ids = set(movie.get('genre_ids', []))
                if genre_ids and fav_genres_set:
                    recommended.append(movie)
        else:
            recommended = movies


        paginator = self.paginator
        page = paginator.paginate_queryset(recommended, request) # type: ignore

        serializer = MovieOutputSerializer(
            page,
            many=True,
            context={"image_base_url": "https://image.tmdb.org/t/p/w500"}
        )
        response = paginator.get_paginated_response(serializer.data) # type: ignore
        response.data['message'] = (
            "Personalized recommendations based on your favorite genres."
            if fav_genres_set
            else "Showing trending movies. Add favorite genres to get personalized recommendations.")
        return response

@extend_schema(
    responses=MovieOutputSerializer(many=True),
    description="Retrieve a list of movies from the cached TMDB API response."
)
@api_view(['GET'])
def movie_list(request):
    results = get_trending_movies()['results']
    paginator = StandardPagination()
    page = paginator.paginate_queryset(results, request)
    serializer = MovieOutputSerializer(
        page,
        many=True,
        context={"image_base_url":"https://image.tmdb.org/t/p/w500"}
    )
    return paginator.get_paginated_response(serializer.data)


from api.utils import get_movie_by_id
from api.movie_data_redis import get_trending_movies
@extend_schema(
    description="Retrieve details of a single movie by its TMDB ID",
    responses={
        200: MovieOutputSerializer,
        404: OpenApiResponse(description="Movie not found"),
    }
)
@api_view(['GET'])
def movie_detail(request, movie_id:int):
    movie = get_movie_by_id(
        movie_id, results=get_trending_movies(max_pages=4)['results'])
    if not movie:
        return Response(
            {"detail": "Sorry, movie not found"},
            status=status.HTTP_404_NOT_FOUND)
    serializer = MovieOutputSerializer(
        movie,
        context={"image_base_url":"https://image.tmdb.org/t/p/w500"}
        )
    return Response(
        serializer.data,
        status=status.HTTP_200_OK
    )


@extend_schema(
    description="Add a movie to the current user's favorites.",
    request=FavoriteMovieWriteSerializer,
    responses={
        201: FavoriteMovieReadSerializer,
        400: OpenApiResponse(description="Validation errors"),
    },
)
@api_view(['POST'])
def favorite_movie(request, movie_id: int):
    serializer = FavoriteMovieWriteSerializer(
        data={"movie_id": movie_id},
        context={"request": request},
    )

    if serializer.is_valid():
        favorite = serializer.save()
        read_serializer = FavoriteMovieReadSerializer(favorite, context={"request": request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    description="Retrieve list of available movie genres",
    responses={
        200: GenreSerializer(many=True)
    }
)
@api_view(['GET'])
def genre_list(request):

    genres = Genre.objects.all()
    paginator = StandardPagination()
    page = paginator.paginate_queryset(genres, request)
    serializer = GenreSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


class MoviesView(views.APIView):
    pass 