// DCA Portal functionality
let currentUser = null;
let selectedDCAId = null;

async function loadDCAPortal() {
    console.log('[DCA Portal] Initializing...');
    // Get current user info
    currentUser = JSON.parse(localStorage.getItem('user') || '{}');
    console.log('[DCA Portal] Current user:', currentUser);
    
    // If FedEx user, show DCA selector
    if (currentUser.role && currentUser.role.startsWith('fedex')) {
        console.log('[DCA Portal] FedEx user detected, loading DCA list...');
        document.getElementById('dca-selector').classList.remove('hidden');
        await loadDCAList();
    } else {
        console.log('[DCA Portal] DCA user detected, loading own portfolio...');
        // DCA users see their own data
        await Promise.all([
            loadPerformanceStats(),
            loadPortfolio()
        ]);
    }
}

async function loadDCAList() {
    console.log('[DCA List] Starting to load DCAs...');
    try {
        const response = await api.getDCAs();
        console.log('[DCA List] API response:', response);
        const select = document.getElementById('dca-select');
        console.log('[DCA List] Select element:', select);
        
        if (response.dcas && response.dcas.length > 0) {
            console.log(`[DCA List] Found ${response.dcas.length} DCAs, adding to dropdown...`);
            response.dcas.forEach(dca => {
                const option = document.createElement('option');
                option.value = dca.dca_id;
                option.textContent = `${dca.name} (${dca.dca_id})`;
                select.appendChild(option);
                console.log(`[DCA List] Added: ${dca.name} (${dca.dca_id})`);
            });
            console.log('[DCA List] Dropdown populated successfully');
        } else {
            console.warn('[DCA List] No DCAs found in response');
        }
    } catch (error) {
        console.error('[DCA List] Error loading DCA list:', error);
    }
}

async function loadSelectedDCA() {
    const select = document.getElementById('dca-select');
    selectedDCAId = select.value;
    
    if (!selectedDCAId) {
        alert('Please select a DCA first');
        return;
    }
    
    console.log('[DCA Portal] Loading portfolio for:', selectedDCAId);
    
    // Load data for selected DCA
    try {
        await Promise.all([
            loadPerformanceStats(selectedDCAId),
            loadPortfolio(null, null, selectedDCAId)
        ]);
        console.log('[DCA Portal] Portfolio loaded successfully');
    } catch (error) {
        console.error('[DCA Portal] Error loading portfolio:', error);
        alert('Failed to load DCA portfolio. Please try again.');
    }
}

async function loadPerformanceStats(dcaId = null) {
    try {
        const performance = await api.getDCAPerformance(dcaId);
        
        document.getElementById('active-cases').textContent = performance.active_cases || 0;
        document.getElementById('recovery-rate').textContent = `${(performance.recovery_rate || 0).toFixed(1)}%`;
        document.getElementById('performance-score').textContent = (performance.performance_score || 0).toFixed(1);
        document.getElementById('avg-time').textContent = `${(performance.avg_recovery_time || 0).toFixed(0)} days`;
    } catch (error) {
        console.error('Error loading performance stats:', error);
        // Display error state in UI
        document.getElementById('active-cases').textContent = '0';
        document.getElementById('recovery-rate').textContent = '0%';
        document.getElementById('performance-score').textContent = '0';
        document.getElementById('avg-time').textContent = '0 days';
    }
}

