import base64
import html
import json
from datetime import date, datetime, time, timedelta
from urllib.parse import quote

import folium
import streamlit as st
import streamlit.components.v1 as components
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium

from database import (
    add_data,
    add_day_image,
    create_trip,
    delete_data,
    delete_day_image,
    delete_trip,
    get_data,
    get_day_images,
    get_trips,
    update_data,
    update_trip_day_colors,
    update_trip_flights,
)

st.set_page_config(page_title="Travel Planner", layout="wide")

TIME_STEP_MINUTES = 5
MINUTE_OPTIONS = list(range(0, 60, TIME_STEP_MINUTES))
DEFAULT_MAP_CENTER = [22.3193, 114.1694]
MAX_DAY_IMAGE_BYTES = 10 * 1024 * 1024
DEFAULT_DAY_COLORS = [
    "#e63946",
    "#1d3557",
    "#2a9d8f",
    "#f4a261",
    "#6a4c93",
    "#ef476f",
    "#118ab2",
    "#06d6a0",
    "#ff9f1c",
    "#8d99ae",
    "#457b9d",
    "#43aa8b",
]

if "expand_all" not in st.session_state:
    st.session_state.expand_all = True
if "current_trip_id" not in st.session_state:
    st.session_state.current_trip_id = None

if "new_spot_day" not in st.session_state:
    st.session_state.new_spot_day = 1
if "new_spot_arrival_hour" not in st.session_state:
    st.session_state.new_spot_arrival_hour = 12
if "new_spot_arrival_minute" not in st.session_state:
    st.session_state.new_spot_arrival_minute = 0
if "new_spot_country" not in st.session_state:
    st.session_state.new_spot_country = ""
if "new_spot_city" not in st.session_state:
    st.session_state.new_spot_city = ""
if "new_spot_query" not in st.session_state:
    st.session_state.new_spot_query = ""
if "reset_new_spot_form" not in st.session_state:
    st.session_state.reset_new_spot_form = False

st.markdown(
    """
    <style>
        div[data-testid="stExpander"] div[data-testid="stVerticalBlock"] {
            gap: 0.35rem;
        }

        div[data-testid="stExpander"] p {
            margin-bottom: 0.25rem;
        }

        div[data-testid="stExpander"] hr {
            margin: 0.8rem 0;
        }

        div[data-testid="stExpander"] .stButton > button {
            min-height: 2.2rem;
            padding: 0.25rem 0.65rem;
            min-width: 5rem;
            white-space: nowrap;
        }

        .day-image-card {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 0.45rem;
            background: #ffffff;
            margin-bottom: 0.85rem;
        }

        .supplement-images-title {
            margin-top: 2.25rem;
            margin-bottom: 0.55rem;
            font-weight: 700;
            font-size: 1.05rem;
        }

        .day-image-link {
            display: block;
            text-decoration: none;
        }

        .day-image-thumb {
            width: 100%;
            height: 220px;
            object-fit: cover;
            border-radius: 6px;
            display: block;
            background: #f3f4f6;
            cursor: zoom-in;
        }

        .day-image-lightbox {
            align-items: flex-start;
            background: rgba(17, 24, 39, 0.86);
            display: none;
            inset: 0;
            justify-content: center;
            overflow: auto;
            padding: 5.5rem 2rem 2.5rem;
            position: fixed;
            text-decoration: none;
            z-index: 999999;
        }

        .day-image-lightbox:target {
            display: flex;
        }

        .day-image-lightbox-backdrop {
            cursor: zoom-out;
            inset: 0;
            position: fixed;
            z-index: 0;
        }

        .day-image-lightbox-stage {
            margin: auto;
            position: relative;
            z-index: 1;
        }

        .day-image-lightbox img {
            background: #ffffff;
            border-radius: 8px;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.45);
            display: block;
            object-fit: contain;
        }

        .day-image-full-fit {
            max-height: 88vh;
            max-width: 94vw;
        }

        .day-image-full-100 {
            max-height: none;
            max-width: none;
        }

        .day-image-full-150 {
            height: auto;
            max-height: none;
            max-width: none;
            width: 140vw;
        }

        .day-image-full-200 {
            height: auto;
            max-height: none;
            max-width: none;
            width: 190vw;
        }

        .day-image-lightbox-close {
            color: #ffffff;
            font-size: 2.25rem;
            font-weight: 700;
            line-height: 1;
            position: fixed;
            right: 1.4rem;
            top: 1rem;
            text-decoration: none;
            z-index: 2;
        }

        .day-image-zoom-toolbar {
            align-items: center;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 999px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.22);
            display: flex;
            gap: 0.35rem;
            left: 50%;
            padding: 0.35rem;
            position: fixed;
            top: 1rem;
            transform: translateX(-50%);
            z-index: 2;
        }

        .day-image-zoom-toolbar a {
            border-radius: 999px;
            color: #111827;
            font-size: 0.9rem;
            font-weight: 700;
            padding: 0.4rem 0.7rem;
            text-decoration: none;
        }

        .day-image-zoom-toolbar a.active,
        .day-image-zoom-toolbar a:hover {
            background: #111827;
            color: #ffffff;
        }

    </style>
    """,
    unsafe_allow_html=True,
)


