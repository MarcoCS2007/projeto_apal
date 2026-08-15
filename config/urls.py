"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.usuarios.urls")),
    path("api/", include("apps.licenciamento.urls")),
    path("api/", include("apps.fiscalizacao.urls")),
    path("api/", include("apps.assistente.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.usuarios.urls_web")),
    path("", include("apps.licenciamento.urls_web")),
    path("", include("apps.espacos.urls_web")),
    path("", include("apps.assistente.urls_web")),
    path("relatorios/", include("apps.relatorios.urls")),
]

handler404 = "apps.core.views.pagina_nao_encontrada"
handler500 = "apps.core.views.erro_servidor"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
