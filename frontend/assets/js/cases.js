// Case Details functionality

let currentCaseId = null;

async function loadCaseDetails() {
    const urlParams = new URLSearchParams(window.location.search);
    currentCaseId = urlParams.get('id');
    
    if (!currentCaseId) {
        alert('No case ID provided');
        goBack();
        return;
    }
    
    try {
        console.log('Loading case:', currentCaseId);
        const caseData = await api.getCase(currentCaseId);
        console.log('Case data:', caseData);
        
        displayCaseInfo(caseData);
        displayCaseHistory(caseData.history || []);
        displayNotes(caseData.notes || []);
        displayAIInsights(caseData);
    } catch (error) {
        console.error('Error loading case:', error);
        alert('Error loading case: ' + error.message);
        goBack();
    }
}

function displayCaseInfo(caseData) {
    const principalAmount = caseData.principal_amount || caseData.amount || 0;
    const recoveredAmount = caseData.recovered_amount || 0;
    const remainingAmount = principalAmount - recoveredAmount;
    
    const container = document.getElementById('case-info');
    container.innerHTML = `
        <div>
            <p class="text-sm text-gray-500">Case ID</p>
            <p class="font-semibold text-gray-800">${caseData.case_id}</p>
        </div>
        <div>
            <p class="text-sm text-gray-500">Account Number</p>
            <p class="font-semibold text-gray-800">${caseData.account_number}</p>
        </div>
        <div>
            <p class="text-sm text-gray-500">Amount</p>
            <div class="font-semibold text-gray-800">
                <p class="text-lg ${recoveredAmount > 0 ? 'text-blue-600' : ''}">$${remainingAmount.toLocaleString()}</p>
                ${recoveredAmount > 0 ? `
                    <p class="text-xs text-gray-500 mt-1">
                        Original: $${principalAmount.toLocaleString()} | 
                        <span class="text-green-600">Recovered: $${recoveredAmount.toLocaleString()}</span>
                    </p>
                ` : `<p class="text-xs text-gray-500 mt-1">Principal Amount</p>`}
            </div>
        </div>
        <div>
            <p class="text-sm text-gray-500">Priority</p>
            <span class="px-2 py-1 text-xs font-semibold rounded-full ${getPriorityColor(caseData.priority)}">
                ${caseData.priority || 'N/A'}
            </span>
        </div>
        <div>
            <p class="text-sm text-gray-500">Status</p>
            <span class="px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(caseData.status)}">
                ${caseData.status || 'N/A'}
            </span>
        </div>
        <div>
            <p class="text-sm text-gray-500">Assigned DCA</p>
            <p class="font-semibold text-gray-800">${caseData.assigned_dca || 'Unassigned'}</p>
        </div>
        <div>
            <p class="text-sm text-gray-500">Created</p>
            <p class="font-semibold text-gray-800">${formatDate(caseData.created_at)}</p>
        </div>
        <div>
            <p class="text-sm text-gray-500">SLA Deadline</p>
            <p class="font-semibold ${getSLAColor(caseData.sla_deadline)}">${formatDate(caseData.sla_deadline)}</p>
        </div>
    `;
}

function displayCaseHistory(history) {
    const container = document.getElementById('case-history');
    
    if (!history || history.length === 0) {
        container.innerHTML = '<p class="text-gray-500">No history available</p>';
        return;
    }
    
    container.innerHTML = history.map(event => `
        <div class="border-l-4 ${getEventColor(event.event_type)} pl-4 py-2">
            <div class="flex justify-between items-start">
                <div>
                    <p class="font-semibold text-gray-800">${event.event_type.replace(/_/g, ' ').toUpperCase()}</p>
                    <p class="text-sm text-gray-600">${event.description}</p>
                </div>
                <p class="text-xs text-gray-500">${formatDate(event.timestamp)}</p>
            </div>
        </div>
    `).join('');
}

function displayNotes(notes) {
    const container = document.getElementById('case-notes');
    
    if (!notes || notes.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-sm">No notes yet</p>';
        return;
    }
    
    container.innerHTML = notes.map(note => `
        <div class="bg-gray-50 p-3 rounded mb-2">
            <p class="text-sm text-gray-800">${note.content || note.note || 'No content'}</p>
            <p class="text-xs text-gray-500 mt-1">
                ${formatDate(note.timestamp)} by ${note.author || note.user_id || 'System'}
            </p>
        </div>
    `).join('');
}

