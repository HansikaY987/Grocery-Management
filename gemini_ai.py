import os
import logging
import requests
from typing import List, Dict, Any

from models import Product

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Gemini API key (inserted directly as requested)
GEMINI_API_KEY = "AIzaSyAiIFLLvo1AziQQjaDdBSz11c_c_bIngAQ"

# Gemini API endpoint
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent"


def extract_text_from_response(response_data: dict) -> str:
    """
    Safely extract the generated text from the Gemini API response.
    """
    try:
        candidates = response_data.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
    except Exception as e:
        logger.error(f"Error extracting Gemini API response text: {e}")
    return ""


def get_ai_response(query: str) -> str:
    """
    Get a response from Gemini AI for a user query.
    """
    if not GEMINI_API_KEY:
        logger.warning("Gemini API key is missing.")
        return "I'm currently unable to respond. Please try again later."

    prompt = (
        "You are a helpful AI assistant for a grocery and pharmacy app. "
        "Provide accurate information about groceries, medicines, interactions, and health advice. "
        "If you're unsure, say so clearly.\n\nUser query: " + query)

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(f"{GEMINI_API_ENDPOINT}?key={GEMINI_API_KEY}",
                                 json=payload,
                                 headers={"Content-Type": "application/json"})

        if response.status_code == 200:
            response_data = response.json()
            logger.debug(f"Gemini API response: {response_data}")
            result_text = extract_text_from_response(response_data)
            return result_text or "I couldn't find an appropriate response. Try again later."
        else:
            logger.error(
                f"Gemini API error {response.status_code}: {response.text}")
            return "There was a problem generating a response. Please try again."
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return "An unexpected error occurred. Please try again later."


def check_medical_interactions(products: List[Product]) -> Dict[str, Any]:
    """
    Check for potential drug interactions among pharmacy products.
    """
    if not products:
        return {"status": "safe", "interactions": []}

    pharmacy_products = []
    for product in products:
        try:
            if getattr(product.category, 'is_pharmacy', False):
                pharmacy_products.append(product)
        except Exception as e:
            logger.error(f"Product category check failed: {e}")

    if len(pharmacy_products) <= 1:
        return {"status": "safe", "interactions": []}

    medication_names = [p.name for p in pharmacy_products]
    warnings = [
        p.medical_warnings for p in pharmacy_products if p.medical_warnings
    ]

    if not GEMINI_API_KEY:
        logger.warning("Gemini API key is missing.")
        return {
            "status":
            "caution",
            "interactions": [
                "Multiple medicines detected. Please consult a doctor for advice."
            ]
        }

    prompt = (
        f"As a healthcare AI assistant, analyze the following medications for possible interactions:\n\n"
        f"Medications: {', '.join(medication_names)}\n"
        f"Known warnings: {warnings if warnings else 'No specific warnings provided.'}\n\n"
        "List any potential drug interactions. If none, state clearly that no known interactions exist."
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(f"{GEMINI_API_ENDPOINT}?key={GEMINI_API_KEY}",
                                 json=payload,
                                 headers={"Content-Type": "application/json"})

        if response.status_code == 200:
            response_data = response.json()
            logger.debug(f"Gemini interaction check response: {response_data}")
            result_text = extract_text_from_response(response_data)

            if "no known significant interactions" in result_text.lower():
                return {
                    "status": "safe",
                    "interactions": ["No significant interactions detected."]
                }

            interactions = [
                line.strip() for line in result_text.split('\n')
                if line.strip()
            ]
            return {
                "status":
                "warning" if interactions else "safe",
                "interactions":
                interactions or ["No significant interactions found."]
            }

        else:
            logger.error(
                f"Gemini API error {response.status_code}: {response.text}")
            return {
                "status":
                "error",
                "interactions": [
                    "Unable to check interactions. Please consult a healthcare provider."
                ]
            }

    except Exception as e:
        logger.error(f"Exception during interaction check: {e}")
        return {
            "status":
            "error",
            "interactions":
            ["System error. Please consult your doctor for safety."]
        }
