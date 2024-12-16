document.addEventListener('DOMContentLoaded', function() {
    const username = sessionStorage.getItem('username');

    if (username) {
        document.getElementById('displayUsername').textContent = username;
    } else {
        window.location.href = 'login.html'; // Redirect to login if no username
    }
});
