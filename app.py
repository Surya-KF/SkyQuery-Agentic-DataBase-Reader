from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import json
import os
import re
from dotenv import load_dotenv
from together import Together
from pymongo import MongoClient
import urllib.parse
from datetime import datetime
import bcrypt
from functools import wraps

# Load environment variables
load_dotenv()
client = Together(api_key=os.getenv("TOGETHER_API_KEY"))

# MongoDB Connection Setup
MONGO_PASSWORD = urllib.parse.quote_plus(os.getenv("MONGO_PASSWORD"))
MONGO_URI = f"mongodb+srv://suryakf1974:{MONGO_PASSWORD}@cluster0.pgvt85f.mongodb.net/Flights?retryWrites=true&w=majority&appName=Cluster0"

# Initialize Flask app


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-for-sessions")

# User authentication functions
def get_db_connection():
    """Returns a connection to MongoDB"""
    return MongoClient(MONGO_URI)

def register_user(username, email, password):
    """Register a new user in the database"""
    try:
        mongo_client = get_db_connection()
        db = mongo_client["Flights"]
        users_collection = db["users"]
        
        # Check if username already exists
        if users_collection.find_one({"username": username}):
            return False, "Username already exists"
        
        # Check if email already exists
        if users_collection.find_one({"email": email}):
            return False, "Email already exists"
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user document
        user = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "role": "user",
            "created_at": datetime.now()
        }
        
        # Insert user into database
        users_collection.insert_one(user)
        return True, "User registered successfully"
    except Exception as e:
        print(f"Registration error: {e}")
        return False, "An error occurred during registration"
    finally:
        mongo_client.close()

def authenticate_user(username, password):
    """Authenticate a user with username and password"""
    try:
        mongo_client = get_db_connection()
        db = mongo_client["Flights"]
        users_collection = db["users"]
        
        # Find user by username
        user = users_collection.find_one({"username": username})
        
        if not user:
            return False, "Invalid username or password"
        
        # Check password
        if bcrypt.checkpw(password.encode('utf-8'), user['password']):
            # Return user data without password
            user_data = {
                "username": user["username"],
                "email": user.get("email", ""),
                "role": user.get("role", "user")
            }
            return True, user_data
        else:
            return False, "Invalid username or password"
    except Exception as e:
        print(f"Authentication error: {e}")
        return False, "An error occurred during authentication"
    finally:
        mongo_client.close()

