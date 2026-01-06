// Authentication Functions

function checkAuth() {
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    
    if (!token) {
        // Redirect to login if not on login page
        if (!window.location.pathname.includes('index.html') && !window.location.pathname.endsWith('/')) {
            window.location.href = 'index.html';
        }
        return null;
    }
    
    return user;
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    api.clearToken();
    window.location.href = 'index.html';
}

function goBack() {
    const user = checkAuth();
    if (user) {
        if (user.role.startsWith('dca')) {
            window.location.href = 'dca_portal.html';
        } else {
            window.location.href = 'dashboard.html';
        }
    }
}

// Login page script
if (document.getElementById('login-form')) {
    const form = document.getElementById('login-form');
    const errorDiv = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const loginBtn = document.getElementById('login-btn');
        
        // Disable button and show loading
        loginBtn.disabled = true;
        loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Signing in...';
        errorDiv.classList.add('hidden');
        
        try {
            const response = await api.login(email, password);
            
            // Store token and user data
            api.setToken(response.token);
            localStorage.setItem('user', JSON.stringify(response.user));
            
            // Redirect based on role
            if (response.user.role.startsWith('dca')) {
                window.location.href = 'dca_portal.html';
            } else {
                window.location.href = 'dashboard.html';
            }
        } catch (error) {
            errorText.textContent = error.message || 'Login failed. Please try again.';
            errorDiv.classList.remove('hidden');
            
            loginBtn.disabled = false;
            loginBtn.innerHTML = '<i class="fas fa-sign-in-alt mr-2"></i>Sign In';
        }
    });
}

// Display user name in navigation
function displayUserName() {
    const user = checkAuth();
    if (user && document.getElementById('user-name')) {
        document.getElementById('user-name').textContent = user.name || user.email;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Check if on a protected page (not login)
    if (!window.location.pathname.includes('index.html') && !window.location.pathname.endsWith('/')) {
        const user = checkAuth();
        if (!user) {
            return; // checkAuth already redirects
        }
        displayUserName();
    }
});