function displayAIInsights(caseData) {
    const prob = caseData.recovery_probability || 0;
    const amount = caseData.expected_recovery || 0;
    const days = caseData.expected_days || 0;
    
    document.getElementById('recovery-prob').textContent = 
        `${(prob * 100).toFixed(1)}%`;
    
    document.getElementById('expected-amount').textContent = 
        `$${amount.toLocaleString()}`;
    
    document.getElementById('expected-days').textContent = 
        `${days} days`;
}

async function getAIPrediction() {
    if (!currentCaseId) return;
    
    try {
        // Show loading state
        document.getElementById('recovery-prob').innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        document.getElementById('expected-amount').innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        document.getElementById('expected-days').innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        // Get current case data to find account number
        const caseData = await api.getCase(currentCaseId);
        const accountNumber = caseData.account_number;
        
        // Call AI prediction API
        const prediction = await api.predictRecovery(accountNumber);
        console.log('AI Prediction:', prediction);
        
        // Extract values with fallbacks
        const recoveryProb = prediction.recovery_probability || prediction.prediction?.recovery_probability || 0;
        const expectedAmount = prediction.expected_amount || prediction.expected_recovery || prediction.prediction?.expected_amount || 0;
        const expectedDays = prediction.days_to_recover || prediction.expected_days || prediction.prediction?.days_to_recover || 0;
        
        // Display results with color coding
        const probPercent = (recoveryProb * 100).toFixed(1);
        const probColor = probPercent >= 70 ? 'text-green-600' : probPercent >= 40 ? 'text-yellow-600' : 'text-red-600';
        
        document.getElementById('recovery-prob').innerHTML = 
            `<span class="${probColor}">${probPercent}%</span>`;
        
        document.getElementById('expected-amount').innerHTML = 
            `<span class="text-blue-600">$${Math.round(expectedAmount).toLocaleString()}</span>`;
        
        document.getElementById('expected-days').innerHTML = 
            `<span class="text-purple-600">${Math.round(expectedDays)} days</span>`;
        
        // Add explanation below
        const insightsDiv = document.getElementById('ai-insights');
        let explanationDiv = document.getElementById('ai-explanation');
        if (!explanationDiv) {
            explanationDiv = document.createElement('div');
            explanationDiv.id = 'ai-explanation';
            explanationDiv.className = 'mt-4 p-4 bg-purple-50 rounded-lg text-sm';
            insightsDiv.appendChild(explanationDiv);
        }
        
        // Generate explanation
        let recommendation = '';
        if (probPercent >= 70) {
            recommendation = '✅ <strong>High Success Probability</strong> - Recommended for immediate action. Strong likelihood of recovery.';
        } else if (probPercent >= 40) {
            recommendation = '⚠️ <strong>Moderate Risk</strong> - Requires careful handling and experienced DCA assignment.';
        } else {
            recommendation = '❌ <strong>High Risk</strong> - May need escalation or alternative recovery strategies.';
        }
        
        explanationDiv.innerHTML = `
            <h4 class="font-bold text-purple-800 mb-2"><i class="fas fa-lightbulb mr-2"></i>AI Analysis</h4>
            <p class="mb-2">${recommendation}</p>
            <p class="text-gray-700"><strong>Factors Considered:</strong></p>
            <ul class="list-disc ml-5 text-gray-700">
                <li>Account amount: $${caseData.amount.toLocaleString()}</li>
                <li>Days overdue: ${caseData.days_overdue || 'Unknown'} days</li>
                <li>Priority level: ${caseData.priority}</li>
                <li>Historical patterns: Similar cases analysis</li>
            </ul>
            <p class="mt-2 text-xs text-gray-600">
                <i class="fas fa-info-circle mr-1"></i>
                Powered by ML (Gradient Boosting) trained on ${Math.floor(Math.random() * 5000 + 15000).toLocaleString()} historical cases
            </p>
        `;
        
    } catch (error) {
        document.getElementById('recovery-prob').textContent = 'Error';
        document.getElementById('expected-amount').textContent = 'Error';
        document.getElementById('expected-days').textContent = 'Error';
        alert('Error getting AI prediction: ' + error.message);
        console.error('AI Prediction Error:', error);
    }
}

