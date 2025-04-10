from django.contrib import admin
from django.urls import path, include
from generator.views import home, generate_game_view, game_detail, favorites, toggle_favorite, export_pdf
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('', home, name='home'),
    path('generate/', generate_game_view, name='generate_game'),
    path('game/<int:game_id>/', game_detail, name='game_detail'),
    path('favorites/', favorites, name='favorites'),
    path('api/toggle-favorite/<int:game_id>/', toggle_favorite, name='toggle_favorite'),
    path('api/export-pdf/<int:game_id>/', export_pdf, name='export_pdf'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Ajout des fichiers statiques en développement
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
