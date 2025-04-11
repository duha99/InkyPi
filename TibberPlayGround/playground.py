import asyncio
import datetime
import os
import tibber

from dotenv import load_dotenv
from pathlib import Path

dotenv_path = Path('../.env')
load_dotenv(dotenv_path=dotenv_path)

tibber_token = os.getenv("TIBBER_TOKEN")

async def get_price_forecast():
    tibber_connection = tibber.Tibber(tibber_token, user_agent="myAgent")
    await tibber_connection.update_info()

    home = tibber_connection.get_homes()[0]
    await home.fetch_consumption_data()

    await home.update_info_and_price_info()

    await home.update_price_info()
    print(home.price_level) #Preis Verlauf mit Forecast Eingeordnet von low, normal, high
    print(home.price_total) #Preis Verlauf mit Forecast preis pro kwh

    await home.update_current_price_info()
    print(home.current_price_info) #Aktuelle Preis info Aufgeschlüsselt (Energie, Steuer, Gesamt)
    print(home.current_price_total) # Aktueller Preis gesammt
    print(home.current_price_data())
    print(home.current_attributes())

    await tibber_connection.close_connection()

if __name__ == '__main__':
    loop = asyncio.run(get_price_forecast())
