document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('usernameForm');
    form.addEventListener('submit', function(event) {
        // Get the username value from the input field
        const username = document.getElementById('username').value;

        // Store the username in sessionStorage
        sessionStorage.setItem('username', username);

        // Allow the form to submit to the server
        // No `event.preventDefault()` here to allow form submission
    });
});

