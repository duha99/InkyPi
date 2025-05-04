import asyncio
from datetime import timedelta, datetime, timezone
import os

import pytz
import tibber
import matplotlib.pyplot as plt
import matplotlib.dates as mdates



from dotenv import load_dotenv
from pathlib import Path

dotenv_path = Path('../.env')
load_dotenv(dotenv_path=dotenv_path)

tibber_token = os.getenv("TIBBER_TOKEN")

async def get_price_forecast():
    tibber_connection = tibber.Tibber(tibber_token, user_agent="myAgent")
    await tibber_connection.update_info()

    home = tibber_connection.get_homes()[0]
    #await home.fetch_consumption_data()

    #await home.update_info_and_price_info()

    await home.update_price_info()
    print(home.price_level) #Preis Verlauf mit Forecast Eingeordnet von low, normal, high
    print(home.price_total) #Preis Verlauf mit Forecast preis pro kwh

    await home.update_price_info()
    print(home.current_price_info) #Aktuelle Preis info Aufgeschlüsselt (Energie, Steuer, Gesamt)
    print(home.current_price_total) # Aktueller Preis gesammt
    print(home.current_price_data())
    print(home.current_attributes())
    print(home.current_price_data())

    # Get the current time and set midnight today (UTC)
    tz = pytz.timezone("Europe/Berlin")
    now = datetime.now(tz) # Current UTC time
    midnight_today = datetime(now.year, now.month, now.day, tzinfo=tz)  # Midnight today

    # Calculate the time range (midnight today to midnight 2 days later)
    start_time = midnight_today  # Today's midnight
    end_time = midnight_today + timedelta(days=2)  # Midnight 48 hours later

    # Filter dictionary for dates in the range
    # Use `fromisoformat` to parse ISO datetime strings which are offset-aware
    filtered_data = {
        datetime.fromisoformat(date): price
        for date, price in home.price_total.items()
        if start_time <= datetime.fromisoformat(date) <= end_time
    }

    # Sort the filtered data by datetime
    filtered_data = dict(sorted(filtered_data.items()))

    dates = list(filtered_data.keys())
    prices = list(filtered_data.values())

    if dates[-1] < end_time:
        dates.append(end_time)
        prices.append(prices[-1])  # Nimm den letzten Preiswert für die letzte Stunde mit

    # Plotting the graph
    plt.figure(figsize=(10, 5))
    plt.step(dates, prices, where="post", color="r", label="Preis", linewidth=2)
    plt.title("Preis Aussicht (Letzte 24h zu nächsten 24h)")
    plt.xlabel("Uhrzeit")
    plt.ylabel("Preise (pro kWh)")

    # Add current time marker with a vertical line and label
    plt.axvline(x=now, color="red", linestyle="--", label="Aktuelle Zeit")

    plt.axvline(x=midnight_today+timedelta(days=1), color="gray", linestyle="--", label="")
    # Mark the current time on the graph explicitly (optional)
    plt.scatter([now], [None], color="red", label=f"Jetzt: {now.strftime('%H:%M')}")

    # Format the x-axis to display only the time
    time_format = mdates.DateFormatter("%H:%M")  # Time only (hours:minutes)
    plt.gca().xaxis.set_major_formatter(time_format)

    # Set x-axis ticks at regular intervals
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))  # Step size: every 6 hours

    # Rotate the x-axis labels for better visibility
    plt.gcf().autofmt_xdate()

    # Add grid, legend, and layout adjustments
    plt.legend()
    plt.grid()
    plt.tight_layout()

    # Show the graph
    plt.show()

    # Parse the data into a list of timestamps and categories
    parsed_data = [(datetime.fromisoformat(ts), category) for ts, category in home.price_level.items()]

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

    # Display the low time windows
    for start, end in low_time_windows:
        print(f"Start: {start}, End: {end}")

    await tibber_connection.close_connection()

if __name__ == '__main__':
    loop = asyncio.run(get_price_forecast())
