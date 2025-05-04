import asyncio

from plugins.base_plugin.base_plugin import BasePlugin
from datetime import datetime, timedelta
import pytz
import tibber

DEFAULT_TIMEZONE = "US/Eastern"

class TibberPower(BasePlugin):
    def generate_image(self, settings, device_config):
        timezone_name = device_config.get_config("timezone") or DEFAULT_TIMEZONE
        tz = pytz.timezone(timezone_name)
        current_time = datetime.now(tz)

        api_key = device_config.load_env_key("TIBBER_TOKEN")
        if not api_key:
            raise RuntimeError("Tibber API Key not configured.")

        tibber_data = asyncio.run(self.get_tibber_data(api_key))

        template_params = self.parse_tibber_data(tibber_data, tz)

        template_params["plugin_settings"] = settings

        dimensions = device_config.get_resolution()
        image = self.render_image(dimensions, "tibber.html", "tibber.css", template_params)

        if not image:
            raise RuntimeError("Failed to take screenshot, please check logs.")
        return image

    async def get_tibber_data(self, api_key):
        tibber_connection = tibber.Tibber(api_key, user_agent="myAgent")
        await tibber_connection.update_info()

        home = tibber_connection.get_homes()[0]

        await home.update_price_info()

        tibber_data = {
            "current": home.current_price_data(),
            "forecast_price": home.price_total,
            "forecast_price_level": home.price_level
        }
        await tibber_connection.close_connection()

        return tibber_data

    def parse_tibber_data(self, tibber_data, tz):

        dates, prices = self.get_price_forecast(tibber_data["forecast_price"], tz)
        low_time_windows = self.get_low_time_windows(tibber_data["forecast_price_level"], tz)

        data = {
            "current_price": tibber_data["current"][0],
            "current_price_level": tibber_data["current"][1],
            "current_price_time": tibber_data["current"][2],
            "price_unit": "EUR/kWh",
            "forcast": {"dates": dates, "prices": prices},
            "low_time_windows": low_time_windows,
        }
        return data

    def get_low_time_windows(self, price_level_data, tz):
        now = datetime.now(tz)
        end_time = now + timedelta(hours=24)
        # Parse the data into a list of timestamps and categories
        parsed_data = [(datetime.fromisoformat(ts), category) for ts, category in price_level_data.items()
                       if now <= datetime.fromisoformat(ts) <= end_time]

        # Sort the data by timestamps (just as a safeguard to ensure correct ordering)
        parsed_data.sort(key=lambda x: x[0])

        # Find consecutive time windows marked as "LOW"
        low_time_windows = []
        current_window = []

        for timestamp, category in parsed_data:
            if category == "LOW":
                if not current_window:
                    # Start a new low window
                    current_window = [timestamp, timestamp]
                else:
                    # Expand the current window
                    current_window[1] = timestamp
            else:
                if current_window:
                    # Close the current window and store it
                    low_time_windows.append(current_window)
                    current_window = []

        # Add the last window if still open
        if current_window:
            low_time_windows.append(current_window)

        return low_time_windows

    def get_price_forecast(self, forecast_price, tz):
        now = datetime.now(tz)  # Current UTC time
        midnight_today = datetime(now.year, now.month, now.day, tzinfo=tz)  # Midnight today

        # Calculate the time range (midnight today to midnight 2 days later)
        start_time = midnight_today  # Today's midnight
        end_time = midnight_today + timedelta(days=2)  # Midnight 48 hours later

        # Filter dictionary for dates in the range
        filtered_data = {
            datetime.fromisoformat(date): price
            for date, price in forecast_price.items()
            if start_time <= datetime.fromisoformat(date) <= end_time
        }

        # Sort the filtered data by datetime
        filtered_data = dict(sorted(filtered_data.items()))

        dates = list(filtered_data.keys())
        prices = list(filtered_data.values())

        if dates[-1] < end_time:
            dates.append(end_time)
            prices.append(prices[-1])  # Nimm den letzten Preiswert für die letzte Stunde mit

        return dates, prices

