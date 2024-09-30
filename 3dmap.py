import streamlit as st
import pydeck as pdk
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
    # Define the initial view state
    view_state = pdk.ViewState(
        latitude=lat,
        longitude=lon,
        zoom=13,
        pitch=45,  # Tilt the map (0 is top-down)
        bearing=0  # Rotation of the map
    )

    # Define the map layer
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"position": [lon, lat]}],
        get_position="position",
        get_color=[255, 0, 0, 200],  # Red color for the marker
        get_radius=100,  # Size of the marker
    )

    # Create the map
    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/satellite-v9",  # Use satellite imagery for a more 3D feel
    )

    # Display the map
    st.pydeck_chart(r)

    st.write(f"Latitude: {lat}")
    st.write(f"Longitude: {lon}")