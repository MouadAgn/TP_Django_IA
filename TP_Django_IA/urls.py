from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('', include('generator.urls')),
    path('users/', include('users.urls')),
    path('api/', include('generator.urls')),  # Notre API de génération de jeux
]
