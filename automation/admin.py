from django.contrib import admin
from .models import TestResult, ListingData, SuggestionData, NetworkLog, ConsoleLog


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'test_case', 'url', 'passed', 'comment')
    list_filter = ('passed', 'test_case')
    search_fields = ('test_case', 'url', 'comment')
    list_per_page = 25
    ordering = ('-id',)

    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(ListingData)
class ListingDataAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'price', 'scraped_at')
    search_fields = ('title',)
    list_per_page = 25
    ordering = ('-scraped_at',)


@admin.register(SuggestionData)
class SuggestionDataAdmin(admin.ModelAdmin):
    list_display = ('id', 'search_query', 'text', 'captured_at')
    search_fields = ('search_query', 'text')
    list_per_page = 25
    ordering = ('-captured_at',)


@admin.register(NetworkLog)
class NetworkLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'method', 'url', 'status_code', 'resource_type', 'captured_at')
    list_filter = ('method', 'status_code')
    search_fields = ('url',)
    list_per_page = 50
    ordering = ('-captured_at',)


@admin.register(ConsoleLog)
class ConsoleLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'level', 'message', 'source', 'captured_at')
    list_filter = ('level',)
    search_fields = ('message',)
    list_per_page = 50
    ordering = ('-captured_at',)
