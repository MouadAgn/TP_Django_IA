from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GameGeneratorViewSet

router = DefaultRouter()
router.register(r'games', GameGeneratorViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 