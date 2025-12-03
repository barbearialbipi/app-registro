from django.contrib import admin
from django.urls import path
from core.views import home  # Importamos a tua view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),  # URL vazia = Página Inicial
]