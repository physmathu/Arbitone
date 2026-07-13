"""
Thin client around the NOAA/National Weather Service API.

NOAA's API is free, public, and requires no API key -- just a descriptive
User-Agent header identifying your app (they ask for a contact email/URL).

Docs: https://www.weather.gov/documentation/services-web-api
"""

import requests
from dataclasses import dataclass
from datetime import date

from .config import NOAA_BASE_URL, NOAA_USER_AGENT


@dataclass
class DailyForecast:
    forecast_date: date
    high_temp_f: float
    short_forecast: str  # e.g. "Sunny", "Chance Showers"


class NOAAClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": NOAA_USER_AGENT,
            "Accept": "application/geo+json",
        })

    def _get_grid_forecast_url(self, lat: float, lon: float) -> str:
        """NOAA requires resolving lat/lon -> a forecast grid endpoint first."""
        resp = self.session.get(f"{NOAA_BASE_URL}/points/{lat},{lon}", timeout=10)
        resp.raise_for_status()
        return resp.json()["properties"]["forecast"]

    def get_daily_high_forecast(self, lat: float, lon: float, target_date: date) -> DailyForecast | None:
        """
        Returns the forecasted daytime high temperature for target_date, or
        None if that date isn't in the current forecast window (NOAA only
        forecasts ~7 days out).
        """
        forecast_url = self._get_grid_forecast_url(lat, lon)
        resp = self.session.get(forecast_url, timeout=10)
        resp.raise_for_status()
        periods = resp.json()["properties"]["periods"]

        for period in periods:
            # NOAA returns periods like "Today", "Tonight", "Monday", "Monday Night"
            # We want the daytime period matching target_date.
            period_date = date.fromisoformat(period["startTime"][:10])
            if period_date == target_date and period["isDaytime"]:
                return DailyForecast(
                    forecast_date=target_date,
                    high_temp_f=float(period["temperature"]),
                    short_forecast=period["shortForecast"],
                )
        return None
