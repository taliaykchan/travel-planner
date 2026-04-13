import streamlit as st
import requests

URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]

HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def get_data():
    """Fetches all locations including their unique ID."""
    endpoint = f"{URL}/rest/v1/locations?select=*&order=day"
    response = requests.get(endpoint, headers=HEADERS)
    
    if response.status_code == 200:
        data = response.json()
        # We now return 6 items: Name, Note, Lat, Lon, Day, and ID
        return [[
            item['name'], 
            item['note'], 
            item['lat'], 
            item['lon'], 
            item.get('day', 1),
            item['id'] 
        ] for item in data]
    return []

def add_data(name, note, lat, lon, day):
    endpoint = f"{URL}/rest/v1/locations"
    payload = {"name": name, "note": note, "lat": lat, "lon": lon, "day": day}
    requests.post(endpoint, headers=HEADERS, json=payload)

def delete_data(item_id):
    """Deletes a specific row using its ID."""
    endpoint = f"{URL}/rest/v1/locations?id=eq.{item_id}"
    response = requests.delete(endpoint, headers=HEADERS)
    if response.status_code not in (200, 204):
        st.error("Failed to delete item.")
# test
