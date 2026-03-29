import asyncio
import json
import logging

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=GEMINI_API_KEY)

EXTRACT_PROMPT = """You are a real estate data extractor for Indian property markets.
The user will send ONE message containing a broker's details and one or more property listings.

Extract:
1. broker_name: the broker's full name
2. broker_phone: 10-digit Indian mobile number (strip +91 or leading 0)
3. society_name: the society/project name. IMPORTANT: you will be given a list of existing
   society names from the database. If the society in the message is clearly the same as one
   in the list (e.g. "Logix Blossom County sector 137" matches "Logix Blossom County"),
   use the EXISTING name from the list. Only use a new name if there is no match.
4. listings: an array of objects, one per distinct flat/unit. Each listing has:
   - config: BHK type normalized. Rules:
     * Basic: "3 BHK"/"3bhk" -> "3BHK"
     * Plus study/+1 means a half BHK: "2+1"/"2 plus 1"/"2BHK+study"/"2.5BHK" -> "2.5BHK", "3+1"/"3BHK+study" -> "3.5BHK"
     * Plus servant is a distinct suffix, NOT a half BHK: "2BHK+servant"/"2bhk plus servant" -> "2BHK+Servant", "3BHK+servant" -> "3BHK+Servant"
     * Combinations: "3+1+servant"/"3BHK+study+servant" -> "3.5BHK+Servant"
   - area_sqft: area in sqft (integer), or null if not mentioned
   - price_lakh: price in lakhs (numeric). Convert: "85 lakh"->85, "85L"->85, "1.2 cr"->120, "1.2 crore"->120. null if not mentioned.
   - floor: floor info as-is string ("4th", "ground", "12-15"), or null
   - facing: facing direction, or null
   - notes: any other relevant detail, or null. IMPORTANT: if the message contains text
     enclosed in single quotes (e.g. 'some note here'), that text MUST be included in the
     notes field for the listing it relates to (append to any other notes).

Return a JSON object:
{
  "broker_name": "...",
  "broker_phone": "...",
  "society_name": "...",
  "listings": [ { "config": "...", "area_sqft": ..., "price_lakh": ..., "floor": ..., "facing": ..., "notes": ... } ]
}

If the text has nothing to do with real estate, return: {"broker_name":null,"broker_phone":null,"society_name":null,"listings":[]}

Return ONLY the JSON object. No markdown, no explanation."""


async def extract_listings(message: str, existing_societies: list[str]) -> dict:
    """Extract broker info and all listings from a single message."""
    societies_str = ", ".join(existing_societies) if existing_societies else "(none yet)"
    prompt = (
        f"Existing societies in DB: [{societies_str}]\n\n"
        f"Message:\n{message}\n\n"
        "Extract broker details plus all property listings as JSON."
    )
    logger.info("[GEMINI] Calling %s | %d chars", GEMINI_MODEL, len(message))

    response = await asyncio.to_thread(
        _client.models.generate_content,
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=EXTRACT_PROMPT,
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )
    result = json.loads(response.text)
    listing_count = len(result.get("listings", []))
    logger.info("[GEMINI] -> broker=%s, society=%s, %d listing(s)",
                result.get("broker_name"), result.get("society_name"), listing_count)
    return result
