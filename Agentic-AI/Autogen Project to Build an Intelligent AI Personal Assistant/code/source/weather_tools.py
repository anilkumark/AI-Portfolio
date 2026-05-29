import httpx
import pytz
from datetime import datetime
from typing import Tuple, Dict, Any, List
from autogen_core.tools import FunctionTool
from source.log_records import logger
from source.configurations import config

class WeatherTools:
    """Single class handling all weather operations - API calls and tool functions."""
    
    def __init__(self):
        self.OPEN_METEO_URL = config.OPEN_METEO_URL
        self.NOMINATIM_URL = config.NOMINATIM_URL
        self.WEATHER_CODE_DESC: Dict[int, str] = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
            55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            66: "Light freezing rain", 67: "Heavy freezing rain", 71: "Slight snow fall",
            73: "Moderate snow fall", 75: "Heavy snow fall", 77: "Snow grains",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            85: "Slight snow showers", 86: "Heavy snow showers", 95: "Thunderstorm",
            96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        self.default_timezone = config.DEFAULT_TIMEZONE

    
    async def get_current_datetime(self) -> str:
        """Get current date and time in the configured timezone."""
        try:
            tz = pytz.timezone(self.default_timezone)
            return datetime.now(tz).isoformat()
        except Exception as e:
            logger.error(f"Error getting current datetime: {str(e)}")
            # Fallback to UTC
            return datetime.now(pytz.UTC).isoformat()
    
    # Helper methods for API interactions
    async def _geocode(self, city: str) -> Tuple[float, float]:
        """Get coordinates for a city."""
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": "weather-agent/1.0"},
                timeout=10,
            ) as client:
                response = await client.get(
                    self.NOMINATIM_URL,
                    params={"q": city, "format": "json", "limit": 1},
                )
                response.raise_for_status()
                data = response.json()
                if not data:
                    logger.error(f"Could not find location: {city}")
                    raise ValueError(f"Could not find location: {city}")
                lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
                logger.info(f"Geocoded {city} to coordinates: {lat}, {lon}")
                return lat, lon
        except Exception as e:
            logger.error(f"Geocoding error for {city}: {str(e)}")
            raise
    
    async def _get_weather_data(self, location: str) -> Dict[str, Any]:
        """Get comprehensive weather data from API."""
        try:
            if "," in location:
                lat, lon = map(float, location.split(",", maxsplit=1))
                location_name = f"{lat:.2f},{lon:.2f}"
            else:
                lat, lon = await self._geocode(location)
                location_name = location
        except Exception as e:
            logger.error(f"Location error for {location}: {str(e)}")
            raise RuntimeError(f"Location error: {e}")

        params = {
            "latitude": lat, "longitude": lon, "current_weather": True,
            "hourly": "temperature_2m,weathercode,precipitation_probability,precipitation",
            "daily": "sunrise,sunset,temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
            "forecast_days": 3, "timezone": "UTC"
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(self.OPEN_METEO_URL, params=params)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Retrieved weather data for {location_name}")
        except Exception as e:
            logger.error(f"Weather API error for {location}: {str(e)}")
            raise RuntimeError(f"Weather API error: {e}")

        return {
            "location": location_name,
            "current": data.get("current_weather", {}),
            "hourly": data.get("hourly", {}),
            "daily": data.get("daily", {}),
            "coordinates": (lat, lon)
        }
    
    def _format_forecast(self, data: Dict, forecast_type: str) -> str:
        """Format different types of forecasts."""
        if forecast_type == "hourly":
            hourly = data["hourly"]
            times = hourly["time"][:12]
            temps = hourly["temperature_2m"][:12]
            codes = hourly["weathercode"][:12]
            precip_probs = hourly["precipitation_probability"][:12]
            
            lines = []
            for time, temp, code, prob in zip(times, temps, codes, precip_probs):
                desc = self.WEATHER_CODE_DESC.get(code, f"Code {code}")
                dt = datetime.fromisoformat(time)
                time_str = dt.strftime("%H:%M")
                lines.append(f"  {time_str}: {temp:.1f}°C, {desc}, rain {prob}%")
            
            logger.info(f"Formatted hourly forecast for {data['location']}")
            return f"Next 12 hours forecast for {data['location']}:\n" + "\n".join(lines)
        
        elif forecast_type == "tomorrow":
            daily = data["daily"]
            if len(daily["time"]) < 2:
                logger.warning(f"No tomorrow forecast available for {data['location']}")
                return f"No tomorrow forecast available for {data['location']}"
            
            date = daily["time"][1]
            temp_max = daily["temperature_2m_max"][1]
            temp_min = daily["temperature_2m_min"][1]
            precip = daily["precipitation_sum"][1]
            code = daily["weathercode"][1]
            desc = self.WEATHER_CODE_DESC.get(code, f"Code {code}")
            
            logger.info(f"Formatted tomorrow forecast for {data['location']}")
            return f"Tomorrow's forecast for {data['location']} ({date}):\n" \
                   f"• Temperature: {temp_min:.0f}°C to {temp_max:.0f}°C\n" \
                   f"• Conditions: {desc}\n" \
                   f"• Precipitation: {precip:.1f}mm"
        
        else:  # daily
            daily = data["daily"]
            lines = []
            for i, (date, temp_max, temp_min, precip, code) in enumerate(zip(
                daily["time"], daily["temperature_2m_max"], 
                daily["temperature_2m_min"], daily["precipitation_sum"], 
                daily["weathercode"]
            )):
                if i >= 3:  # Only show 3 days
                    break
                desc = self.WEATHER_CODE_DESC.get(code, f"Code {code}")
                lines.append(f"  {date}: {temp_min:.0f}-{temp_max:.0f}°C, {desc}, {precip:.1f}mm")
            
            logger.info(f"Formatted 3-day forecast for {data['location']}")
            return f"3-day forecast for {data['location']}:\n" + "\n".join(lines)
    
    # Public tool methods
    async def get_current_weather(self, location: str) -> str:
        """Get current weather conditions for any city or location."""
        try:
            data = await self._get_weather_data(location)
            current = data["current"]
            
            if not current:
                logger.warning(f"No current weather data available for {location}")
                return f"No current weather data available for {location}"
            
            temp_c = current["temperature"]
            wind_kmh = current["windspeed"]
            code = int(current["weathercode"])
            desc = self.WEATHER_CODE_DESC.get(code, f"Weather code {code}")
            timestamp = datetime.fromisoformat(current["time"]).strftime("%Y-%m-%d %H:%M UTC")
            
            result = f"Current weather for {data['location']} at {timestamp}: {temp_c}°C, {desc}, wind {wind_kmh} km/h"
            logger.info(f"Retrieved current weather for {location}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting weather for {location}: {str(e)}")
            return f"Error getting weather for {location}: {str(e)}"
    
    async def get_weather_forecast(self, location: str, forecast_type: str = "today") -> str:
        """Get weather forecast for a location."""
        try:
            data = await self._get_weather_data(location)
            
            if forecast_type.lower() in ["today", "hourly"]:
                result = self._format_forecast(data, "hourly")
            elif forecast_type.lower() == "tomorrow":
                result = self._format_forecast(data, "tomorrow")
            else:  # daily
                result = self._format_forecast(data, "daily")
            
            logger.info(f"Retrieved {forecast_type} forecast for {location}")
            return result
                
        except Exception as e:
            logger.error(f"Error getting forecast for {location}: {str(e)}")
            return f"Error getting forecast for {location}: {str(e)}"
    
    async def check_rain_probability(self, location: str, time_period: str = "today") -> str:
        """Check rain probability for a specific time period."""
        try:
            data = await self._get_weather_data(location)
            hourly = data["hourly"]
            
            if not hourly:
                logger.warning(f"No forecast data available for {location}")
                return f"No forecast data available for {location}"
            
            current_hour = datetime.now().hour
            
            # Determine time window based on period
            if time_period.lower() in ["this_evening", "evening"]:
                start_idx, end_idx, period_name = max(0, 18 - current_hour), min(len(hourly["time"]), 22 - current_hour + 1), "this evening"
            elif time_period.lower() == "tonight":
                start_idx, end_idx, period_name = max(0, 22 - current_hour), min(len(hourly["time"]), 30 - current_hour + 1), "tonight"
            elif time_period.lower() == "tomorrow":
                start_idx, end_idx, period_name = 24 - current_hour, min(len(hourly["time"]), 48 - current_hour), "tomorrow"
            else:  # today
                start_idx, end_idx, period_name = 0, min(len(hourly["time"]), 24 - current_hour), "today"
            
            if start_idx >= len(hourly["time"]) or end_idx <= start_idx:
                logger.warning(f"No forecast data available for {period_name}")
                return f"No forecast data available for {period_name}"
            
            precip_probs = hourly["precipitation_probability"][start_idx:end_idx]
            precip_amounts = hourly["precipitation"][start_idx:end_idx]
            times = hourly["time"][start_idx:end_idx]
            
            max_prob = max(precip_probs) if precip_probs else 0
            total_precip = sum(precip_amounts) if precip_amounts else 0
            peak_idx = precip_probs.index(max_prob) if precip_probs else 0
            peak_time = times[peak_idx] if times else "unknown"
            
            result = f"Rain forecast for {data['location']} {period_name}:\n"
            result += f"• Maximum rain probability: {max_prob}%\n"
            result += f"• Expected precipitation: {total_precip:.1f}mm\n"
            result += f"• Peak rain time: {peak_time}\n"
            
            if max_prob >= 70:
                result += "• Rain is very likely"
            elif max_prob >= 50:
                result += "• Rain is likely"
            elif max_prob >= 30:
                result += "• Rain is possible"
            else:
                result += "• Rain is unlikely"
            
            logger.info(f"Retrieved rain probability for {location} {period_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error checking rain probability for {location}: {str(e)}")
            return f"Error checking rain probability for {location}: {str(e)}"
    
    async def geocode_location(self, location: str) -> str:
        """Get latitude and longitude coordinates for a city."""
        try:
            lat, lon = await self._geocode(location)
            result = f"Coordinates for {location}: {lat:.4f}, {lon:.4f}"
            logger.info(f"Geocoded location {location}")
            return result
        except Exception as e:
            logger.error(f"Error finding location {location}: {str(e)}")
            return f"Error finding location {location}: {str(e)}"
    
    async def as_function_tools(self) -> List[FunctionTool]:
        """Convert methods to FunctionTool instances for AutoGen."""
        tools = [
            FunctionTool(
                self.get_current_weather,
                description="Get current weather conditions for any city or location"
            ),
            FunctionTool(
                self.get_current_datetime,
                description="Get current date and time"
            ),
            FunctionTool(
                self.get_weather_forecast,
                description="Get weather forecast for a location with different time periods"
            ),
            FunctionTool(
                self.check_rain_probability,
                description="Check rain probability and precipitation forecast for specific time periods"
            ),
            FunctionTool(
                self.geocode_location,
                description="Get coordinates for a city. Only use when specifically asked for coordinates"
            ),
        ]
        logger.info(f"Created {len(tools)} weather function tools")
        return tools


# Usage function for creating weather tools
def create_weather_tools() -> List[FunctionTool]:
    """Create weather tools using the single class approach."""
    weather_tools = WeatherTools()
    return weather_tools.as_function_tools()


# usage and testing
async def test_weather_tools():
    """Test the single class weather tools."""
    
    logger.info("Testing Single Class Weather Tools")
    
    weather = WeatherTools()
    
    # Test current weather
    logger.info("Testing current weather")
    result = await weather.get_current_weather("Mumbai")
    logger.info(f"Current weather result: {result}")
    
    # Test rain probability
    logger.info("Testing rain probability")
    result = await weather.check_rain_probability("Mumbai", "today")
    logger.info(f"Rain probability result: {result}")
    
    # Test forecast
    logger.info("Testing weather forecast")
    result = await weather.get_weather_forecast("Mumbai", "tomorrow")
    logger.info(f"Weather forecast result: {result}")
    
    # Test function tools creation
    logger.info("Testing function tools creation")
    tools = await weather.as_function_tools()
    logger.info(f"Created {len(tools)} tools: {[tool.name for tool in tools]}")


#if __name__ == "__main__":
#    import asyncio
#    asyncio.run(test_weather_tools())