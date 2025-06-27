import os
import requests
import logging
from typing import Tuple

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Google Geocoding API key
GOOGLE_MAPS_API_KEY ='AIzaSyCFhD2MFRsgeCUvqQMjmr5cGEk9NH0xQYg'

def get_coordinates_from_address(address: str) -> Tuple[float, float]:
    """
    Convert an address string to geographical coordinates using Google Geocoding API.
    
    Args:
        address: The delivery address as a string
        
    Returns:
        A tuple (latitude, longitude)
        
    Raises:
        Exception: If geocoding fails
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("Google Maps API key not found in environment variables")
        raise ValueError("Google Maps API key is not configured")
    
    try:
        # Format the URL
        endpoint = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": address,
            "key": GOOGLE_MAPS_API_KEY
        }
        
        # Make the request
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            if data["status"] == "OK":
                # Extract coordinates from the first result
                location = data["results"][0]["geometry"]["location"]
                latitude = location["lat"]
                longitude = location["lng"]
                
                logger.debug(f"Geocoded address '{address}' to coordinates ({latitude}, {longitude})")
                return latitude, longitude
            else:
                logger.error(f"Geocoding error: {data['status']}")
                raise ValueError(f"Geocoding failed: {data['status']}")
        else:
            logger.error(f"Geocoding API error: {response.status_code}, {response.text}")
            raise Exception(f"Geocoding API error: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Exception in geocoding: {str(e)}")
        raise Exception(f"Failed to geocode address: {str(e)}")

def get_distance_between_coordinates(origin: Tuple[float, float], destination: Tuple[float, float]) -> float:
    """
    Calculate distance between two coordinate pairs using Google Distance Matrix API.
    
    Args:
        origin: Tuple of (latitude, longitude) for the origin point
        destination: Tuple of (latitude, longitude) for the destination point
        
    Returns:
        Distance in kilometers
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("Google Maps API key not found in environment variables")
        return -1  # Indicate error
    
    try:
        # Format origin and destination
        origin_str = f"{origin[0]},{origin[1]}"
        dest_str = f"{destination[0]},{destination[1]}"
        
        # Format the URL
        endpoint = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": origin_str,
            "destinations": dest_str,
            "key": GOOGLE_MAPS_API_KEY
        }
        
        # Make the request
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            if data["status"] == "OK":
                # Extract distance value
                distance_data = data["rows"][0]["elements"][0]
                
                if distance_data["status"] == "OK":
                    distance_km = distance_data["distance"]["value"] / 1000  # Convert meters to km
                    return distance_km
                else:
                    logger.error(f"Distance calculation error: {distance_data['status']}")
                    return -1
            else:
                logger.error(f"Distance Matrix API error: {data['status']}")
                return -1
        else:
            logger.error(f"Distance Matrix API error: {response.status_code}, {response.text}")
            return -1
            
    except Exception as e:
        logger.error(f"Exception in distance calculation: {str(e)}")
        return -1