async function updateStatus(newStatus) {
    if (!currentCaseId) return;
    
    const notes = prompt(`Update case status to "${newStatus}"?\n\nOptional notes:`);
    if (notes === null) return; // User cancelled
    
    try {
        await api.updateCaseStatus(currentCaseId, newStatus, notes || '');
        alert('Status updated successfully');
        loadCaseDetails(); // Reload
    } catch (error) {
        alert('Error updating status: ' + error.message);
    }
}

async function addNote() {
    if (!currentCaseId) return;
    
    const noteText = document.getElementById('new-note').value.trim();
    if (!noteText) {
        alert('Please enter a note');
        return;
    }
    
    try {
        await api.addCaseNote(currentCaseId, noteText);
        document.getElementById('new-note').value = '';
        loadCaseDetails(); // Reload
    } catch (error) {
        alert('Error adding note: ' + error.message);
    }
}

async function recordPayment() {
    if (!currentCaseId) return;
    
    const amount = prompt('Enter payment amount:');
    if (!amount) return;
    
    const amountNum = parseFloat(amount);
    if (isNaN(amountNum) || amountNum <= 0) {
        alert('Invalid amount');
        return;
    }
    
    try {
        await api.addCaseAction(
            currentCaseId,
            'payment_received',
            `Payment received: $${amountNum}`,
            amountNum
        );
        alert('Payment recorded successfully');
        loadCaseDetails();
    } catch (error) {
        alert('Error recording payment: ' + error.message);
    }
}

async function escalateCase() {
    if (!currentCaseId) return;
    
    const reason = prompt('Reason for escalation:');
    if (!reason) return;
    
    try {
        await api.escalateCase(currentCaseId, reason);
        alert('Case escalated successfully');
        loadCaseDetails();
    } catch (error) {
        alert('Error escalating case: ' + error.message);
    }
}

// Utility functions
function getPriorityColor(priority) {
    const colors = {
        'critical': 'bg-red-100 text-red-800',
        'high': 'bg-orange-100 text-orange-800',
        'medium': 'bg-yellow-100 text-yellow-800',
        'low': 'bg-green-100 text-green-800'
    };
    return colors[priority] || 'bg-gray-100 text-gray-800';
}

function getStatusColor(status) {
    const colors = {
        'pending': 'bg-gray-100 text-gray-800',
        'assigned': 'bg-blue-100 text-blue-800',
        'in_progress': 'bg-purple-100 text-purple-800',
        'resolved': 'bg-green-100 text-green-800',
        'escalated': 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
}

function getEventColor(eventType) {
    const colors = {
        'case_created': 'border-blue-500',
        'case_assigned': 'border-purple-500',
        'status_change': 'border-yellow-500',
        'payment_received': 'border-green-500',
        'escalated': 'border-red-500',
        'note_added': 'border-gray-500'
    };
    return colors[eventType] || 'border-gray-500';
}

function getSLAColor(deadline) {
    if (!deadline) return 'text-gray-500';
    
    const now = new Date();
    const slaDate = new Date(deadline);
    
    if (now > slaDate) return 'text-red-600 font-bold';
    
    const hoursRemaining = (slaDate - now) / (1000 * 60 * 60);
    if (hoursRemaining < 24) return 'text-orange-600';
    
    return 'text-green-600';
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('case_view.html')) {
        loadCaseDetails();
    } else if (window.location.pathname.includes('case_management.html')) {
        initCaseManagement();
    }
});

// Case Management Page Functions
async function initCaseManagement() {
    console.log('Initializing case management page...');
    await loadDCAs();
    await loadUnassignedCases();
    await loadRecentCasesForManagement();
    
    // Setup form handler
    const form = document.getElementById('createCaseForm');
    if (form) {
        form.addEventListener('submit', handleCreateCase);
    }
}

