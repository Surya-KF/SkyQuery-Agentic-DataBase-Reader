document.addEventListener('DOMContentLoaded', function() {
    // Load all flights when the page loads
    loadFlights();

    // Add event listeners for the add flight form
    document.getElementById('add-flight-btn').addEventListener('click', function() {
        document.getElementById('add-flight-form').style.display = 'block';
    });

    document.getElementById('cancel-add').addEventListener('click', function() {
        document.getElementById('add-flight-form').style.display = 'none';
        document.getElementById('new-flight-form').reset();
    });

    // Add event listener for the cancel edit button
    document.getElementById('cancel-edit').addEventListener('click', function() {
        document.getElementById('edit-flight-form').style.display = 'none';
    });

    // Add event listener for the new flight form submission
    document.getElementById('new-flight-form').addEventListener('submit', function(e) {
        e.preventDefault();
        addNewFlight();
    });

    // Add event listener for the edit flight form submission
    document.getElementById('update-flight-form').addEventListener('submit', function(e) {
        e.preventDefault();
        updateFlight();
    });

    // Add event listeners for search and filter
    document.getElementById('search-flights').addEventListener('input', function() {
        filterFlights();
    });

    document.getElementById('filter-status').addEventListener('change', function() {
        filterFlights();
    });
});

// Function to load all flights from the server
function loadFlights() {
    fetch('/api/admin/flights')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch flights');
            }
            return response.json();
        })
        .then(data => {
            displayFlights(data.flights);
        })
        .catch(error => {
            console.error('Error loading flights:', error);
            alert('Failed to load flights. Please try again.');
        });
}

// Function to display flights in the table
function displayFlights(flights) {
    const tableBody = document.getElementById('flights-data');
    tableBody.innerHTML = '';

    if (flights.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="8" class="no-data">No flights found</td></tr>';
        return;
    }

    flights.forEach(flight => {
        const row = document.createElement('tr');
        
        // Format the departure time for display
        const departureTime = flight.departure_time || 'N/A';
        
        row.innerHTML = `
            <td>${flight.flight_number}</td>
            <td>${flight.airline || 'N/A'}</td>
            <td>${flight.origin || 'N/A'}</td>
            <td>${flight.destination || 'N/A'}</td>
            <td>${flight.departure_date || 'N/A'}</td>
            <td>${departureTime}</td>
            <td><span class="status-badge status-${flight.status?.toLowerCase().replace(/\s+/g, '-') || 'unknown'}">${flight.status || 'Unknown'}</span></td>
            <td class="action-buttons">
                <button class="edit-btn" onclick="editFlight('${flight.flight_number}')">Edit</button>
                <button class="delete-btn" onclick="deleteFlight('${flight.flight_number}')">Delete</button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
}

// Function to add a new flight
function addNewFlight() {
    const formData = new FormData(document.getElementById('new-flight-form'));
    const flightData = Object.fromEntries(formData.entries());
    
    fetch('/api/admin/flights', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(flightData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to add flight');
        }
        return response.json();
    })
    .then(data => {
        alert('Flight added successfully!');
        document.getElementById('add-flight-form').style.display = 'none';
        document.getElementById('new-flight-form').reset();
        loadFlights();
    })
    .catch(error => {
        console.error('Error adding flight:', error);
        alert('Failed to add flight. Please try again.');
    });
}

// Function to edit a flight
function editFlight(flightNumber) {
    fetch(`/api/admin/flights/${flightNumber}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch flight details');
            }
            return response.json();
        })
        .then(data => {
            const flight = data.flight;
            
            // Populate the edit form with flight data
            document.getElementById('edit_flight_id').value = flight.flight_number;
            document.getElementById('edit_flight_number').value = flight.flight_number;
            document.getElementById('edit_airline').value = flight.airline || '';
            document.getElementById('edit_departure_date').value = flight.departure_date || '';
            
            // Handle time format (HH:MM)
            if (flight.departure_time) {
                document.getElementById('edit_departure_time').value = flight.departure_time;
            }
            
                    document.getElementById('edit_origin').value = flight.origin || '';
                    document.getElementById('edit_destination').value = flight.destination || '';
                    document.getElementById('edit_status').value = flight.status || 'On Time';
                    document.getElementById('edit_terminal').value = flight.terminal || '';
            
                    // Show the edit form
                    document.getElementById('edit-flight-form').style.display = 'block';
                })
                .catch(error => {
                    console.error('Error fetching flight details:', error);
                    alert('Failed to load flight details. Please try again.');
                });
}

// Function to update a flight
function updateFlight() {
            const formData = new FormData(document.getElementById('update-flight-form'));
            const flightData = Object.fromEntries(formData.entries());
            const flightNumber = flightData.flight_id;
    
            fetch(`/api/admin/flights/${flightNumber}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(flightData)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to update flight');
                }
                return response.json();
            })
            .then(data => {
                alert('Flight updated successfully!');
                document.getElementById('edit-flight-form').style.display = 'none';
                loadFlights();
            })
            .catch(error => {
                console.error('Error updating flight:', error);
                alert('Failed to update flight. Please try again.');
            });
}

// Function to delete a flight
function deleteFlight(flightNumber) {
            if (confirm(`Are you sure you want to delete flight ${flightNumber}?`)) {
                fetch(`/api/admin/flights/${flightNumber}`, {
                    method: 'DELETE'
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Failed to delete flight');
                    }
                    return response.json();
                })
                .then(data => {
                    alert('Flight deleted successfully!');
                    loadFlights();
                })
                .catch(error => {
                    console.error('Error deleting flight:', error);
                    alert('Failed to delete flight. Please try again.');
                });
            }
}

// Function to filter flights based on search and status filter
function filterFlights() {
            const searchTerm = document.getElementById('search-flights').value.toLowerCase();
            const statusFilter = document.getElementById('filter-status').value;
    
            fetch('/api/admin/flights')
                .then(response => response.json())
                .then(data => {
                    let filteredFlights = data.flights;
            
                    // Apply search filter
                    if (searchTerm) {
                        filteredFlights = filteredFlights.filter(flight => 
                            flight.flight_number.toLowerCase().includes(searchTerm) ||
                            (flight.airline && flight.airline.toLowerCase().includes(searchTerm)) ||
                            (flight.origin && flight.origin.toLowerCase().includes(searchTerm)) ||
                            (flight.destination && flight.destination.toLowerCase().includes(searchTerm))
                        );
                    }
            
                    // Apply status filter
                    if (statusFilter) {
                        filteredFlights = filteredFlights.filter(flight => 
                            flight.status === statusFilter
                        );
                    }
            
                    displayFlights(filteredFlights);
                })
                .catch(error => {
                    console.error('Error filtering flights:', error);
                });
}