async function loadPortfolio(status = null, priority = null, dcaId = null) {
    try {
        // For FedEx users, add dca_id to the query
        let params = {};
        if (status) params.status = status;
        if (priority) params.priority = priority;
        if (dcaId) params.dca_id = dcaId;
        
        const queryString = new URLSearchParams(params).toString();
        console.log('[Portfolio] Query params:', params);
        console.log('[Portfolio] Full URL:', `/api/dca/portfolio?${queryString}`);
        
        const response = await fetch(`/api/dca/portfolio?${queryString}`, {
            headers: {
                'Authorization': `Bearer ${api.getToken()}`,
                'Content-Type': 'application/json'
            }
        }).then(res => res.json());
        
        console.log('[Portfolio] Response:', response);
        console.log('[Portfolio] Cases count:', response.cases ? response.cases.length : 0);
        
        const tbody = document.getElementById('portfolio-table');
        const countBadge = document.getElementById('case-count');
        
        if (!response.cases || response.cases.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="px-6 py-12 text-center">
                        <div class="flex flex-col items-center gap-3">
                            <div class="h-16 w-16 bg-slate-100 rounded-full flex items-center justify-center">
                                <i class="fas fa-inbox text-slate-300 text-3xl"></i>
                            </div>
                            <p class="text-slate-500 font-semibold">No cases assigned</p>
                            <p class="text-slate-400 text-sm">Cases will appear here once assigned to you</p>
                        </div>
                    </td>
                </tr>
            `;
            if (countBadge) countBadge.textContent = '0 cases';
            return;
        }
        
        if (countBadge) countBadge.textContent = `${response.cases.length} case${response.cases.length !== 1 ? 's' : ''}`;
        
        tbody.innerHTML = response.cases.map(c => `
            <tr class="hover:bg-slate-50/50 transition-colors duration-150">
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm font-bold text-slate-900">${c.case_id}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm text-slate-600 font-medium">${c.account_number}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm text-slate-600 font-medium">${c.customer_id || 'N/A'}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm font-extrabold text-slate-900">$${(c.amount || 0).toLocaleString()}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-3 py-1.5 text-xs font-bold rounded-xl ${getPriorityColor(c.priority)}">
                        ${getPriorityIcon(c.priority)}
                        ${(c.priority || 'N/A').toUpperCase()}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-3 py-1.5 text-xs font-bold rounded-xl ${getStatusColor(c.status)}">
                        ${getStatusIcon(c.status)}
                        ${formatStatus(c.status)}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm font-bold ${getSLAColor(c.sla_deadline)}">
                        ${formatSLA(c.sla_deadline)}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <div class="flex items-center gap-2">
                        <button onclick="viewCase('${c.case_id}')" class="h-9 w-9 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-lg transition-colors duration-150 flex items-center justify-center" title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button onclick="quickAction('${c.case_id}')" class="h-9 w-9 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-lg transition-colors duration-150 flex items-center justify-center" title="Quick Action">
                            <i class="fas fa-bolt"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading portfolio:', error);
        const tbody = document.getElementById('portfolio-table');
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="px-6 py-12 text-center">
                    <div class="flex flex-col items-center gap-3">
                        <div class="h-16 w-16 bg-red-100 rounded-full flex items-center justify-center">
                            <i class="fas fa-exclamation-triangle text-red-500 text-3xl"></i>
                        </div>
                        <p class="text-red-600 font-bold">Error loading cases</p>
                        <p class="text-slate-500 text-sm">${error.message || 'Please try again later'}</p>
                        <button onclick="loadPortfolio()" class="bg-red-500 hover:bg-red-600 text-white px-6 py-2 rounded-xl font-semibold text-sm mt-2">
                            <i class="fas fa-sync-alt mr-2"></i>Retry
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
}

function applyFilters() {
    const status = document.getElementById('status-filter').value;
    const priority = document.getElementById('priority-filter').value;
    loadPortfolio(status || null, priority || null, selectedDCAId);
}

function resetFilters() {
    document.getElementById('status-filter').value = '';
    document.getElementById('priority-filter').value = '';
    loadPortfolio(null, null, selectedDCAId);
}

function refreshPortfolio() {
    const status = document.getElementById('status-filter').value;
    const priority = document.getElementById('priority-filter').value;
    loadPortfolio(status || null, priority || null, selectedDCAId);
    loadPerformanceStats(selectedDCAId);
    
    // Update sync time
    const now = new Date();
    document.getElementById('last-sync-time').textContent = now.toLocaleTimeString();
}

function getPriorityColor(priority) {
    const colors = {
        'critical': 'bg-red-100 text-red-700',
        'high': 'bg-orange-100 text-orange-700',
        'medium': 'bg-yellow-100 text-yellow-700',
        'low': 'bg-green-100 text-green-700'
    };
    return colors[priority] || 'bg-slate-100 text-slate-700';
}

function getPriorityIcon(priority) {
    const icons = {
        'critical': '<i class="fas fa-exclamation-circle mr-1.5"></i>',
        'high': '<i class="fas fa-arrow-up mr-1.5"></i>',
        'medium': '<i class="fas fa-minus mr-1.5"></i>',
        'low': '<i class="fas fa-arrow-down mr-1.5"></i>'
    };
    return icons[priority] || '<i class="fas fa-circle mr-1.5"></i>';
}

function getStatusColor(status) {
    const colors = {
        'pending': 'bg-slate-100 text-slate-700',
        'assigned': 'bg-blue-100 text-blue-700',
        'in_progress': 'bg-purple-100 text-purple-700',
        'resolved': 'bg-green-100 text-green-700',
        'escalated': 'bg-red-100 text-red-700'
    };
    return colors[status] || 'bg-slate-100 text-slate-700';
}

function getStatusIcon(status) {
    const icons = {
        'pending': '<i class="fas fa-clock mr-1.5"></i>',
        'assigned': '<i class="fas fa-user-check mr-1.5"></i>',
        'in_progress': '<i class="fas fa-tasks mr-1.5"></i>',
        'resolved': '<i class="fas fa-check-circle mr-1.5"></i>',
        'escalated': '<i class="fas fa-exclamation-triangle mr-1.5"></i>'
    };
    return icons[status] || '<i class="fas fa-question-circle mr-1.5"></i>';
}

function formatStatus(status) {
    return (status || 'N/A').replace('_', ' ').toUpperCase();
}

function getSLAColor(deadline) {
    if (!deadline) return 'text-gray-500';
    
    const now = new Date();
    const slaDate = new Date(deadline);
    const hoursRemaining = (slaDate - now) / (1000 * 60 * 60);
    
    if (hoursRemaining < 0) return 'text-red-600 font-bold';
    if (hoursRemaining < 24) return 'text-orange-600';
    return 'text-green-600';
}

function formatSLA(deadline) {
    if (!deadline) return 'No SLA';
    
    const now = new Date();
    const slaDate = new Date(deadline);
    const hoursRemaining = (slaDate - now) / (1000 * 60 * 60);
    
    if (hoursRemaining < 0) {
        return `Breached ${Math.abs(hoursRemaining).toFixed(0)}h ago`;
    }
    
    if (hoursRemaining < 24) {
        return `${hoursRemaining.toFixed(0)}h left`;
    }
    
    const daysRemaining = Math.floor(hoursRemaining / 24);
    return `${daysRemaining}d left`;
}

function viewCase(caseId) {
    window.location.href = `case_view.html?id=${caseId}`;
}

async function quickAction(caseId) {
    const action = prompt('Quick Action:\n1 - Start Work\n2 - Contact Made\n3 - Payment Promised\n\nEnter action number:');
    
    if (!action) return;
    
    const actions = {
        '1': { type: 'started_work', desc: 'Started working on case' },
        '2': { type: 'contact_made', desc: 'Contact made with customer' },
        '3': { type: 'payment_promised', desc: 'Customer promised payment' }
    };
    
    const selectedAction = actions[action];
    if (!selectedAction) {
        alert('Invalid action');
        return;
    }
    
    try {
        await api.addCaseAction(caseId, selectedAction.type, selectedAction.desc);
        alert('Action recorded successfully');
        loadPortfolio();
    } catch (error) {
        alert('Error recording action: ' + error.message);
    }
}

// Initialize DCA portal on page load
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('dca_portal.html')) {
        loadDCAPortal();
        
        // Refresh every 30 seconds
        setInterval(loadPerformanceStats, 30000);
    }
});
