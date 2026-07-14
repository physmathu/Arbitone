"""
Converts a NOAA point forecast (a single predicted high temp) into a
probability that the actual high will be >= some threshold, using a normal
distribution centered on the forecast.
 
This is a deliberately simple starting model -- NOAA's point forecast isn't
a probability distribution, so we're assuming errors are normally distributed
around it with a fixed std dev (configurable in config.py). A real version
of this should eventually calibrate that std dev against historical
forecast-vs-actual error for each city/season, and ideally pull NOAA's
ensemble/probabilistic products instead of just the point forecast.
"""
 
import math
 
from .config import FORECAST_STD_DEV_F
 
 
def prob_high_at_or_above(forecast_high_f: float, threshold_f: float,
                           std_dev_f: float = FORECAST_STD_DEV_F) -> float:
    """
    Returns P(actual high >= threshold_f) given a forecast centered at
    forecast_high_f, assuming normally distributed forecast error.
    """
    z = (threshold_f - forecast_high_f) / std_dev_f
    # P(X >= threshold) = 1 - CDF(z) = 0.5 * erfc(z / sqrt(2))
    return 0.5 * math.erfc(z / math.sqrt(2))
 
 
def prob_high_in_range(forecast_high_f: float, low_f: float, high_f: float,
                        std_dev_f: float = FORECAST_STD_DEV_F) -> float:
    """Returns P(low_f <= actual high <= high_f) -- for Kalshi's banded contracts."""
    p_above_low = prob_high_at_or_above(forecast_high_f, low_f, std_dev_f)
    p_above_high = prob_high_at_or_above(forecast_high_f, high_f, std_dev_f)
    return p_above_low - p_above_high
 
 
def prob_high_below(forecast_high_f: float, threshold_f: float,
                     std_dev_f: float = FORECAST_STD_DEV_F) -> float:
    """
    Returns P(actual high < threshold_f) -- for Kalshi's "less than" /
    cap_strike contracts (strike_type == "less"), as opposed to the
    "greater than" / floor_strike contracts (strike_type == "greater")
    that prob_high_at_or_above handles.
    """
    return 1.0 - prob_high_at_or_above(forecast_high_f, threshold_f, std_dev_f)
 
 
def prob_yes_for_market(forecast_high_f: float, threshold_f: float, strike_type: str,
                         std_dev_f: float = FORECAST_STD_DEV_F) -> float:
    """
    Dispatches to the right probability function based on Kalshi's
    strike_type field ("greater" -> floor_strike markets, "less" ->
    cap_strike markets). This is the function live_run.py should call.
    """
    if strike_type == "greater":
        return prob_high_at_or_above(forecast_high_f, threshold_f, std_dev_f)
    elif strike_type == "less":
        return prob_high_below(forecast_high_f, threshold_f, std_dev_f)
    else:
        raise ValueError(f"Unhandled strike_type: {strike_type!r} (expected 'greater' or 'less')")
