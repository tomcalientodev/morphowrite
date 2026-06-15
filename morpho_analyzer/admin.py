from django.contrib import admin
from .models import CachedMorphoAnalysis

@admin.register(CachedMorphoAnalysis)
class CachedMorphoAnalysisAdmin(admin.ModelAdmin):
    # Columns to show in the spreadsheet view list
    list_display = ('word', 'created_at')
    
    # Adds a functional search bar to quickly lookup cached words
    search_fields = ('word',)
    
    # Adds a sidebar filter to sort entries by date created
    list_filter = ('created_at',)
    
    # Makes the creation timestamp read-only so it can't be accidentally altered
    readonly_fields = ('created_at',)