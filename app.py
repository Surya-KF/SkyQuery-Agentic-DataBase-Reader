from flask import Flask, render_template, request, jsonify
import json
import os
import re
from dotenv import load_dotenv
from together import Together
from pymongo import MongoClient
import urllib.parse
from datetime import datetime

# Load environment variables
load_dotenv()
client = Together(api_key=os.getenv("TOGETHER_API_KEY"))

# MongoDB Connection Setup
MONGO_PASSWORD = urllib.parse.quote_plus(os.getenv("MONGO_PASSWORD"))
MONGO_URI = f"mongodb+srv://suryakf1974:{MONGO_PASSWORD}@cluster0.pgvt85f.mongodb.net/Flights?retryWrites=true&w=majority&appName=Cluster0"

# Initialize Flask app
app = Flask(__name__)

def get_flight_info(flight_number: str) -> dict:
    """Retrieves structured flight data for a given flight number from MongoDB."""
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client["Flights"]
        flights_collection = db["flights"]

        # Query MongoDB for flight info
        flight_info = flights_collection.find_one({"flight_number": flight_number})

        if flight_info:
            # Remove MongoDB's internal '_id' field and return the data
            flight_info.pop('_id', None)
            return flight_info
        return {"flight_number": flight_number, "status": "Not Found"}

    except Exception as e:
        print(f"MongoDB query failed: {e}")
        return {"flight_number": flight_number, "status": "Not Found"}
    finally:
        mongo_client.close()

def get_flights_by_destination(destination: str) -> list:
    """Retrieves all flights going to a specific destination."""
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client["Flights"]
        flights_collection = db["flights"]

        # Query MongoDB for flights with the given destination
        # Using case-insensitive exact match
        flights = list(flights_collection.find(
            {"destination": {"$regex": f"^{destination}$", "$options": "i"}}
        ))

        # If exact match returns no results, try partial match
        if not flights:
            flights = list(flights_collection.find(
                {"destination": {"$regex": destination, "$options": "i"}}
            ))

        # Remove MongoDB's internal '_id' field from each document
        for flight in flights:
            if '_id' in flight:
                flight.pop('_id', None)
        
        # Debug output to console
        print(f"Found {len(flights)} flights to {destination}: {flights}")
        
        return flights
    except Exception as e:
        print(f"MongoDB query failed: {e}")
        return []
    finally:
        if 'mongo_client' in locals():
            mongo_client.close()

def get_all_flights() -> list:
    """Retrieves all flight data from the database."""
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client["Flights"]
        flights_collection = db["flights"]

        # Fetch all flights
        flights = list(flights_collection.find())

        # Remove MongoDB's internal '_id' field from each document
        for flight in flights:
            flight.pop('_id', None)

        return flights
    except Exception as e:
        print(f"MongoDB query failed: {e}")
        return []
    finally:
        mongo_client.close()

def get_flights_for_today() -> list:
    """Retrieves all flights departing today from the database."""
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client["Flights"]
        flights_collection = db["flights"]

        # Get today's date in the format YYYY-MM-DD
        today = datetime.now().strftime('%Y-%m-%d')

        # Query flights with today's departure date
        flights = list(flights_collection.find({"departure_date": today}))

        # Remove MongoDB's internal '_id' field from each document
        for flight in flights:
            flight.pop('_id', None)

        return flights
    except Exception as e:
        print(f"MongoDB query failed: {e}")
        return []
    finally:
        mongo_client.close()

def info_agent_request(flight_number: str) -> str:
    """Calls get_flight_info and returns the data as a JSON string."""
    flight_info = get_flight_info(flight_number)
    return json.dumps(flight_info)

def extract_flight_number(text: str) -> str:
    """Extracts a flight number using regex."""
    match = re.search(r"\b([A-Z]{2,3}\d{2,4})\b", text)
    return match.group(1) if match else None

def extract_destination(text: str) -> str:
    """Attempts to extract a destination from the query using AI."""
    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
            messages=[
                {"role": "system",
                "content": "Extract the destination city or airport from the query. If there is no destination mentioned, respond with 'NONE'."},
                {"role": "user", "content": text},
            ],
        )
        destination = response.choices[0].message.content.strip()
        if not destination or destination == "NONE":
            print("No destination found in the query.")  # Debugging line
            return None
        return destination
    except Exception as e:
        print(f"Together AI API error: {e}")
        return None

