from django.urls import path
from .views import morpho_analyzer, analyze_word_api

urlpatterns = [

    path('', morpho_analyzer, name='morpho_analyzer'),

    path('api/analyze/', analyze_word_api, name='analyze_word_api'), 
    
]