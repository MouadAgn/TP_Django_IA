from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GameGeneratorViewSet, home, generate_game_view, game_detail

# Configuration des routes API
router = DefaultRouter()
router.register(r'games', GameGeneratorViewSet, basename='game')

app_name = 'generator'

urlpatterns = [
    # Routes Frontend
    path('', home, name='home'),
    path('generate/', generate_game_view, name='generate_game'),
    path('game/<int:game_id>/', game_detail, name='game_detail'),
    path('api/games/generate_game/', GameGeneratorViewSet.as_view({'post': 'generate_game'}), name='generate_game_api'),
]

# Ajout des URLs de l'API
urlpatterns += router.urls 