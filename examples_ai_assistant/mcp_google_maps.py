"""
MCP Google Maps Example

Get directions and location information using Google Maps MCP server.

Setup:
    1. Get Google Maps API key from https://console.cloud.google.com
    2. export GOOGLE_MAPS_API_KEY="your_key"
    3. python mcp_google_maps.py
"""

import asyncio
import os
from aeon import Agent


class GoogleMapsHelper:
    """Help with location queries using Google Maps MCP"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_directions(self, origin: str, destination: str) -> dict:
        """Get directions between two places"""
        print(f"  Getting directions from {origin} to {destination}")
        
        # Simulate API response
        return {
            "distance": "5.2 miles",
            "duration": "12 minutes",
            "route": "via Main St",
            "steps": [
                "Head east on First Ave",
                "Turn right onto Main St",
                "Turn left onto Second Ave",
                "Arrive at destination"
            ]
        }

    async def find_nearby(self, location: str, place_type: str = "coffee") -> list:
        """Find nearby places"""
        print(f"  Finding {place_type} shops near {location}")
        
        # Simulate API response
        places = {
            "coffee": [
                {"name": "Brew Haven", "distance": "0.1 mi", "rating": 4.8},
                {"name": "Java Express", "distance": "0.3 mi", "rating": 4.6},
                {"name": "The Daily Grind", "distance": "0.5 mi", "rating": 4.5},
            ],
            "restaurant": [
                {"name": "Italian Kitchen", "distance": "0.2 mi", "rating": 4.7},
                {"name": "Sushi Palace", "distance": "0.4 mi", "rating": 4.9},
                {"name": "Burger Barn", "distance": "0.6 mi", "rating": 4.3},
            ]
        }
        
        return places.get(place_type, [])

    async def get_location_info(self, location: str) -> dict:
        """Get information about a location"""
        print(f"  Getting info about {location}")
        
        return {
            "coordinates": "40.7128°N, 74.0060°W",
            "timezone": "America/New_York",
            "country": "USA",
            "region": "New York"
        }


async def main():
    print("=" * 60)
    print("Æon Framework - Google Maps Location Helper")
    print("=" * 60)

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "demo_key")
    
    # Initialize agent
    agent = Agent(
        name="LocationAssistant",
        model="ollama/phi3.5",
        protocols=[]
    )

    # Initialize Google Maps helper
    maps = GoogleMapsHelper(api_key=api_key)

    # Example 1: Get directions
    print("\\n[1] Getting Directions")
    print("-" * 60)
    directions = await maps.get_directions("New York", "Boston")
    print(f"Distance: {directions['distance']}")
    print(f"Duration: {directions['duration']}")
    print(f"Route: {directions['route']}")
    print("Steps:")
    for i, step in enumerate(directions['steps'], 1):
        print(f"  {i}. {step}")

    # Example 2: Find nearby places
    print("\\n[2] Finding Nearby Coffee Shops")
    print("-" * 60)
    coffee_shops = await maps.find_nearby("New York", "coffee")
    for shop in coffee_shops:
        print(f"  {shop['name']}: {shop['distance']} away (★{shop['rating']})")

    # Example 3: Get location info
    print("\\n[3] Location Information")
    print("-" * 60)
    info = await maps.get_location_info("New York")
    print(f"Coordinates: {info['coordinates']}")
    print(f"Timezone: {info['timezone']}")
    print(f"Country: {info['country']}")

    # Example 4: AI-powered recommendation
    print("\\n[4] AI Travel Recommendation")
    print("-" * 60)
    
    prompt = """Based on these nearby places:
    - Brew Haven (4.8 rating, 0.1 mi)
    - Java Express (4.6 rating, 0.3 mi)
    - The Daily Grind (4.5 rating, 0.5 mi)
    
    Which coffee shop would you recommend and why?"""
    
    recommendation = agent.cortex.plan_action(
        system_prompt=agent.system_prompt,
        user_input=prompt,
        tools=[]
    )
    print(recommendation)

    # Example 5: Multi-step travel planning
    print("\\n[5] Travel Planning with AI")
    print("-" * 60)
    
    directions_info = f"""
    From NYC to Boston:
    - Distance: {directions['distance']}
    - Duration: {directions['duration']}
    - Route: {directions['route']}
    """
    
    prompt = f"""Based on this travel information:
    {directions_info}
    
    Suggest:
    1. Best time to leave
    2. Places to stop for breaks
    3. What to bring
    4. Estimated cost
    
    Keep it practical and friendly."""
    
    travel_plan = agent.cortex.plan_action(
        system_prompt=agent.system_prompt,
        user_input=prompt,
        tools=[]
    )
    print(travel_plan)


if __name__ == "__main__":
    asyncio.run(main())
