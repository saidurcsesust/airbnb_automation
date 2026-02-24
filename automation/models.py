from django.db import models


class TestResult(models.Model):
    test_case = models.CharField(max_length=255)
    url = models.URLField(max_length=2048)
    passed = models.BooleanField(default=False)
    comment = models.TextField(blank=True)

    class Meta:
        db_table = "testing"
        verbose_name = "Test Result"
        verbose_name_plural = "Test Results"

    def __str__(self):
        return f"{self.test_case} ({'PASS' if self.passed else 'FAIL'})"


class ListingData(models.Model):
    title = models.CharField(max_length=512)
    price = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(max_length=2048, blank=True)
    listing_url = models.URLField(max_length=2048, blank=True)
    scraped_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "listing_data"
        verbose_name = "Listing"
        verbose_name_plural = "Listings"

    def __str__(self):
        return self.title[:80]


class SuggestionData(models.Model):
    text = models.CharField(max_length=512)
    search_query = models.CharField(max_length=255)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "suggestion_data"
        verbose_name = "Suggestion"
        verbose_name_plural = "Suggestions"

    def __str__(self):
        return self.text[:80]


class NetworkLog(models.Model):
    METHOD_CHOICES = [
        ("GET", "GET"),
        ("POST", "POST"),
        ("PUT", "PUT"),
        ("DELETE", "DELETE"),
        ("PATCH", "PATCH"),
        ("OPTIONS", "OPTIONS"),
    ]

    url = models.URLField(max_length=2048)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default="GET")
    status_code = models.IntegerField(null=True, blank=True)
    resource_type = models.CharField(max_length=50, blank=True)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "network_logs"
        verbose_name = "Network Log"
        verbose_name_plural = "Network Logs"


class ConsoleLog(models.Model):
    LEVEL_CHOICES = [
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
        ("DEBUG", "Debug"),
    ]

    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="INFO")
    message = models.TextField()
    source = models.CharField(max_length=512, blank=True)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "console_logs"
        verbose_name = "Console Log"
        verbose_name_plural = "Console Logs"