# Create admin user if not exists
def create_admin_user():
    try:
        mongo_client = get_db_connection()
        db = mongo_client["Flights"]
        users_collection = db["users"]
        
        # Check if admin exists
        admin = users_collection.find_one({"username": "Admin"})
        
        if not admin:
            # Hash the password
            hashed_password = bcrypt.hashpw("Password@12345678910".encode('utf-8'), bcrypt.gensalt())
            
            # Create admin document
            admin_user = {
                "username": "Admin",
                "email": "admin@skybot.com",
                "password": hashed_password,
                "role": "admin",
                "created_at": datetime.now()
            }
            
            # Insert admin into database
            users_collection.insert_one(admin_user)
            print("Admin user created successfully")
    except Exception as e:
        print(f"Admin creation error: {e}")
    finally:
        mongo_client.close()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user'].get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

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

    """Generate a more conversational response based on the user query using LLM"""
    





    query_lower = user_query.lower()
    









    # First, check if it's a simple greeting or farewell to avoid unnecessary LLM calls
    greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]
    farewells = ["bye", "goodbye", "see you", "farewell", "exit", "quit"]
    help_queries = ["help", "what can you do", "how does this work", "instructions"]
    
    # Handle simple patterns without LLM
    if any(greeting in query_lower for greeting in greetings) and len(query_lower.split()) < 4:
        return {

            "answer": "Hello! I'm SkyBot, your flight information assistant. How can I help you today? You can ask me about flight status, departure times, or destinations."
        }










    elif any(farewell in query_lower for farewell in farewells) and len(query_lower.split()) < 4:
        return {

            "answer": "Thank you for using SkyBot! Have a safe journey and a wonderful day. Goodbye!"
        }



    elif any(help_query in query_lower for help_query in help_queries) and len(query_lower.split()) < 5:
        return {





            "answer": "I can help you find information about flights. Try asking questions like:<br>"
                     "- When does Flight AI123 depart?<br>"
                     "- What is the status of Flight EK500?<br>"
                     "- Tell me about Flight LH789<br>"
                     "- Show me flights to London<br>"
                     "Just make sure to include either a flight number or destination in your question!"
        }
    



    # For all other queries, first get the flight data
    flight_data_response = qa_agent_respond(user_query)
    
    # If we have flight data or a list of flights, use LLM to generate a contextual response
    if "flight_data" in flight_data_response or "flights_list" in flight_data_response:
        try:
            # Prepare the context for the LLM
            if "flight_data" in flight_data_response:
                flight_info = flight_data_response["flight_data"]
                context = f"Flight {flight_info['flight_number']} information: Departs at {flight_info['departure_time']} from {flight_info['origin']} to {flight_info['destination']}. Current status: {flight_info['status']}. Departure date: {flight_info.get('departure_date', 'Not specified')}. Airline: {flight_info.get('airline', 'Not specified')}."
            else:
                flights = flight_data_response["flights_list"]
                destination = flights[0]["destination"] if flights else "the requested destination"
                context = f"Found {len(flights)} flights to {destination}. "
                for i, flight in enumerate(flights[:5]):  # Limit to first 5 flights to avoid token limits
                    context += f"Flight {flight['flight_number']} departs at {flight['departure_time']} from {flight['origin']}. Status: {flight['status']}. "
                if len(flights) > 5:
                    context += f"And {len(flights) - 5} more flights. "
            
            # Call the LLM to generate a conversational response
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                messages=[
                    {"role": "system", 


                     "content": "You are SkyBot, a helpful and friendly flight information assistant. Respond conversationally to the user's query using the flight information provided. Make your response informative, natural, and engaging. Include all relevant flight details but in a conversational way. If appropriate, offer additional help or suggestions."},
                    {"role": "user", "content": f"User query: {user_query}\nFlight information: {context}"}
                ],
            )


            
            # Get the LLM's response
            llm_response = response.choices[0].message.content.strip()
            
            # Keep the original structured data for the frontend
            result = flight_data_response.copy()
            # Replace the answer with the LLM-generated response
            result["answer"] = llm_response
            return result
            
        except Exception as e:














            print(f"LLM response generation error: {e}")
            # Fall back to the original response if LLM fails
            return flight_data_response
    
    # For queries where we couldn't find flight data, also use LLM to generate a helpful response
    elif "answer" in flight_data_response and ("not found" in flight_data_response["answer"].lower() or 
                                              "no valid flight" in flight_data_response["answer"].lower()):
        try:
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                messages=[
                    {"role": "system", 
                     "content": "You are SkyBot, a helpful and friendly flight information assistant. The user asked about flight information, but no matching flights were found. Respond in a helpful, empathetic way, suggesting alternatives or clarifying what information you need."},
                    {"role": "user", "content": f"User query: {user_query}\nNo flight information found."}
                ],
            )
            






            llm_response = response.choices[0].message.content.strip()
            return {"answer": llm_response}
            














        except Exception as e:
            print(f"LLM error response generation error: {e}")
            # Fall back to the original response if LLM fails
            return flight_data_response
    
    # Return the original response for any other cases
    return flight_data_response

def add_flight(flight_data):
    """Add a new flight to the database"""
    try:
        mongo_client = get_db_connection()
        db = mongo_client["Flights"]
        flights_collection = db["flights"]
        
        # Check if flight number already exists
        if flights_collection.find_one({"flight_number": flight_data["flight_number"]}):
            return False, "Flight number already exists"
        
        # Insert flight into database
        flights_collection.insert_one(flight_data)
        return True, "Flight added successfully"
    except Exception as e:
        print(f"Add flight error: {e}")
        return False, f"An error occurred: {str(e)}"
    finally:
        mongo_client.close()

def update_flight(flight_number, updated_data):
    """Update an existing flight in the database"""
    try:
        mongo_client = get_db_connection()
        db = mongo_client["Flights"]
        flights_collection = db["flights"]
        
        # Check if flight exists
        if not flights_collection.find_one({"flight_number": flight_number}):
            return False, "Flight not found"
        
        # Update flight
        result = flights_collection.update_one(
            {"flight_number": flight_number},
            {"$set": updated_data}
        )
        
        if result.modified_count > 0:
            return True, "Flight updated successfully"
        else:
            return False, "No changes made to the flight"
    except Exception as e:
        print(f"Update flight error: {e}")
        return False, f"An error occurred: {str(e)}"
    finally:
        mongo_client.close()

