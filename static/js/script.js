// static/js/script.js
document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    // Function to add a message to the chat
    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        
        if (isUser) {
            messageDiv.classList.add('user-message');
            messageDiv.innerHTML = `
                <div class="avatar">
                    <i class="fas fa-user"></i>
                </div>
                <div class="content">
                    <p>${message}</p>
                </div>
            `;
        } else {
            messageDiv.classList.add('bot-message');
            messageDiv.innerHTML = `
                <div class="avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="content">
                    <p>${message}</p>
                </div>
            `;
        }
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Function to handle sending a message
    function sendMessage() {
        const message = userInput.value.trim();
        
        if (message) {
            // Add user message to chat
            addMessage(message, true);
            
            // Clear input field
            userInput.value = '';
            
            // Show loading indicator
            const loadingDiv = document.createElement('div');
            loadingDiv.classList.add('message', 'bot-message', 'loading-message');
            loadingDiv.innerHTML = `
                <div class="avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="content">
                    <p>Thinking...</p>
                </div>
            `;
            chatMessages.appendChild(loadingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Send message to server
            fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: message })
            })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 401) {
                        // Redirect to login if unauthorized
                        window.location.href = '/login';
                        throw new Error('Please login to continue');
                    }
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Remove loading message
                chatMessages.removeChild(loadingDiv);
                
                // Add bot response to chat
                addMessage(data.answer);
                
                // If there's flight data, display it in a card
                if (data.flight_data) {
                    displayFlightCard(data.flight_data);
                }
                
                // If there's a flights list, display them
                if (data.flights_list && data.flights_list.length > 0) {
                    data.flights_list.forEach(flight => {
                        displayFlightCard(flight);
                    });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                
                // Remove loading message
                if (document.querySelector('.loading-message')) {
                    chatMessages.removeChild(loadingDiv);
                }
                
                // Add error message
                addMessage('Sorry, I encountered an error. Please try again later.');
            });
        }
    }

    // Function to display a flight card
    function displayFlightCard(flightData) {
        const flightCard = document.createElement('div');
        flightCard.classList.add('message', 'bot-message');
        
        // Determine status class
        let statusClass = 'status-on-time';
        if (flightData.status) {
            const status = flightData.status.toLowerCase();
            if (status.includes('delay')) {
                statusClass = 'status-delayed';
            } else if (status.includes('board')) {
                statusClass = 'status-boarding';
            } else if (status.includes('cancel')) {
                statusClass = 'status-cancelled';
            }
        }
        
        flightCard.innerHTML = `
            <div class="avatar">
                <i class="fas fa-plane"></i>
            </div>
            <div class="content">
                <div class="flight-card">
                    <div class="flight-header">
                        <span class="flight-number">${flightData.flight_number}</span>
                        <span class="flight-status ${statusClass}">${flightData.status}</span>
                    </div>
                    <div class="flight-details">
                        <div class="flight-destination">
                            <i class="fas fa-map-marker-alt"></i> ${flightData.origin || 'N/A'} → ${flightData.destination || 'N/A'}
                        </div>
                        <div class="flight-time">
                            <i class="far fa-clock"></i> ${flightData.departure_time || 'N/A'}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        chatMessages.appendChild(flightCard);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Event listener for send button
    sendButton.addEventListener('click', sendMessage);

    // Event listener for Enter key
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Function to handle suggestion clicks
    function sendSuggestion(suggestion) {
        userInput.value = suggestion;
        sendMessage();
    }

    // Make sendSuggestion available globally
    window.sendSuggestion = sendSuggestion;
});