def toggle_expand() -> None:
    st.session_state.expand_all = not st.session_state.expand_all


def normalize_minute(minute_value: int) -> int:
    return min(MINUTE_OPTIONS, key=lambda option: abs(option - int(minute_value)))


def normalize_time_to_step(raw_time: time) -> time:
    return time(hour=raw_time.hour, minute=normalize_minute(raw_time.minute))


def parse_time_string(value: str | None, fallback: str = "12:00") -> time:
    raw_value = value or fallback
    parsed = datetime.strptime(raw_value, "%H:%M").time()
    return normalize_time_to_step(parsed)


def render_time_selector(label: str, key_prefix: str, default_value: time) -> time:
    default_value = normalize_time_to_step(default_value)
    hour_key = f"{key_prefix}_hour"
    minute_key = f"{key_prefix}_minute"

    if hour_key not in st.session_state:
        st.session_state[hour_key] = default_value.hour
    if minute_key not in st.session_state:
        st.session_state[minute_key] = default_value.minute

    st.markdown(f"**{label}**")
    col1, col2 = st.columns(2)

    with col1:
        hour_value = st.selectbox(
            "Hour",
            options=list(range(24)),
            key=hour_key,
            format_func=lambda item: f"{item:02d}",
        )

    with col2:
        minute_value = st.selectbox(
            "Minute",
            options=MINUTE_OPTIONS,
            key=minute_key,
            format_func=lambda item: f"{item:02d}",
        )

    return time(hour=hour_value, minute=minute_value)


def build_day_colors(raw_day_colors, total_days: int) -> dict[str, str]:
    colors = {}

    if isinstance(raw_day_colors, str) and raw_day_colors.strip():
        try:
            raw_day_colors = json.loads(raw_day_colors)
        except json.JSONDecodeError:
            raw_day_colors = {}

    if isinstance(raw_day_colors, dict):
        colors.update({str(key): str(value) for key, value in raw_day_colors.items()})

    for day in range(1, total_days + 1):
        colors.setdefault(str(day), DEFAULT_DAY_COLORS[(day - 1) % len(DEFAULT_DAY_COLORS)])

    return colors


def build_dot_icon_data_uri(color: str) -> str:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18">'
        f'<circle cx="9" cy="9" r="7" fill="{color}" />'
        f"</svg>"
    )
    return f"data:image/svg+xml;utf8,{quote(svg)}"


def build_day_expander_label(day: int, current_date, weekday_label: str, color: str) -> str:
    icon_uri = build_dot_icon_data_uri(color)
    return f"![day-dot]({icon_uri}) Day {day} | {current_date.strftime('%Y-%m-%d')} ({weekday_label})"


def encode_uploaded_image(uploaded_file) -> str:
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")


def group_day_images(day_images: list[dict]) -> dict[int, list[dict]]:
    grouped_images: dict[int, list[dict]] = {}
    for image in day_images:
        grouped_images.setdefault(int(image["day"]), []).append(image)
    return grouped_images


