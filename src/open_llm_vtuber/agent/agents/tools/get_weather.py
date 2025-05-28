import os
import json
import requests
from datetime import datetime, timedelta

AMAP_API_KEY = "ee170d9927962ec572636358acd61d53"

def get_location_adcode(location: str):
    geo_url = f"https://restapi.amap.com/v3/geocode/geo?key={AMAP_API_KEY}&address={location}"
    try:
        response = requests.get(geo_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "1" and data["geocodes"]:
            return data["geocodes"][0]["adcode"]
        return None
    except:
        return None

def get_current_temperature(location: str, unit: str = "celsius"):
    adcode = get_location_adcode(location)
    if not adcode:
        return {"error": f"Location '{location}' not found or failed to get adcode."}

    weather_url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={AMAP_API_KEY}&city={adcode}&extensions=base"
    try:
        response = requests.get(weather_url, timeout=5)
        data = response.json()
        if data["status"] == "1" and data.get("lives"):
            live_weather = data["lives"][0]
            temp_c = float(live_weather.get("temperature"))
            temperature = temp_c if unit == "celsius" else temp_c * 9 / 5 + 32
            return {
                "temperature": round(temperature, 1),
                "weather": live_weather.get("weather"),
                "humidity": live_weather.get("humidity"),
                "wind_direction": live_weather.get("winddirection"),
                "wind_power": live_weather.get("windpower"),
                "location": location,
                "unit": unit,
                "report_time": live_weather.get("reporttime")
            }
        return {"error": "Weather data unavailable."}
    except:
        return {"error": "API request failed"}

def get_temperature_date(location: str, date: str, unit: str = "celsius"):
    adcode = get_location_adcode(location)
    if not adcode:
        return {"error": f"Location '{location}' not found or failed to get adcode."}

    forecast_url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={AMAP_API_KEY}&city={adcode}&extensions=all"
    dates_to_query = []
    today = datetime.now()

    if date == "明天":
        dates_to_query.append((today + timedelta(days=1)).strftime("%Y-%m-%d"))
    elif date.startswith("未来"):
        num_days = 2 if "两" in date else int("".join([c for c in date if c.isdigit()]) or 0)
        for i in range(1, min(num_days, 7) + 1):
            dates_to_query.append((today + timedelta(days=i)).strftime("%Y-%m-%d"))
    else:
        try:
            datetime.strptime(date, "%Y-%m-%d")
            dates_to_query.append(date)
        except:
            return {"error": f"Invalid date format: {date}"}

    try:
        response = requests.get(forecast_url, timeout=10)
        data = response.json()
        if data["status"] == "1" and data.get("forecasts"):
            forecasts = data["forecasts"][0].get("casts", [])
            results = []
            for qd in dates_to_query:
                forecast = next((f for f in forecasts if f.get("date") == qd), None)
                if forecast:
                    temp_day = float(forecast.get("daytemp"))
                    temp_night = float(forecast.get("nighttemp"))
                    if unit == "fahrenheit":
                        temp_day = temp_day * 9 / 5 + 32
                        temp_night = temp_night * 9 / 5 + 32
                    results.append({
                        "location": location,
                        "date": qd,
                        "day_temperature": round(temp_day, 1),
                        "night_temperature": round(temp_night, 1),
                        "unit": unit,
                        "day_weather": forecast.get("dayweather"),
                        "night_weather": forecast.get("nightweather"),
                        "day_wind_direction": forecast.get("daywind"),
                        "day_wind_power": forecast.get("daypower"),
                        "night_wind_direction": forecast.get("nightwind"),
                        "night_wind_power": forecast.get("nightpower"),
                    })
                else:
                    results.append({"date": qd, "error": "No forecast data found."})
            return results[0] if len(results) == 1 else results
        return {"error": "Forecast data unavailable."}
    except:
        return {"error": "API request failed"}
