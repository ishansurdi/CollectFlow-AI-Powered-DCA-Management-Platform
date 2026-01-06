// Dashboard functionality

let priorityChart, statusChart;

async function loadDashboard() {
    await Promise.all([
        loadKPIs(),
        loadCharts(),
        loadDCARankings(),
        loadRecentCases()
    ]);
}

async function loadKPIs() {
    try {
        const kpis = await api.getKPIs();
        
        document.getElementById('total-cases').textContent = kpis.total_cases || 0;
        document.getElementById('resolved-cases').textContent = kpis.resolved_cases || 0;
        document.getElementById('sla-breaches').textContent = kpis.sla_breaches || 0;
        document.getElementById('total-amount').textContent = `$${(kpis.total_amount_in_recovery || 0).toLocaleString()}`;
    } catch (error) {
        console.error('Error loading KPIs:', error);
    }
}

async function loadCharts() {
    try {
        const kpis = await api.getKPIs();
        
        // Priority Chart
        const priorityCtx = document.getElementById('priority-chart');
        if (priorityChart) priorityChart.destroy();
        
        priorityChart = new Chart(priorityCtx, {
            type: 'doughnut',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    data: [
                        kpis.priority_distribution?.critical || 0,
                        kpis.priority_distribution?.high || 0,
                        kpis.priority_distribution?.medium || 0,
                        kpis.priority_distribution?.low || 0
                    ],
                    backgroundColor: ['#ef4444', '#f97316', '#eab308', '#22c55e']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true
            }
        });
        
        // Status Chart
        const statusCtx = document.getElementById('status-chart');
        if (statusChart) statusChart.destroy();
        
        statusChart = new Chart(statusCtx, {
            type: 'bar',
            data: {
                labels: ['Pending', 'Assigned', 'In Progress', 'Resolved', 'Escalated'],
                datasets: [{
                    label: 'Cases',
                    data: [
                        kpis.status_distribution?.pending || 0,
                        kpis.status_distribution?.assigned || 0,
                        kpis.status_distribution?.in_progress || 0,
                        kpis.status_distribution?.resolved || 0,
                        kpis.status_distribution?.escalated || 0
                    ],
                    backgroundColor: '#8b5cf6'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading charts:', error);
    }
}

async function loadDCARankings() {
    try {
        const rankings = await api.getDCARankings();
        const container = document.getElementById('dca-rankings');
        
        if (!rankings.rankings || rankings.rankings.length === 0) {
            container.innerHTML = '<p class="text-slate-500 text-center py-8">No DCA data available</p>';
            return;
        }
        
        container.innerHTML = rankings.rankings.map((dca, index) => {
            const isFirst = index === 0;
            const barColor = isFirst ? '#4D148C' : index === 1 ? '#a78bfa' : '#94a3b8';
            const bgColor = isFirst ? 'purple-50' : 'slate-50';
            const borderColor = isFirst ? 'purple-100' : 'slate-100';
            const textColor = isFirst ? 'text-purple-700' : 'text-slate-600';
            const scoreColor = isFirst ? 'text-slate-900' : 'text-slate-500';
            const shadowStyle = isFirst ? 'box-shadow: 0 0 10px rgba(77,20,140,0.3);' : '';
            
            return `
                <div>
                    <div class="flex justify-between items-center mb-2">
                        <div class="flex items-center gap-3">
                            <div class="h-8 w-8 bg-${bgColor} ${textColor} font-black flex items-center justify-center rounded-lg text-sm border border-${borderColor}">${index + 1}</div>
                            <span class="text-xs font-extrabold text-slate-700">${dca.name}</span>
                        </div>
                        <span class="text-sm font-black ${scoreColor}">${dca.performance_score?.toFixed(1) || 0}</span>
                    </div>
                    <div class="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div class="h-full rounded-full" style="width: ${Math.min(dca.performance_score || 0, 100)}%; background-color: ${barColor}; ${shadowStyle}"></div>
                    </div>
                    <p class="text-xs text-slate-400 mt-1 font-bold">
                        Recovery: ${dca.recovery_rate?.toFixed(1) || 0}% • Cases: ${dca.current_cases || 0}/${dca.capacity || 0}
                    </p>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading DCA rankings:', error);
        document.getElementById('dca-rankings').innerHTML = '<p class="text-red-500 text-center py-8">Error loading rankings</p>';
    }
}

async function loadRecentCases() {
    const tbody = document.getElementById('cases-table');
    try {
        console.log('Loading recent cases...');
        console.log('API Base URL:', api.baseURL);
        console.log('Token:', api.getToken() ? 'Present' : 'Missing');
        
        // Build the full URL for debugging
        const filters = { limit: 10 };
        const params = new URLSearchParams(filters);
        const fullUrl = `${api.baseURL}/cases?${params}`;
        console.log('Full URL:', fullUrl);
        
        const response = await api.getCases(filters);
        console.log('Cases response:', response);
        
        if (!response || !response.cases || response.cases.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="px-6 py-4 text-center text-gray-500">No cases found</td></tr>';
            return;
        }
        
        tbody.innerHTML = response.cases.map(c => `
            <tr class="hover:bg-slate-50/80 transition-all group">
                <td class="px-8 py-6">
                    <div class="flex items-center gap-3">
                        <div class="h-2.5 w-2.5 rounded-full ${c.status === 'resolved' ? 'bg-green-500' : c.priority === 'critical' ? 'bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.4)]' : 'bg-slate-200'}"></div>
                        <span class="font-extrabold text-slate-900 text-sm">${c.case_id}</span>
                    </div>
                </td>
                <td class="px-8 py-6">
                    <p class="text-sm font-bold text-[#050B20]">${c.account_number}</p>
                    <p class="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">${c.customer_name || c.account_number || 'N/A'}</p>
                </td>
                <td class="px-8 py-6">
                    <p class="text-sm font-black text-slate-900 tracking-tight">$${(c.amount || 0).toLocaleString()}</p>
                    <p class="text-[10px] font-black ${c.priority === 'critical' ? 'text-red-500' : 'text-slate-400'} uppercase">${c.priority || 'N/A'}</p>
                </td>
                <td class="px-8 py-6">
                    <span class="status-pill inline-block ${getPriorityColorNew(c.priority)}">
                        ${c.priority || 'N/A'}
                    </span>
                </td>
                <td class="px-8 py-6">
                    <span class="status-pill inline-block ${getStatusColorNew(c.status)}">
                        ${c.status || 'N/A'}
                    </span>
                </td>
                <td class="px-8 py-6">
                    <div class="flex items-center gap-2">
                        <div class="h-6 w-6 rounded-md ${c.assigned_dca ? 'bg-purple-50 text-[#4D148C] border-purple-100' : 'bg-slate-100 text-slate-400 border-slate-200'} flex items-center justify-center text-[10px] font-black border">
                            ${c.assigned_dca ? c.assigned_dca.substring(0, 2).toUpperCase() : 'UN'}
                        </div>
                        <span class="text-xs font-bold text-slate-600">${c.assigned_dca || 'Unassigned'}</span>
                    </div>
                </td>
                <td class="px-8 py-6 text-right">
                    <button onclick="viewCase('${c.case_id}')" class="p-2 text-slate-300 hover:text-[#4D148C] hover:bg-purple-50 rounded-lg transition-all">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading cases:', error);
        console.error('Error details:', error.message, error.stack);
        tbody.innerHTML = 
            `<tr><td colspan="7" class="px-8 py-8 text-center text-red-500">Error loading cases: ${error.message}</td></tr>`;
    }
}

function getPriorityColorNew(priority) {
    const colors = {
        'critical': 'bg-red-100 text-red-700 border border-red-200',
        'high': 'bg-orange-100 text-orange-700 border border-orange-200',
        'medium': 'bg-yellow-100 text-yellow-700 border border-yellow-200',
        'low': 'bg-green-100 text-green-700 border border-green-200'
    };
    return colors[priority] || 'bg-slate-100 text-slate-500 border border-slate-200';
}

function getStatusColorNew(status) {
    const colors = {
        'pending': 'bg-slate-100 text-slate-500 border border-slate-200',
        'assigned': 'bg-blue-100 text-blue-700 border border-blue-200',
        'in_progress': 'bg-orange-100 text-orange-700 border border-orange-200',
        'resolved': 'bg-green-100 text-green-700 border border-green-200',
        'escalated': 'bg-red-100 text-red-700 border border-red-200'
    };
    return colors[status] || 'bg-slate-100 text-slate-500 border border-slate-200';
}

function viewCase(caseId) {
    window.location.href = `case_view.html?id=${caseId}`;
}

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('dashboard.html')) {
        console.log('Dashboard initializing...');
        console.log('API token:', api.getToken() ? 'Present' : 'Missing');
        console.log('User data:', localStorage.getItem('user'));
        
        loadDashboard();
        
        // Refresh every 30 seconds
        setInterval(loadKPIs, 30000);
    }
});

// Create Case Modal Functions
function showCreateCaseModal() {
    document.getElementById('createCaseModal').classList.remove('hidden');
}

function hideCreateCaseModal() {
    document.getElementById('createCaseModal').classList.add('hidden');
    document.getElementById('account-select').value = '';
    document.getElementById('priority-select').value = 'medium';
}

async function createNewCase() {
    const accountNumber = document.getElementById('account-select').value;
    const priority = document.getElementById('priority-select').value;
    
    if (!accountNumber) {
        alert('Please select an account');
        return;
    }
    
    try {
        const result = await api.createCase({ account_number: accountNumber, priority });
        alert(`Case ${result.case.case_id} created successfully!`);
        hideCreateCaseModal();
        loadRecentCases(); // Refresh the cases list
    } catch (error) {
        alert('Error creating case: ' + error.message);
    }
}
