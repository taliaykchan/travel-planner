import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
# This line is the key: it pulls the Cloud logic from your other file
from database import get_data, add_data

# --- 1. Page Config ---
st.set_page_config(page_title="Trip Planner 2026", layout="wide")
st.title("🗺️ Our Cloud Travel Map")

# --- 2. Sidebar for Adding Locations ---
with st.sidebar:
    st.header("📍 Add New Spot")
    
    with st.form("add_location_form"):
        loc_name = st.text_input("Location Name")
        loc_note = st.text_area("Notes")
        submitted = st.form_submit_button("Add to Map")

        if submitted and loc_name:
            with st.spinner('Finding coordinates...'):
                geolocator = Nominatim(user_agent="my_travel_planner_2026")
                try:
                    location = geolocator.geocode(loc_name)
                    if location:
                        # This now sends data to Supabase!
                        add_data(loc_name, loc_note, location.latitude, location.longitude)
                        st.success(f"Added {loc_name} to the cloud!")
                        st.rerun()
                    else:
                        st.error("Location not found.")
                except Exception as e:
                    st.error("Service busy, try again in a moment.")

# --- 3. Main Map Display ---
# This now pulls data from Supabase!
locations = get_data()

# Center the map
if locations:
    last_lat, last_lon = locations[-1][2], locations[-1][3]
    m = folium.Map(location=[last_lat, last_lon], zoom_start=12)
else:
    m = folium.Map(location=[22.3193, 114.1694], zoom_start=2)

# Drop pins for everything in the cloud
for loc in locations:
    name, note, lat, lon = loc
    folium.Marker(
        [lat, lon],
        popup=folium.Popup(f"<b>{name}</b><br>{note}", max_width=300),
        tooltip=name,
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

st_folium(m, width=1000, height=600)
