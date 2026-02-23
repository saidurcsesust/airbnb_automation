from django.db import models


class TestRun(models.Model):
    """Represents a single end-to-end automation run."""

    STATUS_CHOICES = [
        ("running", "Running"),
        ("passed", "Passed"),
        ("failed", "Failed"),
    ]

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    selected_country = models.CharField(max_length=100, blank=True)
    selected_suggestion = models.CharField(max_length=255, blank=True)
    checkin_date = models.CharField(max_length=50, blank=True)
    checkout_date = models.CharField(max_length=50, blank=True)
    selected_month = models.CharField(max_length=50, blank=True)
    guest_count = models.IntegerField(null=True, blank=True)
    is_mobile = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"TestRun #{self.pk} - {self.status} ({self.started_at:%Y-%m-%d %H:%M})"


class TestCase(models.Model):
    """Represents an individual step/test-case within a TestRun."""

    STATUS_CHOICES = [
        ("passed", "Passed"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    test_run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name="test_cases")
    step_number = models.IntegerField()
    step_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    message = models.TextField(blank=True)
    screenshot_path = models.CharField(max_length=500, blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)
    duration_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["step_number"]

    def __str__(self):
        return f"Step {self.step_number}: {self.step_name} [{self.status}]"


class AutoSuggestion(models.Model):
    """Stores auto-suggestion items captured during search."""

    test_run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name="suggestions")
    text = models.CharField(max_length=500)
    has_map_icon = models.BooleanField(default=False)
    position = models.IntegerField()
    is_selected = models.BooleanField(default=False)

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return f"Suggestion [{self.position}]: {self.text}"


class SelectedDates(models.Model):
    """Stores the dates selected in the date picker."""

    test_run = models.OneToOneField(TestRun, on_delete=models.CASCADE, related_name="selected_dates")
    month_name = models.CharField(max_length=50)
    checkin_date = models.CharField(max_length=50)
    checkout_date = models.CharField(max_length=50)
    next_month_clicks = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.checkin_date} → {self.checkout_date} ({self.month_name})"


class GuestSelection(models.Model):
    """Stores guest picker selections."""

    test_run = models.OneToOneField(TestRun, on_delete=models.CASCADE, related_name="guest_selection")
    adults = models.IntegerField(default=0)
    children = models.IntegerField(default=0)
    infants = models.IntegerField(default=0)
    pets = models.IntegerField(default=0)
    total_guests = models.IntegerField(default=0)

    def __str__(self):
        return f"Guests: {self.total_guests} (A:{self.adults} C:{self.children} I:{self.infants} P:{self.pets})"


class SearchListing(models.Model):
    """Stores listing data scraped from the search results page."""

    test_run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name="listings")
    title = models.TextField(blank=True)
    price = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(max_length=1000, blank=True)
    listing_url = models.URLField(max_length=1000, blank=True)
    position = models.IntegerField()
    is_selected = models.BooleanField(default=False)

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return f"Listing [{self.position}]: {self.title[:60]}"


class ListingDetail(models.Model):
    """Stores details captured from an individual listing page."""

    test_run = models.OneToOneField(TestRun, on_delete=models.CASCADE, related_name="listing_detail")
    title = models.TextField(blank=True)
    subtitle = models.TextField(blank=True)
    image_urls = models.JSONField(default=list)
    page_url = models.URLField(max_length=1000, blank=True)

    def __str__(self):
        return f"Detail: {self.title[:80]}"


class NetworkLog(models.Model):
    """Stores captured network requests/responses."""

    test_run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name="network_logs")
    url = models.URLField(max_length=2000)
    method = models.CharField(max_length=10, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    resource_type = models.CharField(max_length=50, blank=True)
    step_name = models.CharField(max_length=255, blank=True)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["logged_at"]

    def __str__(self):
        return f"[{self.status_code}] {self.method} {self.url[:80]}"


class ConsoleLog(models.Model):
    """Stores browser console messages."""

    LOG_TYPES = [
        ("log", "Log"),
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
        ("debug", "Debug"),
    ]

    test_run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name="console_logs")
    log_type = models.CharField(max_length=20, choices=LOG_TYPES, default="log")
    message = models.TextField()
    step_name = models.CharField(max_length=255, blank=True)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["logged_at"]

    def __str__(self):
        return f"[{self.log_type.upper()}] {self.message[:100]}"