def qa_agent_respond(user_query: str) -> dict:
    """Processes user query, extracts flight number, and returns structured flight info."""
    
    # Check if query is about flights to a destination
    destination_keywords = ["flights to", "flying to", "travel to", "planes to", "airlines to", "to"]
    is_destination_query = any(keyword in user_query.lower() for keyword in destination_keywords)
    
    if is_destination_query:
        # Extract destination
        destination = extract_destination(user_query)
        if destination:
            print(f"Extracted destination: {destination}")  # Debug log
            
            # Get flights to that destination
            flights = get_flights_by_destination(destination)
            print(f"Found {len(flights)} flights to {destination}")  # Debug log
            
            if not flights:
                return {
                    "answer": f"Sorry, I couldn't find any flights to {destination} in our database. Please try a different destination."
                }
                
            flights_info = "\n".join([
                f"Flight {flight['flight_number']} to {flight['destination']} departs at {flight['departure_time']}. Status: {flight['status']}"
                for flight in flights
            ])
            formatted_flights_info = flights_info.replace('\n', '<br>')
            
            # Handle singular vs plural correctly
            if len(flights) == 1:
                return {
                    "answer": f"I found 1 flight to {destination}:<br><br>{formatted_flights_info}",
                    "flights_list": flights
                }
            else:
                return {
                    "answer": f"I found {len(flights)} flights to {destination}:<br><br>{formatted_flights_info}",
                    "flights_list": flights
                }
    
    # Normal flight number query processing
    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
            messages=[
                {"role": "system",
                "content": "Extract the flight number from the query and return ONLY the flight number."},
                {"role": "user", "content": user_query},
            ],
        )
        flight_number = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Together AI API error: {e}")
        flight_number = None

    # If AI fails, use regex extraction
    if not flight_number or not re.match(r"^[A-Z]{2,3}\d{2,4}$", flight_number):
        flight_number = extract_flight_number(user_query)

    # If no valid flight number is found
    if not flight_number:
        return {"answer": "No valid flight number found in your query. Please provide a flight number in the format like 'AI123' or 'EK500'."}

    # Get flight info from Info Agent
    flight_info_json = info_agent_request(flight_number)
    flight_info = json.loads(flight_info_json)

    # Handle "Not Found" case
    if flight_info.get("status") == "Not Found":
        return {"answer": f"Flight {flight_number} not found in our database. Please check the flight number and try again."}

    # Construct structured response
    return {
        "answer": f"Flight {flight_info['flight_number']} departs at {flight_info['departure_time']} "
                f"to {flight_info['destination']}. Current status: {flight_info['status']}.",
        "flight_data": flight_info
    }

def generate_chatbot_response(user_query: str) -> dict:
    """Generate a more conversational response based on the user query"""
    
    # Check if it's a greeting or farewell
    greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]
    farewells = ["bye", "goodbye", "see you", "farewell", "exit", "quit"]
    help_queries = ["help", "what can you do", "how does this work", "instructions"]
    
    query_lower = user_query.lower()
    
    # Handle greetings
    if any(greeting in query_lower for greeting in greetings) and not any(kw in query_lower for kw in ["flights", "delhi", "dubai", "frankfurt"]):
        return {
            "answer": "Hello! I'm SkyBot, your flight information assistant. How can I help you today? You can ask me about flight status, departure times, or destinations."
        }
    
    # Handle farewells
    elif any(farewell in query_lower for farewell in farewells):
        return {
            "answer": "Thank you for using SkyBot! Have a safe journey and a wonderful day. Goodbye!"
        }
    
    # Handle help requests
    elif any(help_query in query_lower for help_query in help_queries):
        return {
            "answer": "I can help you find information about flights. Try asking questions like:<br>"
                     "- When does Flight AI123 depart?<br>"
                     "- What is the status of Flight EK500?<br>"
                     "- Tell me about Flight LH789<br>"
                     "- Show me flights to London<br>"
                     "Just make sure to include either a flight number or destination in your question!"
        }
    
    # Check if it's likely a flight query (either by number or destination)
    else:
        # Log the query
        print(f"Processing flight query: {query_lower}")
        return qa_agent_respond(user_query)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    print(f"Received message: {user_message}")  # Debug log
    
    # Generate response
    response = generate_chatbot_response(user_message)
    print(f"Generated response: {response}")  # Debug log
    
    return jsonify(response)

@app.route('/api/flights', methods=['GET'])
def get_flights():
    """API endpoint to retrieve all flights."""
    flights = get_all_flights()
    if not flights:
        return jsonify({"message": "No flights found in the database."}), 404
    return jsonify({"flights": flights}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))