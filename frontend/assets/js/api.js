// API Configuration
// Use environment variable for production, default to relative path for local development
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? '/api' 
    : (window.BACKEND_URL || '/api');

// API Client Class
class APIClient {
    constructor() {
        this.baseURL = API_BASE_URL;
        this.token = localStorage.getItem('token');
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('token', token);
    }

    getToken() {
        return this.token || localStorage.getItem('token');
    }

    clearToken() {
        this.token = null;
        localStorage.removeItem('token');
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.getToken()) {
            headers['Authorization'] = `Bearer ${this.getToken()}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // Helper methods for common HTTP methods
    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    // Auth endpoints
    async login(email, password) {
        return this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
    }

    async verifyToken() {
        return this.request('/auth/verify');
    }

    // Case endpoints
    async getCases(filters = {}) {
        const params = new URLSearchParams(filters);
        return this.request(`/cases?${params}`);
    }

    async getCase(caseId) {
        return this.request(`/cases/${caseId}`);
    }

    async createCase(data) {
        return this.request('/cases', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateCaseStatus(caseId, status, notes) {
        return this.request(`/cases/${caseId}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status, notes })
        });
    }

    async addCaseNote(caseId, note) {
        return this.request(`/cases/${caseId}/notes`, {
            method: 'POST',
            body: JSON.stringify({ note })
        });
    }

    async addCaseAction(caseId, actionType, description, amount = 0) {
        return this.request(`/cases/${caseId}/actions`, {
            method: 'POST',
            body: JSON.stringify({ action_type: actionType, description, amount })
        });
    }

    async escalateCase(caseId, reason) {
        return this.request(`/cases/${caseId}/escalate`, {
            method: 'POST',
            body: JSON.stringify({ reason })
        });
    }

    // DCA endpoints
    async getDCAPortfolio(status = null, priority = null) {
        const params = new URLSearchParams();
        if (status) params.append('status', status);
        if (priority) params.append('priority', priority);
        return this.request(`/dca/portfolio?${params}`);
    }

    async getDCAPerformance(dcaId = null) {
        const params = dcaId ? `?dca_id=${dcaId}` : '';
        return this.request(`/dca/performance${params}`);
    }

    async getDCAs(status = null) {
        const params = status ? `?status=${status}` : '';
        return this.request(`/dca/list${params}`);
    }

    // Dashboard endpoints
    async getKPIs() {
        return this.request('/dashboard/kpis');
    }

    async getTrends(days = 30) {
        return this.request(`/dashboard/trends?days=${days}`);
    }

    async getDCARankings() {
        return this.request('/dashboard/dca-rankings');
    }

    async getActivityFeed(limit = 50) {
        return this.request(`/dashboard/activity-feed?limit=${limit}`);
    }

    async getAlerts() {
        return this.request('/dashboard/alerts');
    }

    async getBusinessMetrics() {
        return this.request('/dashboard/business-metrics');
    }

    async getPortfolioAnalytics() {
        return this.request('/dashboard/portfolio-analytics');
    }

    // AI endpoints
    async predictRecovery(accountNumber) {
        return this.request('/ai/predict-recovery', {
            method: 'POST',
            body: JSON.stringify({ account_number: accountNumber })
        });
    }

    async recommendDCA(caseId) {
        return this.request('/ai/recommend-dca', {
            method: 'POST',
            body: JSON.stringify({ case_id: caseId })
        });
    }

    // Agent endpoints
    async getAgentStatus() {
        return this.request('/agents/status');
    }

    async triggerAgent(agentName) {
        return this.request(`/agents/trigger/${agentName}`, {
            method: 'POST'
        });
    }

    async getAgentActivity(limit = 20) {
        return this.request(`/agents/activity?limit=${limit}`);
    }
}

// Create global API instance
const api = new APIClient();
