import streamlit as st
import pydeck as pdk
import numpy as np
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

def create_building_polygon(lat, lon, width, length, height):
    # Convert dimensions from meters to degrees
    lat_offset = width / 111111
    lon_offset = length / (111111 * np.cos(np.radians(lat)))

    # Create polygon coordinates
    polygon = [
        [lon - lon_offset/2, lat - lat_offset/2],
        [lon + lon_offset/2, lat - lat_offset/2],
        [lon + lon_offset/2, lat + lat_offset/2],
        [lon - lon_offset/2, lat + lat_offset/2]
    ]
    return polygon, height

st.title("3D Building Mapper")

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

# Building information inputs
building_type = st.selectbox("Select building type:", ["House", "Office", "Skyscraper", "Factory"])
col1, col2, col3 = st.columns(3)
with col1:
    width = st.number_input("Width (meters):", min_value=1.0, value=10.0)
with col2:
    length = st.number_input("Length (meters):", min_value=1.0, value=10.0)
with col3:
    height = st.number_input("Height (meters):", min_value=1.0, value=5.0)

if lat is not None and lon is not None:
    # Create building polygon
    polygon, building_height = create_building_polygon(lat, lon, width, length, height)

    # Define the initial view state
    view_state = pdk.ViewState(
        latitude=lat,
        longitude=lon,
        zoom=18,
        pitch=60,
        bearing=0
    )

    # Define the map layers
    layers = [
        pdk.Layer(
            "PolygonLayer",
            data=[{
                "polygon": polygon,
                "elevation": building_height
            }],
            get_polygon="polygon",
            get_elevation="elevation",
            get_fill_color=[200, 200, 200],  # Light gray color for the building
            get_line_color=[0, 0, 0],
            wireframe=True,
            extruded=True,
        )
    ]

    # Create the map
    r = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/satellite-v9",
    )

    # Display the map
    st.pydeck_chart(r)

    st.write(f"Latitude: {lat}")
    st.write(f"Longitude: {lon}")
    st.write(f"Building Type: {building_type}")
    st.write(f"Dimensions: {width}m x {length}m x {height}m")