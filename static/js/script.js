// static/js/script.js
document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    // Function to add a message to the chat
    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'avatar';
        
        const avatarIcon = document.createElement('i');
        avatarIcon.className = isUser ? 'fas fa-user' : 'fas fa-robot';
        avatarDiv.appendChild(avatarIcon);
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'content';
        
        // Handle HTML content from server (for <br> tags)
        contentDiv.innerHTML = message;
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        chatMessages.appendChild(messageDiv);
        
        // Scroll to the bottom of the chat
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Function to display flight data in a nice card format
    function displayFlightData(flightData) {
        let statusClass = '';
        
        if (flightData.status.toLowerCase() === 'on time') {
            statusClass = 'status-on-time';
        } else if (flightData.status.toLowerCase() === 'delayed') {
            statusClass = 'status-delayed';
        } else if (flightData.status.toLowerCase() === 'boarding') {
            statusClass = 'status-boarding';
        }
        
        return `
            <div class="flight-card">
                <div class="flight-header">
                    <span class="flight-number">${flightData.flight_number}</span>
                    <span class="flight-status ${statusClass}">${flightData.status}</span>
                </div>
                <div class="flight-details">
                    <div class="flight-destination">
                        <i class="fas fa-plane-arrival"></i> ${flightData.destination}
                    </div>
                    <div class="flight-time">
                        <i class="far fa-clock"></i> ${flightData.departure_time}
                    </div>
                </div>
            </div>
        `;
    }

    // Function to display multiple flights
    function displayFlightsList(flights) {
        let html = '';
        
        flights.forEach(flight => {
            html += displayFlightData(flight);
        });
        
        return html;
    }

    // Function to send a message to the server
    function sendMessage() {
        const message = userInput.value.trim();
        
        if (message === '') return;
        
        // Add user message to chat
        addMessage(message, true);
        
        // Clear input field
        userInput.value = '';
        
        // Show loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot-message';
        loadingDiv.innerHTML = `
            <div class="avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="content">
                <p><i class="fas fa-spinner fa-spin"></i> Searching for flight information...</p>
            </div>
        `;
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Send request to server
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message }),
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading indicator
            chatMessages.removeChild(loadingDiv);
            
            // Add bot response
            let responseHTML = data.answer;
            
            // If there's flight data, display it in a card
            if (data.flight_data) {
                responseHTML += displayFlightData(data.flight_data);
            }
            
            // If there's a list of flights, display them
            if (data.flights_list && data.flights_list.length > 0) {
                responseHTML += displayFlightsList(data.flights_list);
            }
            
            addMessage(responseHTML);
        })
        .catch(error => {
            // Remove loading indicator
            chatMessages.removeChild(loadingDiv);
            
            // Show error message
            addMessage('Sorry, there was an error processing your request. Please try again.');
            console.error('Error:', error);
        });
    }

    // Function to handle suggestion clicks
    function sendSuggestion(suggestion) {
        userInput.value = suggestion;
        sendMessage();
    }

    // Event listener for send button
    sendButton.addEventListener('click', sendMessage);

    // Event listener for Enter key
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Make sendSuggestion available globally
    window.sendSuggestion = sendSuggestion;
});