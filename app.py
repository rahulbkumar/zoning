import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from shapely.geometry import Point, Polygon
from shapely.ops import transform
import pyproj
from functools import partial

# Set page config for dark theme
st.set_page_config(
    page_title="ZoningLLM - 3D Building Visualizer",
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

# Define Waterloo zone coordinates (approximate boundaries)
WATERLOO_ZONE = {
    'coordinates': [
        [-80.5800, 43.4900],  # Northwest
        [-80.5800, 43.4400],  # Southwest
        [-80.5000, 43.4400],  # Southeast
        [-80.5000, 43.4900],  # Northeast
    ],
    'center': [-80.5400, 43.4650],
    'height_limit': 100  # meters
}

# Function to check if a point is within Waterloo zone
def is_in_waterloo_zone(lon, lat):
    point = Point(lon, lat)
    polygon = Polygon(WATERLOO_ZONE['coordinates'])
    return polygon.contains(point)

# Function to calculate distance to Waterloo center
def distance_to_waterloo(lon, lat):
    # Convert lat/lon to meters using geodesic distance
    geod = pyproj.Geod(ellps='WGS84')
    _, _, distance = geod.inv(
        WATERLOO_ZONE['center'][0],
        WATERLOO_ZONE['center'][1],
        lon,
        lat
    )
    return distance

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

# Function to rotate points around center
def rotate_points(points, angle_degrees, center):
    angle = np.radians(angle_degrees)
    cos_angle = np.cos(angle)
    sin_angle = np.sin(angle)
    
    rotated_points = []
    for point in points:
        px = point[0] - center[0]
        py = point[1] - center[1]
        rx = px * cos_angle - py * sin_angle
        ry = px * sin_angle + py * cos_angle
        rotated_points.append([rx + center[0], ry + center[1]])
    
    return rotated_points

# Title and description
st.title("ZoningLLM - 3D Building Visualizer")
st.markdown("Enter an address and building dimensions to visualize it on a map. Be aware of dimension restrictions.")

# Create tabs for different input methods
location_tab, coords_tab = st.tabs(["Search by Address", "Enter Coordinates"])

# Initialize session state
if 'latitude' not in st.session_state:
    st.session_state.latitude = 43.4650
if 'longitude' not in st.session_state:
    st.session_state.longitude = -80.5400
if 'formatted_address' not in st.session_state:
    st.session_state.formatted_address = "Waterloo, ON, Canada"
if 'rotation' not in st.session_state:
    st.session_state.rotation = 0

# Address input tab
with location_tab:
    col1, col2 = st.columns([6, 1])
    with col1:
        address = st.text_input("Enter Address", "Square One", label_visibility="visible")
    with col2:
        # Add some vertical padding to align with text input
        st.write("")  # Creates a small vertical space
        if st.button("Search", key="search_button", use_container_width=True):
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

# Check if location is in Waterloo zone
in_waterloo = is_in_waterloo_zone(st.session_state.longitude, st.session_state.latitude)

# Display current location and zone information
st.markdown("### Current Location")
st.markdown(f"**{st.session_state.formatted_address}**")
st.markdown(f"Coordinates: ({st.session_state.latitude:.6f}, {st.session_state.longitude:.6f})")
if in_waterloo:
    st.warning("⚠️ This location is within the Waterloo zone. Building height is limited to 100 meters.")

# Building dimensions and rotation
st.markdown("### Building Specifications")
col1, col2, col3, col4 = st.columns(4)

with col1:
    max_height = WATERLOO_ZONE['height_limit'] if in_waterloo else 1000
    height = st.number_input("Height (meters)", 
                        value=100.0,
                        min_value=1.0,
                        max_value=float(max_height),  # Convert max_height to float
                        help=f"Enter the building height in meters (max {max_height}m)")
with col2:
    length = st.number_input("Length (meters)", value=50.0, min_value=1.0,
                           help="Enter the building length in meters")
with col3:
    width = st.number_input("Width (meters)", value=30.0, min_value=1.0,
                          help="Enter the building width in meters")
with col4:
    rotation = st.slider("Rotation (degrees)", min_value=0, max_value=359, 
                        value=st.session_state.rotation,
                        help="Rotate building relative to true north")
    st.session_state.rotation = rotation

# Create building data
def create_building_data(lon, lat, height, length, width, rotation):
    meter_to_coord = 0.00001
    half_length = (length * meter_to_coord) / 2
    half_width = (width * meter_to_coord) / 2
    
    polygon = [
        [lon - half_width, lat - half_length],
        [lon + half_width, lat - half_length],
        [lon + half_width, lat + half_length],
        [lon - half_width, lat + half_length]
    ]
    
    center = [lon, lat]
    rotated_polygon = rotate_points(polygon, rotation, center)
    
    return pd.DataFrame({
        'polygon': [rotated_polygon],
        'height': [height]
    })

# Create Waterloo zone data
def create_zone_data():
    return pd.DataFrame({
        'polygon': [WATERLOO_ZONE['coordinates']],
        'height': [20]  # Height of zone visualization
    })

# Create the 3D visualization
def create_3d_map(building_data, center_lon, center_lat):
    # Building layer
    building_layer = pdk.Layer(
        'PolygonLayer',
        building_data,
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
    
    # Waterloo zone layer
    zone_layer = pdk.Layer(
        'PolygonLayer',
        create_zone_data(),
        get_polygon='polygon',
        get_elevation='height',
        elevation_scale=1,
        extruded=True,
        filled=True,
        wireframe=True,
        get_fill_color=[255, 0, 0, 50],  # Semi-transparent red
        get_line_color=[255, 0, 0],
        pickable=False
    )
    
    # Compass indicator
    compass_data = pd.DataFrame({
        'position': [[center_lon, center_lat]],
        'angle': [0]
    })
    
    compass_layer = pdk.Layer(
        'TextLayer',
        compass_data,
        get_position='position',
        get_text='N',
        get_angle='angle',
        get_size=18,
        get_color=[255, 0, 0],
        get_alignment_baseline="'bottom'",
        font_family='"Font Awesome 5 Free"'
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
        layers=[zone_layer, building_layer, compass_layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/dark-v10',
    )
    
    return deck

# Create and display the map
st.subheader("3D Visualization")
building_data = create_building_data(
    st.session_state.longitude,
    st.session_state.latitude,
    height,
    length,
    width,
    rotation
)
deck = create_3d_map(building_data, st.session_state.longitude, st.session_state.latitude)
st.pydeck_chart(deck)

# Add information about the visualization
with st.expander("About this visualization"):
    st.markdown(f"""
    This 3D building visualization shows your building at:
    - **Address**: {st.session_state.formatted_address}
    - **Coordinates**: ({st.session_state.latitude:.6f}°, {st.session_state.longitude:.6f}°)
    
    Building specifications:
    - Height: {height:.1f} meters {' (Limited by Waterloo zone)' if in_waterloo else ''}
    - Length: {length:.1f} meters
    - Width: {width:.1f} meters
    - Rotation: {rotation}° from true north
    
    Zone Information:
    - {'Location is within' if in_waterloo else 'Location is outside'} the Waterloo zone
    - Waterloo zone height limit: {WATERLOO_ZONE['height_limit']} meters
    
    The building is rendered on a dark-themed MapBox map, with the building shown as a 3D extrusion.
    The red semi-transparent zone indicates the Waterloo area with height restrictions.
    
    You can:
    - Rotate the view by holding right-click and dragging
    - Zoom with the scroll wheel
    - Pan by holding left-click and dragging
    - Adjust the building's rotation using the slider
    """)

# Footer
st.markdown("---")
st.markdown("Built by Rahul Kumar for ZoningLLM (WAT.ai)")