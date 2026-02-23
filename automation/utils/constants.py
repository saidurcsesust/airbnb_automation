"""Static data and shared constants for the Airbnb automation."""

AIRBNB_URL = "https://www.airbnb.com/"

TOP_20_COUNTRIES = [
    "United States",
    "China",
    "India",
    "Brazil",
    "Russia",
    "Indonesia",
    "Pakistan",
    "Nigeria",
    "Bangladesh",
    "Mexico",
    "Ethiopia",
    "Japan",
    "Philippines",
    "Egypt",
    "DR Congo",
    "Vietnam",
    "Iran",
    "Turkey",
    "Germany",
    "Thailand",
]

# Playwright viewport for desktop
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}

# Playwright device descriptor for mobile (iPhone 13)
MOBILE_DEVICE = {
    "viewport": {"width": 390, "height": 844},
    "user_agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
        "Mobile/15E148 Safari/604.1"
    ),
    "device_scale_factor": 3,
    "is_mobile": True,
    "has_touch": True,
}
