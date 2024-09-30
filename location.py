import streamlit as st
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

def get_coordinates(address):
    geolocator = Nominatim(user_agent="my_streamlit_app")
    try:
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        else:
            return None
    except (GeocoderTimedOut, GeocoderUnavailable):
        st.error("Geocoding service is unavailable. Please try again later.")
        return None

st.title("ZoningLLM")

input_type = st.radio("Select input type:", ("Address", "Coordinates"))

if input_type == "Address":
    address = st.text_input("Enter your address:")
    if address:
        coordinates = get_coordinates(address)
        if coordinates:
            lat, lon = coordinates
        else:
            st.error("Unable to find the location. Please check the address and try again.")
            lat, lon = None, None
else:
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("Enter latitude:", min_value=-90.0, max_value=90.0, value=0.0)
    with col2:
        lon = st.number_input("Enter longitude:", min_value=-180.0, max_value=180.0, value=0.0)

if lat is not None and lon is not None:
    m = folium.Map(location=[lat, lon], zoom_start=10)
    folium.Marker([lat, lon]).add_to(m)
    folium_static(m)

    st.write(f"Latitude: {lat}")
    st.write(f"Longitude: {lon}")