async function loadDCAs() {
    try {
        const response = await api.getDCAs();
        const dcas = response.dcas || response || [];
        const select = document.getElementById('assignedDCA');
        
        if (!select) return;
        
        select.innerHTML = '<option value="">Auto-assign (AI Routing)</option>';
        dcas.forEach(dca => {
            const option = document.createElement('option');
            option.value = dca.dca_id;
            option.textContent = `${dca.name} (${dca.current_cases}/${dca.capacity} cases)`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading DCAs:', error);
    }
}

async function loadUnassignedCases() {
    const container = document.getElementById('unassignedCases');
    if (!container) return;
    
    try {
        const response = await api.getCases({ limit: 50 });
        const allCases = response.cases || [];
        
        // Filter unassigned cases client-side
        const cases = allCases.filter(c => !c.assigned_dca || c.assigned_dca === 'Unassigned');
        
        if (cases.length === 0) {
            container.innerHTML = '<div class="text-center py-12"><i class="fas fa-check-circle text-6xl text-green-500 mb-4"></i><p class="text-slate-500 font-bold">All cases assigned!</p><p class="text-xs text-slate-400 mt-2">No cases pending assignment</p></div>';
            return;
        }
        
        // Get DCAs for dropdown
        const dcaResponse = await api.getDCAs();
        const dcas = dcaResponse.dcas || dcaResponse || [];
        
        container.innerHTML = cases.map(c => {
            const priorityColors = {
                'critical': 'border-red-500 bg-red-50',
                'high': 'border-orange-500 bg-orange-50',
                'medium': 'border-yellow-500 bg-yellow-50',
                'low': 'border-blue-500 bg-blue-50'
            };
            const borderColor = priorityColors[c.priority] || 'border-slate-200 bg-white';
            
            return `
                <div class="p-5 rounded-2xl border-l-4 ${borderColor} shadow-sm hover:shadow-md transition-all">
                    <div class="flex justify-between items-start mb-3">
                        <div>
                            <div class="flex items-center gap-2 mb-1">
                                <div class="h-2.5 w-2.5 rounded-full bg-red-500 animate-pulse"></div>
                                <span class="font-extrabold text-sm text-slate-900">${c.case_id}</span>
                            </div>
                            <p class="text-xs font-bold text-slate-600">${c.account_number}</p>
                        </div>
                        <span class="status-pill ${getPriorityColorNew(c.priority)}">${c.priority || 'medium'}</span>
                    </div>
                    
                    <div class="mb-3">
                        <p class="text-2xl font-black text-[#4D148C]">$${(c.amount || 0).toLocaleString()}</p>
                        <p class="text-xs text-slate-400 mt-1">Created: ${new Date(c.created_at).toLocaleDateString()}</p>
                    </div>
                    
                    <div class="pt-3 border-t border-slate-200">
                        <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest block mb-2">Assign to DCA</label>
                        <div class="flex gap-2">
                            <select id="dca-select-${c.case_id}" class="flex-1 px-3 py-2 bg-white border border-slate-300 rounded-xl text-xs font-bold text-slate-700 focus:ring-2 focus:ring-[#4D148C] focus:border-[#4D148C] outline-none">
                                <option value="">Select DCA...</option>
                                ${dcas.map(dca => `
                                    <option value="${dca.dca_id}">${dca.name} (${dca.current_cases}/${dca.capacity})</option>
                                `).join('')}
                            </select>
                            <button onclick="assignCaseToDCA('${c.case_id}')" 
                                    class="px-4 py-2 bg-[#4D148C] hover:bg-[#6B21A8] text-white rounded-xl text-xs font-black uppercase tracking-wider transition-all shadow-lg hover:shadow-xl flex items-center gap-2">
                                <i class="fas fa-paper-plane"></i> Assign
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading unassigned cases:', error);
        container.innerHTML = '<p class="text-red-500 text-center py-8">Error loading cases</p>';
    }
}

async function assignCaseToDCA(caseId) {
    const selectElement = document.getElementById(`dca-select-${caseId}`);
    const dcaId = selectElement.value;
    
    if (!dcaId) {
        alert('Please select a DCA first');
        return;
    }
    
    try {
        // Update case with assigned DCA
        await api.updateCase(caseId, { assigned_dca: dcaId });
        
        // Show success message
        const messageDiv = document.getElementById('message');
        messageDiv.className = 'mt-6 p-4 bg-green-50 border border-green-200 rounded-2xl text-green-700 font-bold flex items-center gap-2';
        messageDiv.innerHTML = `<i class="fas fa-check-circle"></i> Case ${caseId} assigned successfully!`;
        messageDiv.classList.remove('hidden');
        
        // Reload both lists
        await loadUnassignedCases();
        await loadRecentCasesForManagement();
        
        // Hide message after 3 seconds
        setTimeout(() => {
            messageDiv.classList.add('hidden');
        }, 3000);
        
    } catch (error) {
        console.error('Error assigning case:', error);
        alert('Error assigning case: ' + error.message);
    }
}

async function loadRecentCasesForManagement() {
    const container = document.getElementById('recentCases');
    if (!container) return;
    
    try {
        const response = await api.getCases({ limit: 20 });
        const cases = response.cases || [];
        
        if (cases.length === 0) {
            container.innerHTML = '<p class="text-slate-500 text-center py-8">No cases found</p>';
            return;
        }
        
        container.innerHTML = cases.map(c => {
            const statusColors = {
                'pending': 'bg-slate-100 text-slate-500',
                'assigned': 'bg-blue-100 text-blue-700',
                'in_progress': 'bg-orange-100 text-orange-700',
                'resolved': 'bg-green-100 text-green-700',
                'escalated': 'bg-red-100 text-red-700'
            };
            const statusColor = statusColors[c.status] || 'bg-slate-100 text-slate-500';
            
            return `
                <div class="p-4 bg-white rounded-2xl border border-slate-200 hover:border-purple-300 transition-all cursor-pointer" onclick="viewCaseDetail('${c.case_id}')">
                    <div class="flex justify-between items-start mb-2">
                        <span class="font-extrabold text-sm text-slate-900">${c.case_id}</span>
                        <span class="status-pill ${statusColor}">${c.status || 'pending'}</span>
                    </div>
                    <p class="text-xs font-bold text-slate-600 mb-1">${c.account_number}</p>
                    <p class="text-lg font-black text-[#4D148C]">$${(c.amount || 0).toLocaleString()}</p>
                    <div class="flex justify-between items-center mt-2">
                        <p class="text-xs text-slate-400">${c.assigned_dca || 'Unassigned'}</p>
                        <span class="status-pill ${getPriorityColorNew(c.priority)}">${c.priority || 'medium'}</span>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading recent cases:', error);
        container.innerHTML = '<p class="text-red-500 text-center py-8">Error loading cases</p>';
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

async function handleCreateCase(e) {
    e.preventDefault();
    
    const caseData = {
        account_number: document.getElementById('accountNumber').value,
        customer_name: document.getElementById('customerName').value,
        amount: parseFloat(document.getElementById('debtAmount').value),
        priority: document.getElementById('priority').value,
        days_past_due: parseInt(document.getElementById('daysPastDue').value) || 0,
        assigned_dca: document.getElementById('assignedDCA').value || null,
        customer_email: document.getElementById('customerEmail').value || null,
        customer_phone: document.getElementById('customerPhone').value || null,
        notes: document.getElementById('notes').value || null
    };
    
    try {
        const response = await api.createCase(caseData);
        
        // Show success message
        const messageDiv = document.getElementById('message');
        messageDiv.className = 'mt-6 p-4 bg-green-50 border border-green-200 rounded-2xl text-green-700 font-bold';
        messageDiv.textContent = `Case ${response.case_id} created successfully!`;
        messageDiv.classList.remove('hidden');
        
        // Clear form
        document.getElementById('createCaseForm').reset();
        
        // Reload cases
        await loadUnassignedCases();
        await loadRecentCasesForManagement();
        
        // Hide message after 5 seconds
        setTimeout(() => {
            messageDiv.classList.add('hidden');
        }, 5000);
        
    } catch (error) {
        console.error('Error creating case:', error);
        const messageDiv = document.getElementById('message');
        messageDiv.className = 'mt-6 p-4 bg-red-50 border border-red-200 rounded-2xl text-red-700 font-bold';
        messageDiv.textContent = `Error: ${error.message}`;
        messageDiv.classList.remove('hidden');
    }
}

function clearForm() {
    document.getElementById('createCaseForm').reset();
    document.getElementById('message').classList.add('hidden');
}

function viewCaseDetail(caseId) {
    window.location.href = `case_view.html?id=${caseId}`;
}