def render_day_images(trip_id: str, day: int, images: list[dict]) -> None:
    st.markdown('<div class="supplement-images-title">Supplement Images</div>', unsafe_allow_html=True)
    image_count = len(images)
    expander_label = f"Supplement Images ({image_count})" if image_count else "Supplement Images"

    with st.expander(expander_label, expanded=bool(images)):
        uploaded_file = st.file_uploader(
            "Upload image",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"day_image_upload_{trip_id}_{day}",
        )

        if st.button("Add Image", key=f"add_day_image_{trip_id}_{day}"):
            if uploaded_file is None:
                st.warning("Please choose an image first.")
            elif uploaded_file.size > MAX_DAY_IMAGE_BYTES:
                st.error("Image is too large. Please upload an image under 10 MB.")
            else:
                image_saved = add_day_image(
                    trip_id=trip_id,
                    day=day,
                    file_name=uploaded_file.name,
                    mime_type=uploaded_file.type,
                    image_data=encode_uploaded_image(uploaded_file),
                )
                if image_saved:
                    st.rerun()

        if images:
            st.divider()
            image_cols = st.columns(3)
            for index, image in enumerate(images):
                with image_cols[index % 3]:
                    image_src = f"data:{image['mime_type']};base64,{image['image_data']}"
                    safe_src = html.escape(image_src, quote=True)
                    safe_image_id = "".join(
                        char if char.isalnum() else "-" for char in str(image["id"])
                    )
                    viewer_id = f"day-image-viewer-{day}-{safe_image_id}"
                    zoom_levels = {
                        "fit": "Fit",
                        "100": "100%",
                        "150": "150%",
                        "200": "200%",
                    }

                    st.markdown('<div class="day-image-card">', unsafe_allow_html=True)
                    st.markdown(
                        f'<a class="day-image-link" href="#{viewer_id}-fit">'
                        f'<img class="day-image-thumb" src="{safe_src}" alt="Supplement image">'
                        f"</a>",
                        unsafe_allow_html=True,
                    )
                    for zoom_key, zoom_label in zoom_levels.items():
                        toolbar_links = "".join(
                            f'<a class="{"active" if link_key == zoom_key else ""}" '
                            f'href="#{viewer_id}-{link_key}">{link_label}</a>'
                            for link_key, link_label in zoom_levels.items()
                        )
                        st.markdown(
                            f'<div id="{viewer_id}-{zoom_key}" class="day-image-lightbox">'
                            f'<a class="day-image-lightbox-backdrop" href="#_"></a>'
                            f'<a class="day-image-lightbox-close" href="#_">&times;</a>'
                            f'<div class="day-image-zoom-toolbar">{toolbar_links}</div>'
                            f'<div class="day-image-lightbox-stage">'
                            f'<img class="day-image-full-{zoom_key}" src="{safe_src}" alt="Supplement image full size">'
                            f"</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    st.markdown("<div style='height: 0.65rem;'></div>", unsafe_allow_html=True)
                    if st.button("Delete", key=f"delete_day_image_{image['id']}"):
                        delete_day_image(image["id"])
                        st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)


def get_shortbread_tile_url() -> str:
    api_key = st.secrets.get("STADIA_API_KEY", "")
    if api_key:
        return f"https://tiles.stadiamaps.com/tiles/shortbread/{{z}}/{{x}}/{{y}}{{r}}.png?api_key={api_key}"
    return ""


def get_shortbread_tile_attribution() -> str:
    return (
        '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a> '
        '&copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> '
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    )


def add_base_map_layer(travel_map: folium.Map) -> str:
    shortbread_url = get_shortbread_tile_url()

    if shortbread_url:
        folium.TileLayer(
            tiles=shortbread_url,
            attr=get_shortbread_tile_attribution(),
            name="Shortbread",
            overlay=False,
            control=False,
            max_zoom=20,
            detect_retina=True,
        ).add_to(travel_map)
        return "Shortbread"

    folium.TileLayer(
        tiles="CartoDB positron",
        name="Fallback",
        overlay=False,
        control=False,
    ).add_to(travel_map)
    return "CartoDB Positron"


@st.cache_data(show_spinner=False, ttl=3600)
def search_places(query: str, city: str = "", country: str = "", limit: int = 8) -> list[dict]:
    query = query.strip()
    city = city.strip()
    country = country.strip()

    if not query:
        return []

    geolocator = Nominatim(user_agent="travel_planner_streamlit")

    search_queries = []
    for parts in [
        [query, city, country],
        [query, city],
        [query, country],
        [query],
    ]:
        search_query = ", ".join(part for part in parts if part)
        if search_query and search_query not in search_queries:
            search_queries.append(search_query)

    seen = set()
    candidates = []

    query_tokens = [token.lower() for token in query.split() if token.strip()]
    city_lower = city.lower()
    country_lower = country.lower()

    for index, search_query in enumerate(search_queries):
        try:
            results = geolocator.geocode(
                search_query,
                exactly_one=False,
                addressdetails=True,
                limit=limit,
            )
        except Exception:
            continue

        for result in results or []:
            key = (round(result.latitude, 6), round(result.longitude, 6))
            if key in seen:
                continue

            seen.add(key)
            address = result.address or query
            address_lower = address.lower()

            city_match = city_lower in address_lower if city_lower else True
            country_match = country_lower in address_lower if country_lower else True
            query_match_count = sum(1 for token in query_tokens if token in address_lower)

            score = 0
            score += query_match_count * 3
            score += 4 if city_match and city_lower else 0
            score += 4 if country_match and country_lower else 0
            score += max(0, 3 - index)

            name = address.split(",")[0].strip() if address else query

            candidates.append(
                {
                    "name": name or query,
                    "label": address or query,
                    "lat": float(result.latitude),
                    "lon": float(result.longitude),
                    "score": score,
                    "city_match": city_match,
                    "country_match": country_match,
                }
            )

    if not candidates:
        return []

    filtered = candidates

    if country:
        country_filtered = [item for item in filtered if item["country_match"]]
        if country_filtered:
            filtered = country_filtered

    if city:
        city_filtered = [item for item in filtered if item["city_match"]]
        if city_filtered:
            filtered = city_filtered

    filtered.sort(key=lambda item: (-item["score"], item["label"]))

    return [
        {
            "name": item["name"],
            "label": item["label"],
            "lat": item["lat"],
            "lon": item["lon"],
        }
        for item in filtered[:limit]
    ]


