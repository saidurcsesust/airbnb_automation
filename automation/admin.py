from django.contrib import admin
from .models import (
    TestRun, TestCase, AutoSuggestion, SelectedDates,
    GuestSelection, SearchListing, ListingDetail, NetworkLog, ConsoleLog,
)


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 0
    readonly_fields = ("step_number", "step_name", "status", "message", "screenshot_path", "executed_at", "duration_ms")


class AutoSuggestionInline(admin.TabularInline):
    model = AutoSuggestion
    extra = 0
    readonly_fields = ("position", "text", "has_map_icon", "is_selected")


class SearchListingInline(admin.TabularInline):
    model = SearchListing
    extra = 0
    readonly_fields = ("position", "title", "price", "image_url", "listing_url", "is_selected")


class NetworkLogInline(admin.TabularInline):
    model = NetworkLog
    extra = 0
    readonly_fields = ("url", "method", "status_code", "resource_type", "step_name", "logged_at")


class ConsoleLogInline(admin.TabularInline):
    model = ConsoleLog
    extra = 0
    readonly_fields = ("log_type", "message", "step_name", "logged_at")


@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    list_display = ("pk", "status", "selected_country", "selected_suggestion", "checkin_date", "checkout_date", "guest_count", "is_mobile", "started_at")
    list_filter = ("status", "is_mobile")
    readonly_fields = ("started_at", "finished_at")
    inlines = [TestCaseInline, AutoSuggestionInline, SearchListingInline, NetworkLogInline, ConsoleLogInline]


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ("test_run", "step_number", "step_name", "status", "duration_ms", "executed_at")
    list_filter = ("status",)
    search_fields = ("step_name", "message")


@admin.register(SearchListing)
class SearchListingAdmin(admin.ModelAdmin):
    list_display = ("test_run", "position", "title", "price", "is_selected")


@admin.register(ListingDetail)
class ListingDetailAdmin(admin.ModelAdmin):
    list_display = ("test_run", "title", "subtitle", "page_url")


@admin.register(NetworkLog)
class NetworkLogAdmin(admin.ModelAdmin):
    list_display = ("test_run", "method", "status_code", "resource_type", "step_name", "logged_at")
    list_filter = ("method", "status_code", "resource_type")


@admin.register(ConsoleLog)
class ConsoleLogAdmin(admin.ModelAdmin):
    list_display = ("test_run", "log_type", "message", "step_name", "logged_at")
    list_filter = ("log_type",)
