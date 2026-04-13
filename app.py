import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from database import get_data, add_data, delete_data

st.set_page_config(page_title="Trip Planner 2026", layout="wide")
st.title("✈️ Our Cloud Travel Planner")

# --- UI Setup: Tabs ---
tab1, tab2 = st.tabs(["🗺️ Interactive Map", "📅 Daily Itinerary"])

# --- Sidebar: Smarter Input Form ---
with st.sidebar:
    st.header("📍 Add New Spot")
    
    with st.form("add_location_form"):
        # 1. Day Selection
        day_num = st.number_input("Day of Trip", min_value=1, value=1, step=1)
        
        # 2. Smarter Location Inputs
        st.caption("Help the map find your spot:")
        country = st.text_input("Country (e.g., Japan)")
        city = st.text_input("City (e.g., Tokyo)")
        loc_name = st.text_input("Place (e.g., Best ramen near Shinjuku)")
        
        loc_note = st.text_area("Notes / Schedule")
        submitted = st.form_submit_button("Add to Itinerary")

        if submitted and loc_name:
            with st.spinner('Finding coordinates...'):
                # Combine inputs for a smarter search query
                search_query = f"{loc_name}, {city}, {country}"
                geolocator = Nominatim(user_agent="my_travel_planner_2026")
                
                success = False # Flag to safely handle reruns
                
                try:
                    location = geolocator.geocode(search_query)
                    if location:
                        add_data(loc_name, loc_note, location.latitude, location.longitude, day_num)
                        success = True
                    else:
                        st.error(f"Couldn't find coordinates for: {search_query}. Try being more specific.")
                except Exception as e:
                    st.error("Network error while searching. Please try again.")

            # We trigger the rerun OUTSIDE the try/except block to fix your bug!
            if success:
                st.success(f"Added {loc_name} to Day {day_num}!")
                st.rerun()

# --- Fetch Data ---
locations = get_data()

# --- TAB 1: Map View ---
with tab1:
    if locations:
        last_lat, last_lon = locations[-1][2], locations[-1][3]
        m = folium.Map(location=[last_lat, last_lon], zoom_start=12)
    else:
        m = folium.Map(location=[22.3193, 114.1694], zoom_start=2)

    for loc in locations:
        name, note, lat, lon, day, item_id = loc
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(f"<b>Day {day}: {name}</b><br>{note}", max_width=300),
            tooltip=f"Day {day}: {name}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)

    st_folium(m, width=1000, height=600)

# --- TAB 2: Daily Itinerary View ---
with tab2:
    st.header("Your Schedule")
    
    if not locations:
        st.info("Your itinerary is empty. Add a location in the sidebar to get started!")
    else:
        # Sort unique days
        unique_days = sorted(list(set([loc[4] for loc in locations])))
        
        for d in unique_days:
            with st.expander(f"📍 Day {d}", expanded=True):
                # Filter locations for just this day
                day_items = [l for l in locations if l[4] == d]
                
                for item in day_items:
                    name, note, lat, lon, day, item_id = item
                    
                    # Create two columns: one for text, one for the delete button
                    col1, col2 = st.columns([0.9, 0.1])
                    
                    with col1:
                        st.markdown(f"**{name}**")
                        if note:
                            st.caption(note)
                    
                    with col2:
                        # Unique key is required for buttons in a loop
                        if st.button("🗑️", key=f"del_{item_id}"):
                            delete_data(item_id)
                            st.rerun() # Refresh the app to show it's gone
                st.divider()
