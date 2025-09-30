from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from api import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="users")

app_name = "api"

urlpatterns = [
    # Router endpoints - Users
    path("", include(router.urls)),

    # Movie endpoints
    path("movies/", views.movie_list, name="movies-list"),
    path("movies/<int:movie_id>/", views.movie_detail, name="movie-detail"),
    path(
        "movies/<int:movie_id>/favorite_movie/",
        views.favorite_movie,
        name="add-movie-favorite",
    ),
    path(
        "movies/<int:movie_id>/remove_favorite/",
        views.remove_favorite,
        name="remove-favorite-movie"
    ),
    path("movies/search/", views.search_movie, name="search-movie"),

    # Genre endpoints
    path("genres/", views.genre_list, name="genre-list"),

    # Authentication endpoints (JWT)
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    #NOTE: api key for future versions
    path("token/retrieve_api_key/", views.get_api_key, name='get-api-key'),
]
