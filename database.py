import streamlit as st
import requests

URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
TIMEOUT_SECONDS = 20

HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def _request(method: str, endpoint: str, **kwargs):
    try:
        response = requests.request(
            method=method,
            url=endpoint,
            headers=HEADERS,
            timeout=TIMEOUT_SECONDS,
            **kwargs,
        )
        return response
    except requests.RequestException as exc:
        st.error(f"Supabase request failed: {exc}")
        return None


def _response_error_detail(response):
    if response is None:
        return "No response from Supabase."

    try:
        return response.json()
    except ValueError:
        return response.text


def get_trips():
    endpoint = f"{URL}/rest/v1/trips?select=*&order=start_date"
    response = _request("GET", endpoint)
    if response and response.status_code == 200:
        return response.json()
    return []


def create_trip(trip_name, start_date, end_date):
    endpoint = f"{URL}/rest/v1/trips"
    payload = {
        "trip_name": trip_name,
        "start_date": start_date,
        "end_date": end_date,
    }
    response = _request("POST", endpoint, json=payload)
    if response and response.status_code in (200, 201):
        data = response.json()
        if data:
            return data[0]["id"]

    st.error("Failed to create trip.")
    return None


def update_trip_flights(trip_id, flight_data):
    endpoint = f"{URL}/rest/v1/trips?id=eq.{trip_id}"
    response = _request("PATCH", endpoint, json=flight_data)
    if response and response.status_code in (200, 204):
        return True

    st.error("Failed to save flight info.")
    return False


def update_trip_day_colors(trip_id, day_colors):
    endpoint = f"{URL}/rest/v1/trips?id=eq.{trip_id}"
    response = _request("PATCH", endpoint, json={"day_colors": day_colors})
    if response and response.status_code in (200, 204):
        return True

    st.error("Failed to save day colours. Add a jsonb column named day_colors to trips if it does not exist yet.")
    return False


def delete_trip(trip_id):
    endpoint = f"{URL}/rest/v1/trips?id=eq.{trip_id}"
    response = _request("DELETE", endpoint)
    if response and response.status_code in (200, 204):
        return True

    st.error("Failed to delete trip.")
    return False


def get_data(trip_id):
    endpoint = f"{URL}/rest/v1/locations?trip_id=eq.{trip_id}&select=*"
    response = _request("GET", endpoint)

    if response and response.status_code == 200:
        data = response.json()
        return [
            {
                "id": item["id"],
                "name": item["name"],
                "note": item.get("note") or "",
                "lat": item["lat"],
                "lon": item["lon"],
                "day": int(item.get("day", 1)),
                "arrival_time": item.get("arrival_time") or "",
            }
            for item in data
        ]

    return []


def add_data(trip_id, name, note, lat, lon, day, arrival_time):
    endpoint = f"{URL}/rest/v1/locations"
    payload = {
        "trip_id": trip_id,
        "name": name,
        "note": note,
        "lat": lat,
        "lon": lon,
        "day": day,
        "arrival_time": arrival_time,
    }
    response = _request("POST", endpoint, json=payload)
    if response and response.status_code in (200, 201):
        return True

    st.error("Failed to add location. Check your Supabase table schema and RLS policies.")
    return False


def update_data(item_id, name, note, day, arrival_time):
    endpoint = f"{URL}/rest/v1/locations?id=eq.{item_id}"
    payload = {
        "name": name,
        "note": note,
        "day": day,
        "arrival_time": arrival_time,
    }
    response = _request("PATCH", endpoint, json=payload)
    if response and response.status_code in (200, 204):
        return True

    st.error("Failed to update item.")
    return False


def delete_data(item_id):
    endpoint = f"{URL}/rest/v1/locations?id=eq.{item_id}"
    response = _request("DELETE", endpoint)
    if response and response.status_code in (200, 204):
        return True

    st.error("Failed to delete item.")
    return False


def get_day_images(trip_id):
    endpoint = f"{URL}/rest/v1/day_images?trip_id=eq.{trip_id}&select=*&order=day"
    response = _request("GET", endpoint)

    if response and response.status_code == 200:
        return [
            {
                "id": item["id"],
                "trip_id": item["trip_id"],
                "day": int(item.get("day", 1)),
                "file_name": item.get("file_name") or "",
                "mime_type": item.get("mime_type") or "image/jpeg",
                "image_data": item.get("image_data") or "",
            }
            for item in response.json()
        ]

    return []


def add_day_image(trip_id, day, file_name, mime_type, image_data):
    endpoint = f"{URL}/rest/v1/day_images"
    payload = {
        "trip_id": trip_id,
        "day": day,
        "file_name": file_name,
        "mime_type": mime_type,
        "image_data": image_data,
    }
    response = _request("POST", endpoint, json=payload)
    if response and response.status_code in (200, 201):
        return True

    detail = _response_error_detail(response)
    st.error(f"Failed to add day image. Status: {response.status_code if response else 'N/A'}")
    st.code(str(detail), language="text")
    return False


def delete_day_image(image_id):
    endpoint = f"{URL}/rest/v1/day_images?id=eq.{image_id}"
    response = _request("DELETE", endpoint)
    if response and response.status_code in (200, 204):
        return True

    st.error("Failed to delete day image.")
    return False
