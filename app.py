import streamlit as st
import pydeck as pdk
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time

# Set page config for dark theme
st.set_page_config(
    page_title="3D Building Visualizer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
    <style>
        .stApp {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        .stTextInput > div > div > input {
            background-color: #262730;
            color: #FAFAFA;
        }
        .stNumberInput > div > div > input {
            background-color: #262730;
            color: #FAFAFA;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize the geocoder
@st.cache_resource
def get_geocoder():
    return Nominatim(user_agent="building_visualizer")

# Function to geocode address
def geocode_address(address):
    geocoder = get_geocoder()
    try:
        location = geocoder.geocode(address)
        if location:
            return location.latitude, location.longitude, location.address
        return None, None, None
    except (GeocoderTimedOut, GeocoderUnavailable):
        return None, None, None

# Title and description
st.title("3D Building Visualizer")
st.markdown("Enter an address and building dimensions to visualize it on a map.")

# Create tabs for different input methods
location_tab, coords_tab = st.tabs(["Search by Address", "Enter Coordinates"])

# Initialize session state for coordinates
if 'latitude' not in st.session_state:
    st.session_state.latitude = 40.7128
if 'longitude' not in st.session_state:
    st.session_state.longitude = -74.0060
if 'formatted_address' not in st.session_state:
    st.session_state.formatted_address = "New York, NY, USA"

# Address input tab
with location_tab:
    col1, col2 = st.columns([3, 1])
    with col1:
        address = st.text_input("Enter Address", "Empire State Building, New York, NY")
    with col2:
        if st.button("Search", key="search_button"):
            with st.spinner("Looking up address..."):
                lat, lon, formatted_address = geocode_address(address)
                if lat and lon:
                    st.session_state.latitude = lat
                    st.session_state.longitude = lon
                    st.session_state.formatted_address = formatted_address
                    st.success("Location found!")
                else:
                    st.error("Address not found. Please try again.")

# Coordinate input tab
with coords_tab:
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.longitude = st.number_input(
            "Longitude",
            value=st.session_state.longitude,
            format="%.6f",
            help="Enter the longitude coordinate"
        )
    with col2:
        st.session_state.latitude = st.number_input(
            "Latitude",
            value=st.session_state.latitude,
            format="%.6f",
            help="Enter the latitude coordinate"
        )

# Display current location
st.markdown("### Current Location")
st.markdown(f"**{st.session_state.formatted_address}**")
st.markdown(f"Coordinates: ({st.session_state.latitude:.6f}, {st.session_state.longitude:.6f})")

# Building dimensions
st.markdown("### Building Dimensions")
col1, col2, col3 = st.columns(3)

with col1:
    height = st.number_input("Height (meters)", value=100.0, min_value=1.0,
                           help="Enter the building height in meters")
with col2:
    length = st.number_input("Length (meters)", value=50.0, min_value=1.0,
                           help="Enter the building length in meters")
with col3:
    width = st.number_input("Width (meters)", value=30.0, min_value=1.0,
                          help="Enter the building width in meters")

# Create building data
def create_building_data(lon, lat, height, length, width):
    # Convert building dimensions from meters to coordinates
    # Approximate conversion (varies by latitude)
    meter_to_coord = 0.00001  # rough approximation
    
    half_length = (length * meter_to_coord) / 2
    half_width = (width * meter_to_coord) / 2
    
    # Create polygon coordinates
    polygon = [
        [lon - half_width, lat - half_length],
        [lon + half_width, lat - half_length],
        [lon + half_width, lat + half_length],
        [lon - half_width, lat + half_length]
    ]
    
    return pd.DataFrame({
        'polygon': [polygon],
        'height': [height]
    })

# Create the building data
building_data = create_building_data(
    st.session_state.longitude,
    st.session_state.latitude,
    height,
    length,
    width
)

# Create the 3D visualization
def create_3d_map(data, center_lon, center_lat):
    # Define the layer for the building
    layer = pdk.Layer(
        'PolygonLayer',
        data,
        get_polygon='polygon',
        get_elevation='height',
        elevation_scale=1,
        extruded=True,
        filled=True,
        wireframe=True,
        get_fill_color=[169, 169, 169, 200],
        get_line_color=[0, 0, 0],
        pickable=True
    )
    
    # Create the view state
    view_state = pdk.ViewState(
        longitude=center_lon,
        latitude=center_lat,
        zoom=16,
        pitch=45,
        bearing=0
    )
    
    # Create the deck
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/dark-v10',
    )
    
    return deck

# Create and display the map
st.subheader("3D Visualization")
deck = create_3d_map(building_data, st.session_state.longitude, st.session_state.latitude)
st.pydeck_chart(deck)

# Add information about the visualization
with st.expander("About this visualization"):
    st.markdown(f"""
    This 3D building visualization shows your building at:
    - **Address**: {st.session_state.formatted_address}
    - **Coordinates**: ({st.session_state.latitude:.6f}°, {st.session_state.longitude:.6f}°)
    
    Building specifications:
    - Height: {height:.1f} meters
    - Length: {length:.1f} meters
    - Width: {width:.1f} meters
    
    The building is rendered on a dark-themed MapBox map, with the building shown as a 3D extrusion.
    You can:
    - Rotate the view by holding right-click and dragging
    - Zoom with the scroll wheel
    - Pan by holding left-click and dragging
    """)

# Footer
st.markdown("---")
st.markdown("Built with Streamlit, PyDeck, and Nominatim geocoding")