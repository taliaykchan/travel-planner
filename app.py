import streamlit as st
import sqlite3
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- 1. 設置網頁基本資訊 ---
st.set_page_config(page_title="Trip Planner 2026", layout="wide")
st.title("🗺️ 我們的專屬旅遊地圖")

# --- 2. 數據庫操作函數 ---
def get_data():
    """從數據庫讀取所有景點"""
    conn = sqlite3.connect('travel_data.db')
    c = conn.cursor()
    # 讀取 name, note, lat, lon
    c.execute("SELECT name, note, lat, lon FROM locations")
    data = c.fetchall()
    conn.close()
    return data

def add_data(name, note, lat, lon):
    """將新景點存入數據庫"""
    conn = sqlite3.connect('travel_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO locations (name, note, lat, lon) VALUES (?, ?, ?, ?)", (name, note, lat, lon))
    conn.commit()
    conn.close()

# --- 3. 左側控制欄 (新增景點) ---
with st.sidebar:
    st.header("📍 新增景點")
    
    # 輸入表單
    with st.form("add_location_form"):
        loc_name = st.text_input("景點名稱 (例如：淺草寺, Asakusa)")
        loc_note = st.text_area("備註 / 行程安排 (例如：早上9點去求籤)")
        submitted = st.form_submit_button("搜尋並加入地圖")

        if submitted:
            if loc_name:
                with st.spinner('正在尋找座標...'):
                    # 使用 Geopy 自動把地名轉換成經緯度
                    geolocator = Nominatim(user_agent="my_travel_planner")
                    try:
                        location = geolocator.geocode(loc_name)
                        if location:
                            # 找到座標了，存入數據庫！
                            add_data(loc_name, loc_note, location.latitude, location.longitude)
                            st.success(f"成功加入：{loc_name}！")
                            st.rerun() # 刷新頁面來顯示新標記
                        else:
                            st.error("找不到這個地點，請嘗試輸入更詳細的地址或英文名稱。")
                    except Exception as e:
                        st.error("定位服務暫時無回應，請稍後再試。")
            else:
                st.warning("請先輸入景點名稱！")

# --- 4. 主畫面：顯示互動地圖 ---
locations = get_data()

# 決定地圖的初始中心點
if locations:
    # 如果已經有資料，把地圖中心設定在最後一個加入的景點
    last_lat, last_lon = locations[-1][2], locations[-1][3]
    m = folium.Map(location=[last_lat, last_lon], zoom_start=12)
else:
    # 如果沒資料，預設顯示世界地圖 (或者你可以改成你目的地的座標)
    m = folium.Map(location=[22.3193, 114.1694], zoom_start=2) # 預設香港

# 將數據庫裡的所有景點標記到地圖上
for loc in locations:
    name, note, lat, lon = loc
    # 建立標記 (Marker)
    folium.Marker(
        [lat, lon],
        popup=folium.Popup(f"<b>{name}</b><br>{note}", max_width=300),
        tooltip=name,
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

# 在 Streamlit 中渲染這個 Folium 地圖
st_folium(m, width=1000, height=600)

st.markdown("---")
st.caption("提示：在左側輸入景點，地圖會自動更新。點擊地圖上的紅點可以看你的備註！")