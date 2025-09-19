from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
import api.views as v

router = DefaultRouter()
router.register(r'users', v.UserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('movies/', v.movie_list, name='movies-list'),
    path('movies/<int:movie_id>/', v.movie_detail, name='movie-detail'),
    path('movies/<int:movie_id>/favorite_movie/', v.favorite_movie, name='add-movie-favorite'),
    path('genres/', v.genre_list, name='genre-list'),

    #token obtain
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]