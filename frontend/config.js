// Backend API Configuration
// Only set backend URL for production (non-localhost environments)
if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    window.BACKEND_URL = 'https://collectflow-ai-powered-dca-management-ls10.onrender.com/api';
}
