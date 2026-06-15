
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('morphowrite-hq/', admin.site.urls),
    path('', include('core.urls')),
    path('morpho-analyzer/', include('morpho_analyzer.urls')),
]