def delete_flight(flight_number):
    """Delete a flight from the database"""
    try:
        mongo_client = get_db_connection()
        db = mongo_client["Flights"]
        flights_collection = db["flights"]
        
        # Check if flight exists
        if not flights_collection.find_one({"flight_number": flight_number}):
            return False, "Flight not found"
        
        # Delete flight
        result = flights_collection.delete_one({"flight_number": flight_number})
        
        if result.deleted_count > 0:
            return True, "Flight deleted successfully"
        else:
            return False, "Failed to delete flight"
    except Exception as e:
        print(f"Delete flight error: {e}")
        return False, f"An error occurred: {str(e)}"
    finally:
        mongo_client.close()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')
    

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Basic validation
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        # Register user
        success, message = register_user(username, email, password)
        
        if success:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Basic validation
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html')
        
        # Authenticate user
        success, user_data = authenticate_user(username, password)
        
        if success:
            # Store user in session
            session['user'] = user_data
            
            # Redirect to admin dashboard if admin
            if user_data.get('role') == 'admin':
                return redirect(url_for('admin_dashboard'))
            
            # Redirect to user dashboard
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('chatbot'))
        else:
            flash(user_data, 'error')  # user_data contains error message
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get today's flights
    today_flights = get_flights_for_today()
    return render_template('dashboard.html', flights=today_flights)

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # Get all flights for admin view
    all_flights = get_all_flights()
    return render_template('admin.html', flights=all_flights)

@app.route('/admin/flights/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_flight():
    if request.method == 'POST':
        # Get flight data from form
        flight_data = {
            "flight_number": request.form.get('flight_number'),
            "airline": request.form.get('airline'),
            "departure_date": request.form.get('departure_date'),
            "departure_time": request.form.get('departure_time'),
            "origin": request.form.get('origin'),
            "destination": request.form.get('destination'),
            "status": request.form.get('status', 'On Time')
        }
        
        # Basic validation
        if not all([flight_data["flight_number"], flight_data["airline"], 
                   flight_data["departure_date"], flight_data["departure_time"],
                   flight_data["origin"], flight_data["destination"]]):
            flash('All fields are required', 'error')
            return render_template('add_flight.html')
        
        # Add flight
        success, message = add_flight(flight_data)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash(message, 'error')
            return render_template('add_flight.html')
    
    return render_template('add_flight.html')

@app.route('/admin/flights/edit/<flight_number>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_flight(flight_number):
    # Get flight data
    flight_info = get_flight_info(flight_number)
    
    if flight_info.get('status') == 'Not Found':
        flash('Flight not found', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        # Get updated flight data from form
        updated_data = {
            "airline": request.form.get('airline'),
            "departure_date": request.form.get('departure_date'),
            "departure_time": request.form.get('departure_time'),
            "origin": request.form.get('origin'),
            "destination": request.form.get('destination'),
            "status": request.form.get('status')
        }
        
        # Update flight
        success, message = update_flight(flight_number, updated_data)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash(message, 'error')
            return render_template('edit_flight.html', flight=flight_info)
    
    return render_template('edit_flight.html', flight=flight_info)

@app.route('/admin/flights/delete/<flight_number>', methods=['POST'])
@login_required
@admin_required
def admin_delete_flight(flight_number):
    # Delete flight
    success, message = delete_flight(flight_number)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    user_message = request.json.get('message', '')
    print(f"Received message: {user_message}")  # Debug log
    
    # Generate response
    response = generate_chatbot_response(user_message)
    print(f"Generated response: {response}")  # Debug log
    
    return jsonify(response)

@app.route('/api/flights', methods=['GET'])
@login_required
def get_flights_api():
    """API endpoint to retrieve all flights."""
    flights = get_all_flights()
    if not flights:
        return jsonify({"message": "No flights found in the database."}), 404
    return jsonify({"flights": flights}), 200

@app.route('/about')
def about():
    """Render the about page"""
    return render_template('about.html')
# Initialize admin user when the app starts


def initialize_app():
    create_admin_user()

if __name__ == '__main__':
    with app.app_context():
        create_admin_user()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