def get_selected_search_result(search_results: list[dict], trip_id: str) -> dict | None:
    if not search_results:
        return None

    option_labels = [item["label"] for item in search_results]
    selected_label = st.selectbox(
        "Suggested matches",
        options=option_labels,
        key=f"search_result_{trip_id}",
    )
    return next((item for item in search_results if item["label"] == selected_label), None)


def format_popup(location: dict) -> str:
    safe_name = html.escape(location["name"])
    safe_note = html.escape(location.get("note") or "")
    arrival_time = location.get("arrival_time") or ""
    safe_time = html.escape(arrival_time)

    parts = [f"<b>Day {location['day']}: {safe_name}</b>"]
    if safe_time:
        parts.append(f"Time: {safe_time}")
    if safe_note:
        parts.append(safe_note.replace("\n", "<br>"))
    return "<br>".join(parts)


def get_google_maps_api_key() -> str:
    return st.secrets.get("GOOGLE_MAPS_API_KEY", "").strip()


def get_google_map_id() -> str:
    return st.secrets.get("GOOGLE_MAP_ID", "").strip()


def build_google_map_html(
    locations: list[dict],
    total_days: int,
    day_colors: dict[str, str],
    api_key: str,
) -> str:
    if locations:
        center = {"lat": float(locations[-1]["lat"]), "lng": float(locations[-1]["lon"])}
        zoom_start = 12
    else:
        center = {"lat": DEFAULT_MAP_CENTER[0], "lng": DEFAULT_MAP_CENTER[1]}
        zoom_start = 2

    map_locations = []
    for location in sorted(locations, key=lambda item: (item["day"], item.get("arrival_time") or "23:59")):
        day = int(location["day"])
        color = day_colors.get(str(day), DEFAULT_DAY_COLORS[(day - 1) % len(DEFAULT_DAY_COLORS)])
        map_locations.append(
            {
                "name": location["name"],
                "day": day,
                "lat": float(location["lat"]),
                "lng": float(location["lon"]),
                "color": color,
                "popupHtml": format_popup(location),
            }
        )

    day_controls = []
    for day in range(1, total_days + 1):
        color = html.escape(day_colors.get(str(day), DEFAULT_DAY_COLORS[(day - 1) % len(DEFAULT_DAY_COLORS)]))
        day_controls.append(
            f"""
            <label class="google-day-toggle">
                <input id="google-day-toggle-{day}" type="checkbox" checked>
                <span class="google-day-dot" style="background:{color};"></span>
                <span>Day {day}</span>
            </label>
            """
        )

    locations_json = json.dumps(map_locations, ensure_ascii=False).replace("</", "<\\/")
    map_id_json = json.dumps(get_google_map_id())
    script_url = (
        "https://maps.googleapis.com/maps/api/js"
        f"?key={quote(api_key)}&callback=initTravelMap&loading=async&language=zh-HK&region=HK"
    )

    return f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            html, body {{
                height: 100%;
                margin: 0;
                padding: 0;
            }}

            .google-map-shell {{
                border-radius: 12px;
                height: 640px;
                overflow: hidden;
                position: relative;
                width: 100%;
            }}

            #google-map {{
                height: 100%;
                width: 100%;
            }}

            .google-layer-control {{
                background: rgba(255, 255, 255, 0.94);
                border: 1px solid rgba(31, 41, 55, 0.15);
                border-radius: 12px;
                box-shadow: 0 12px 30px rgba(15, 23, 42, 0.18);
                color: #1f2937;
                font-family: Arial, sans-serif;
                max-height: 560px;
                overflow: auto;
                padding: 12px;
                position: absolute;
                right: 16px;
                top: 16px;
                z-index: 5;
            }}

            .google-layer-title {{
                border-bottom: 1px solid #e5e7eb;
                font-size: 15px;
                font-weight: 700;
                margin-bottom: 8px;
                padding-bottom: 8px;
            }}

            .google-day-toggle {{
                align-items: center;
                cursor: pointer;
                display: flex;
                font-size: 15px;
                font-weight: 700;
                gap: 8px;
                margin: 8px 0;
                white-space: nowrap;
            }}

            .google-day-toggle input {{
                height: 18px;
                width: 18px;
            }}

            .google-day-dot {{
                border-radius: 50%;
                display: inline-block;
                height: 14px;
                width: 14px;
            }}

            .google-map-error {{
                align-items: center;
                color: #b91c1c;
                display: flex;
                font-family: Arial, sans-serif;
                font-weight: 700;
                height: 100%;
                justify-content: center;
                padding: 24px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="google-map-shell">
            <div id="google-map"></div>
            <div class="google-layer-control">
                <div class="google-layer-title">Map Layers</div>
                {"".join(day_controls)}
            </div>
        </div>

        <script>
            const locations = {locations_json};
            const totalDays = {int(total_days)};
            const mapCenter = {{ lat: {center["lat"]:.8f}, lng: {center["lng"]:.8f} }};
            const mapZoom = {zoom_start};
            const mapId = {map_id_json};

            window.gm_authFailure = function() {{
                document.getElementById("google-map").innerHTML =
                    '<div class="google-map-error">Google Maps authentication failed. Please check GOOGLE_MAPS_API_KEY.</div>';
            }};

            function initTravelMap() {{
                const mapOptions = {{
                    center: mapCenter,
                    fullscreenControl: true,
                    gestureHandling: "greedy",
                    mapTypeControl: true,
                    mapTypeId: "roadmap",
                    streetViewControl: true,
                    zoom: mapZoom,
                }};

                if (mapId) {{
                    mapOptions.mapId = mapId;
                }}

                const map = new google.maps.Map(document.getElementById("google-map"), mapOptions);
                const transitLayer = new google.maps.TransitLayer();
                transitLayer.setMap(map);

                const infoWindow = new google.maps.InfoWindow();
                const bounds = new google.maps.LatLngBounds();
                const dayMarkers = {{}};

                for (let day = 1; day <= totalDays; day += 1) {{
                    dayMarkers[day] = [];
                }}

                locations.forEach((location) => {{
                    const day = Number(location.day);
                    const marker = new google.maps.Marker({{
                        icon: {{
                            fillColor: location.color,
                            fillOpacity: 0.95,
                            path: google.maps.SymbolPath.CIRCLE,
                            scale: 9,
                            strokeColor: "#ffffff",
                            strokeWeight: 2,
                        }},
                        map,
                        position: {{ lat: Number(location.lat), lng: Number(location.lng) }},
                        title: `Day ${{day}}: ${{location.name}}`,
                    }});

                    marker.addListener("click", () => {{
                        infoWindow.setContent(location.popupHtml);
                        infoWindow.open({{ anchor: marker, map }});
                    }});

                    if (!dayMarkers[day]) {{
                        dayMarkers[day] = [];
                    }}
                    dayMarkers[day].push(marker);
                    bounds.extend(marker.getPosition());
                }});

                if (locations.length > 1) {{
                    map.fitBounds(bounds, 70);
                }} else if (locations.length === 1) {{
                    map.setCenter(bounds.getCenter());
                    map.setZoom(14);
                }}

                for (let day = 1; day <= totalDays; day += 1) {{
                    const checkbox = document.getElementById(`google-day-toggle-${{day}}`);
                    if (!checkbox) {{
                        continue;
                    }}

                    checkbox.addEventListener("change", () => {{
                        const targetMap = checkbox.checked ? map : null;
                        (dayMarkers[day] || []).forEach((marker) => marker.setMap(targetMap));
                    }});
                }}
            }}

            window.initTravelMap = initTravelMap;
        </script>
        <script src="{script_url}" async defer></script>
    </body>
    </html>
    """


def build_map(locations: list[dict], total_days: int, day_colors: dict[str, str]) -> tuple[folium.Map, str]:
    if locations:
        center = [locations[-1]["lat"], locations[-1]["lon"]]
        zoom_start = 12
    else:
        center = DEFAULT_MAP_CENTER
        zoom_start = 2

    travel_map = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles=None,
        control_scale=True,
    )

    base_map_name = add_base_map_layer(travel_map)
    day_layers: dict[int, folium.FeatureGroup] = {}

    for day in range(1, total_days + 1):
        color = day_colors.get(str(day), DEFAULT_DAY_COLORS[(day - 1) % len(DEFAULT_DAY_COLORS)])
        layer_label = (
            f'<span style="display:inline-flex; align-items:center; gap:8px;">'
            f'<span style="width:14px; height:14px; border-radius:50%; background:{color}; display:inline-block;"></span>'
            f'<span style="font-weight:700; color:#1f2937;">Day {day}</span>'
            f"</span>"
        )
        layer = folium.FeatureGroup(name=layer_label, show=True)
        layer.add_to(travel_map)
        day_layers[day] = layer

    for location in sorted(locations, key=lambda item: (item["day"], item.get("arrival_time") or "23:59")):
        day = int(location["day"])
        marker_color = day_colors.get(str(day), DEFAULT_DAY_COLORS[(day - 1) % len(DEFAULT_DAY_COLORS)])

        folium.CircleMarker(
            location=[location["lat"], location["lon"]],
            radius=8,
            color=marker_color,
            weight=2,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.95,
            tooltip=f"Day {day}: {location['name']}",
            popup=folium.Popup(format_popup(location), max_width=320),
        ).add_to(day_layers[day])

    folium.LayerControl(collapsed=False).add_to(travel_map)
    return travel_map, base_map_name


def save_flight_stop(
    trip_id: str,
    label: str,
    airport_query: str,
    flight_no: str,
    takeoff_time: time,
    landing_time: time,
    day: int,
) -> None:
    matches = search_places(airport_query, limit=1)
    if not matches:
        return

    airport = matches[0]
    airport_arrival = (
        datetime.combine(date.today(), takeoff_time) - timedelta(hours=2)
    ).strftime("%H:%M")
    note = (
        f"Flight {flight_no} | "
        f"Takeoff: {takeoff_time.strftime('%H:%M')} | "
        f"Landing: {landing_time.strftime('%H:%M')}"
    )
    add_data(
        trip_id=trip_id,
        name=label,
        note=note,
        lat=airport["lat"],
        lon=airport["lon"],
        day=day,
        arrival_time=airport_arrival,
    )


all_trips = get_trips()
trip_options = {trip["trip_name"]: trip for trip in all_trips}

with st.sidebar:
    st.title("Cloud Planner")
    st.header("My Trips")

    options_list = ["-- Select a Trip --", "Create New Trip"] + list(trip_options.keys())

    default_idx = 0
    if st.session_state.current_trip_id:
        for i, trip in enumerate(trip_options.values()):
            if trip["id"] == st.session_state.current_trip_id:
                default_idx = i + 2
                break

    selected_option = st.selectbox("Choose Action", options=options_list, index=default_idx)

    if selected_option == "Create New Trip":
        with st.form("new_trip_form"):
            new_trip_name = st.text_input("Trip Name", placeholder="Summer in Japan")
            col1, col2 = st.columns(2)
            with col1:
                start_d = st.date_input("Start Date")
            with col2:
                end_d = st.date_input("End Date")

            if st.form_submit_button("Save Trip", use_container_width=True):
                if new_trip_name.strip() and end_d >= start_d:
                    new_id = create_trip(
                        trip_name=new_trip_name.strip(),
                        start_date=start_d.strftime("%Y-%m-%d"),
                        end_date=end_d.strftime("%Y-%m-%d"),
                    )
                    if new_id:
                        st.session_state.current_trip_id = new_id
                        st.success("Trip created.")
                        st.rerun()
                else:
                    st.error("Please provide a valid trip name and date range.")

        st.stop()

    if selected_option == "-- Select a Trip --":
        st.info("Please select or create a trip to continue.")
        st.stop()

    current_trip = trip_options[selected_option]
    st.session_state.current_trip_id = current_trip["id"]

    start_date = datetime.strptime(current_trip["start_date"], "%Y-%m-%d").date()
    end_date = datetime.strptime(current_trip["end_date"], "%Y-%m-%d").date()
    total_days = (end_date - start_date).days + 1
    day_colors = build_day_colors(current_trip.get("day_colors"), total_days)

    st.session_state.new_spot_day = min(max(int(st.session_state.new_spot_day), 1), int(total_days))

    st.success(f"{current_trip['trip_name']} loaded ({total_days} days)")

    with st.expander("Delete this trip"):
        if st.button("Delete Entire Trip", use_container_width=True):
            delete_trip(current_trip["id"])
            st.session_state.current_trip_id = None
            st.rerun()

    st.divider()

    with st.expander("Flight Automator", expanded=False):
        st.caption("Airport arrivals are scheduled 2 hours before takeoff.")

        outbound_flight = st.text_input(
            "Outbound Flight No.",
            value=current_trip.get("out_flight") or "",
            key=f"outbound_flight_{current_trip['id']}",
        )
        outbound_airport = st.text_input(
            "Departing Airport",
            value=current_trip.get("out_airport") or "",
            key=f"outbound_airport_{current_trip['id']}",
        )
        outbound_takeoff = render_time_selector(
            "Outbound Takeoff",
            f"trip_{current_trip['id']}_outbound_takeoff",
            parse_time_string(current_trip.get("out_takeoff"), "10:00"),
        )
        outbound_landing = render_time_selector(
            "Outbound Landing",
            f"trip_{current_trip['id']}_outbound_landing",
            parse_time_string(current_trip.get("out_landing"), "14:30"),
        )

        st.divider()

        return_flight = st.text_input(
            "Return Flight No.",
            value=current_trip.get("ret_flight") or "",
            key=f"return_flight_{current_trip['id']}",
        )
        return_airport = st.text_input(
            "Returning Airport",
            value=current_trip.get("ret_airport") or "",
            key=f"return_airport_{current_trip['id']}",
        )
        return_takeoff = render_time_selector(
            "Return Takeoff",
            f"trip_{current_trip['id']}_return_takeoff",
            parse_time_string(current_trip.get("ret_takeoff"), "16:00"),
        )
        return_landing = render_time_selector(
            "Return Landing",
            f"trip_{current_trip['id']}_return_landing",
            parse_time_string(current_trip.get("ret_landing"), "20:30"),
        )

        if st.button("Save Flight Plan", use_container_width=True):
            flight_payload = {
                "out_flight": outbound_flight,
                "out_airport": outbound_airport,
                "out_takeoff": outbound_takeoff.strftime("%H:%M"),
                "out_landing": outbound_landing.strftime("%H:%M"),
                "ret_flight": return_flight,
                "ret_airport": return_airport,
                "ret_takeoff": return_takeoff.strftime("%H:%M"),
                "ret_landing": return_landing.strftime("%H:%M"),
            }
            update_trip_flights(current_trip["id"], flight_payload)

            if outbound_flight and outbound_airport:
                save_flight_stop(
                    trip_id=current_trip["id"],
                    label=f"Arrive at {outbound_airport}",
                    airport_query=outbound_airport,
                    flight_no=outbound_flight,
                    takeoff_time=outbound_takeoff,
                    landing_time=outbound_landing,
                    day=1,
                )

            if return_flight and return_airport:
                save_flight_stop(
                    trip_id=current_trip["id"],
                    label=f"Arrive at {return_airport}",
                    airport_query=return_airport,
                    flight_no=return_flight,
                    takeoff_time=return_takeoff,
                    landing_time=return_landing,
                    day=total_days,
                )

            st.success("Flight details saved.")
            st.rerun()

    st.divider()

    with st.expander("Day Layer Colours", expanded=False):
        st.caption("Markers, map legend dots, and itinerary dots use the same colour.")
        edited_day_colors = {}

        for day in range(1, total_days + 1):
            edited_day_colors[str(day)] = st.color_picker(
                f"Day {day}",
                value=day_colors[str(day)],
                key=f"color_picker_{current_trip['id']}_{day}",
            )

        if st.button("Save Day Colours", use_container_width=True):
            if update_trip_day_colors(current_trip["id"], edited_day_colors):
                st.success("Day colours saved.")
                st.rerun()

    st.divider()

    note_key = f"new_spot_note_{current_trip['id']}"
    if note_key not in st.session_state:
        st.session_state[note_key] = ""

    if st.session_state.reset_new_spot_form:
        st.session_state.new_spot_query = ""
        st.session_state[note_key] = ""
        st.session_state.reset_new_spot_form = False

    st.header("Add New Spot")

    day_options = list(range(1, total_days + 1))
    day_num = st.selectbox(
        "Day",
        options=day_options,
        key="new_spot_day",
        format_func=lambda item: f"Day {item}",
    )

    arrival_time = render_time_selector(
        "Arrival Time",
        "new_spot_arrival",
        time(st.session_state.new_spot_arrival_hour, st.session_state.new_spot_arrival_minute),
    )

    country = st.text_input(
        "Country",
        placeholder="Japan",
        key="new_spot_country",
    )
    city = st.text_input(
        "City",
        placeholder="Tokyo",
        key="new_spot_city",
    )
    place_query = st.text_input(
        "Place Search",
        placeholder="teamLab, sushi near Ginza, Disneyland",
        help="Search results will prioritize the selected country, city, and your place keywords together.",
        key="new_spot_query",
    )

    search_results = search_places(place_query, city, country) if place_query.strip() else []
    selected_result = get_selected_search_result(search_results, current_trip["id"])

    if selected_result:
        st.caption(f"Selected match: {selected_result['label']}")
    elif place_query.strip():
        st.caption("No strong match yet. Try refining the country, city, or place search.")

    loc_note = st.text_area("Notes / Schedule", key=note_key)

    if st.button("Add to Itinerary", use_container_width=True):
        if not place_query.strip():
            st.error("Please enter a place search term.")
        else:
            chosen_place = selected_result
            if chosen_place is None:
                fallback_results = search_places(place_query, city, country, limit=1)
                chosen_place = fallback_results[0] if fallback_results else None

            if chosen_place is None:
                st.error("Unable to find a good match. Try refining country, city, or place search.")
            else:
                add_data(
                    trip_id=current_trip["id"],
                    name=chosen_place["name"],
                    note=loc_note,
                    lat=chosen_place["lat"],
                    lon=chosen_place["lon"],
                    day=int(day_num),
                    arrival_time=arrival_time.strftime("%H:%M"),
                )
                st.success(f"Added {chosen_place['name']}.")
                st.session_state.reset_new_spot_form = True
                st.rerun()

locations = get_data(st.session_state.current_trip_id)
locations.sort(key=lambda item: (item["day"], item.get("arrival_time") or "23:59", item["name"].lower()))
day_images = get_day_images(st.session_state.current_trip_id)
day_images_by_day = group_day_images(day_images)

st.title(current_trip["trip_name"])
tab_map, tab_itinerary = st.tabs(["Interactive Map", "Daily Itinerary"])

with tab_map:
    google_maps_api_key = get_google_maps_api_key()

    if google_maps_api_key:
        st.caption("Interactive map is using Google Maps with the Transit layer for rail and subway visibility.")
        st.caption("Use the map layer control to show or hide each day.")
        components.html(
            build_google_map_html(locations, total_days, day_colors, google_maps_api_key),
            height=660,
            scrolling=False,
        )
    else:
        st.warning("GOOGLE_MAPS_API_KEY is not set. Add it to Streamlit secrets to use Google Maps.")

        travel_map, base_map_name = build_map(locations, total_days, day_colors)
        if base_map_name == "Shortbread":
            st.caption("Fallback map is using the Shortbread basemap.")
        else:
            st.caption("Fallback map is using CartoDB Positron.")

        st.caption("Use the layer control on the map to show or hide each day.")
        st_folium(travel_map, width=None, height=620)

with tab_itinerary:
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.header("Your Schedule")
    with col2:
        button_label = "Collapse All" if st.session_state.expand_all else "Expand All"
        st.button(button_label, on_click=toggle_expand, use_container_width=True)

    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for day in range(1, total_days + 1):
        current_date = start_date + timedelta(days=day - 1)
        weekday_label = weekday_labels[current_date.weekday()]
        day_items = [item for item in locations if int(item["day"]) == day]
        day_color = day_colors.get(str(day), DEFAULT_DAY_COLORS[(day - 1) % len(DEFAULT_DAY_COLORS)])
        expander_label = build_day_expander_label(day, current_date, weekday_label, day_color)

        with st.expander(expander_label, expanded=st.session_state.expand_all):
            if not day_items:
                st.info("No plans yet for this day.")
            else:
                for item in day_items:
                    item_id = item["id"]
                    edit_key = f"edit_{item_id}"

                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = False

                    if not st.session_state[edit_key]:
                        item_col1, item_col2 = st.columns([0.78, 0.22])

                        with item_col1:
                            time_badge = f"{item['arrival_time']} | " if item.get("arrival_time") else ""
                            st.markdown(f"**{time_badge}{item['name']}**")
                            if item.get("note"):
                                st.caption(item["note"])

                        with item_col2:
                            edit_col, delete_col = st.columns(2, gap="small")
                            with edit_col:
                                if st.button("Edit", key=f"btn_edit_{item_id}"):
                                    st.session_state[edit_key] = True
                                    st.rerun()
                            with delete_col:
                                if st.button("Delete", key=f"btn_delete_{item_id}"):
                                    delete_data(item_id)
                                    st.rerun()
                    else:
                        st.markdown(f"**Editing: {item['name']}**")
                        with st.form(key=f"form_{item_id}"):
                            new_name = st.text_input("Name", value=item["name"])

                            day_options = list(range(1, total_days + 1))
                            current_day = int(item["day"])
                            default_day_index = day_options.index(current_day) if current_day in day_options else 0

                            new_day = st.selectbox(
                                "Day",
                                options=day_options,
                                index=default_day_index,
                                format_func=lambda option: f"Day {option}",
                                key=f"edit_day_{item_id}",
                            )

                            new_time = render_time_selector(
                                "Arrival Time",
                                f"edit_time_{item_id}",
                                parse_time_string(item.get("arrival_time"), "12:00"),
                            )

                            new_note = st.text_area("Note", value=item.get("note") or "")
                            save_col, cancel_col = st.columns(2)

                            with save_col:
                                if st.form_submit_button("Save Changes"):
                                    update_data(
                                        item_id=item_id,
                                        name=new_name.strip(),
                                        note=new_note,
                                        day=int(new_day),
                                        arrival_time=new_time.strftime("%H:%M"),
                                    )
                                    st.session_state[edit_key] = False
                                    st.rerun()

                            with cancel_col:
                                if st.form_submit_button("Cancel"):
                                    st.session_state[edit_key] = False
                                    st.rerun()

            render_day_images(
                trip_id=current_trip["id"],
                day=day,
                images=day_images_by_day.get(day, []),
            )

            st.divider()
