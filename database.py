import streamlit as st
from supabase import create_client

# This connects your app to the cloud
def get_supabase():
    # We will set these up in Step 5
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def get_data():
    supabase = get_supabase()
    # Pull all rows from the 'locations' table
    response = supabase.table("locations").select("*").execute()
    # Extract the data list
    return [[item['name'], item['note'], item['lat'], item['lon']] for item in response.data]

def add_data(name, note, lat, lon):
    supabase = get_supabase()
    # Push a new row to the cloud
    data = {
        "name": name,
        "note": note,
        "lat": lat,
        "lon": lon
    }
    supabase.table("locations").insert(data).execute()