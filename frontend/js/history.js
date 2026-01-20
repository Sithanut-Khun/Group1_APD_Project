class HistoryManager {
    constructor() {
        this.predictions = [];
        this.filteredPredictions = [];
        
        // DOM Elements
        this.tableBody = document.getElementById('historyTableBody');
        this.activityFilter = document.getElementById('activityFilter');
        this.limitFilter = document.getElementById('limitFilter');
        this.refreshBtn = document.getElementById('refreshBtn');
        this.exportBtn = document.getElementById('exportBtn');
        this.recordCount = document.getElementById('recordCount');
        
        // Stats elements
        this.totalRecords = document.getElementById('totalRecords');
        this.avgConfidence = document.getElementById('avgConfidence');
        this.avgFPS = document.getElementById('avgFPS');
        this.avgLatency = document.getElementById('avgLatency');
        
        this.init();
    }
    
    async init() {
        console.log('🚀 Initializing History Manager...');
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Check backend health
        await this.checkBackendHealth();
        
        // Load initial data
        await this.loadHistory();
        
        // Auto-refresh every 30 seconds
        setInterval(() => this.loadHistory(), 30000);
    }
    
    async checkBackendHealth() {
        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.HEALTH}`);
            if (response.ok) {
                document.getElementById('status').textContent = 'Connected to backend';
                document.getElementById('processingIndicator').classList.add('active');
            } else {
                throw new Error('Backend offline');
            }
        } catch (error) {
            console.error('Backend health check error:', error);
            document.getElementById('status').textContent = 'Backend offline';
            document.getElementById('processingIndicator').classList.remove('active');
        }
    }
    
    setupEventListeners() {
        console.log('🔧 Setting up event listeners...');
        console.log('activityFilter element:', this.activityFilter);
        
        this.activityFilter.addEventListener('change', (e) => {
            console.log('🎯 Activity filter changed to:', e.target.value);
            this.applyFilters();
        });
        this.limitFilter.addEventListener('change', () => this.loadHistory());
        this.refreshBtn.addEventListener('click', () => this.loadHistory());
        this.exportBtn.addEventListener('click', () => this.exportToCSV());
        
        console.log('✅ Event listeners set up');
    }
    
    async loadHistory() {
        try {
            this.showLoading();
            
            const limit = this.limitFilter.value;
            const response = await fetch(
                `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.HISTORY}?limit=${limit}`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.predictions = await response.json();
            console.log(`✅ Loaded ${this.predictions.length} predictions`);
            
            this.applyFilters();
            this.updateStatistics();
            
        } catch (error) {
            console.error('❌ Error loading history:', error);
            this.showError(error.message);
        }
    }
    
    applyFilters() {
        const activityFilter = this.activityFilter.value;
        
        this.filteredPredictions = this.predictions.filter(pred => {
            if (activityFilter && pred.prediction !== activityFilter) {
                return false;
            }
            return true;
        });
        
        this.renderTable();
        this.updateRecordCount();
        this.updateStatistics();
    }
    
    renderTable() {
        if (this.filteredPredictions.length === 0) {
            this.showEmpty();
            return;
        }
        
        const rows = this.filteredPredictions
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .map(pred => this.createTableRow(pred))
            .join('');
        
        this.tableBody.innerHTML = rows;
    }
    
    createTableRow(pred) {
        const timestamp = new Date(pred.created_at).toLocaleString();
        const confidence = (pred.confidence * 100).toFixed(1);
        const activityClass = pred.prediction.toLowerCase().replace(/\s+/g, '-');
        
        // Determine confidence color
        let confidenceClass = 'high';
        if (pred.confidence < 0.7) confidenceClass = 'medium';
        if (pred.confidence < 0.5) confidenceClass = 'low';
        
        // Determine FPS color
        let fpsClass = 'high';
        if (pred.fps < 15) fpsClass = 'medium';
        if (pred.fps < 10) fpsClass = 'low';
        
        return `
            <tr data-id="${pred.id}">
                <td><strong>#${pred.id}</strong></td>
                <td>${timestamp}</td>
                <td>
                    <span class="activity-badge ${activityClass}">
                        <i class="fas ${this.getActivityIcon(pred.prediction)}"></i>
                        ${pred.prediction}
                    </span>
                </td>
                <td>
                    <div class="confidence-indicator">
                        <span class="metric-value ${confidenceClass}">${confidence}%</span>
                        <div class="confidence-bar-mini">
                            <div class="confidence-fill-mini" style="width: ${confidence}%"></div>
                        </div>
                    </div>
                </td>
                <td><span class="metric-value">${pred.person_count || 0}</span></td>
                <td><span class="metric-value ${fpsClass}">${pred.fps ? pred.fps.toFixed(1) : 'N/A'}</span></td>
                <td><span class="metric-value">${pred.latency ? pred.latency.toFixed(0) + 'ms' : 'N/A'}</span></td>
                <td><span class="image-filename">${pred.input_data}</span></td>
            </tr>
        `;
    }
    
    getActivityIcon(activity) {
        const icons = {
            'Running': 'fa-running',
            'Walking': 'fa-walking',
            'Standing': 'fa-user',
            'Sitting': 'fa-chair',
            'Jumping': 'fa-child',
            'Waving': 'fa-hand-paper',
            'Squatting': 'fa-dumbbell',
            'Raising Arms': 'fa-hands',
            'Bending Over': 'fa-arrow-down',
            'Unknown Pose': 'fa-question'
        };
        return icons[activity] || 'fa-user';
    }
    
    updateStatistics() {
        const total = this.filteredPredictions.length;
        
        console.log('📊 Updating statistics for', total, 'filtered records');
        
        if (total === 0) {
            this.totalRecords.textContent = '0';
            this.avgConfidence.textContent = '0%';
            this.avgFPS.textContent = '0';
            this.avgLatency.textContent = '0ms';
            return;
        }
        
        // Calculate averages from filtered predictions
        const avgConf = this.filteredPredictions.reduce((sum, p) => sum + p.confidence, 0) / total;
        
        const validFPS = this.filteredPredictions.filter(p => p.fps !== null && p.fps !== undefined);
        const avgFPSVal = validFPS.length > 0
            ? validFPS.reduce((sum, p) => sum + p.fps, 0) / validFPS.length
            : 0;
        
        const validLatency = this.filteredPredictions.filter(p => p.latency !== null && p.latency !== undefined);
        const avgLatencyVal = validLatency.length > 0
            ? validLatency.reduce((sum, p) => sum + p.latency, 0) / validLatency.length
            : 0;
        
        // Set values immediately first, then animate from current value
        const currentTotal = parseInt(this.totalRecords.textContent) || 0;
        const currentConf = parseFloat(this.avgConfidence.textContent) || 0;
        const currentFPS = parseFloat(this.avgFPS.textContent) || 0;
        const currentLatency = parseFloat(this.avgLatency.textContent) || 0;
        
        // Update UI with animation
        this.animateValue(this.totalRecords, currentTotal, total, 500, 0);
        this.animateValue(this.avgConfidence, currentConf, avgConf * 100, 500, 1, '%');
        this.animateValue(this.avgFPS, currentFPS, avgFPSVal, 500, 1);
        this.animateValue(this.avgLatency, currentLatency, avgLatencyVal, 500, 0, 'ms');
    }
    
    animateValue(element, start, end, duration, decimals = 0, suffix = '') {
        const startTime = performance.now();
        
        const update = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const current = start + (end - start) * progress;
            element.textContent = current.toFixed(decimals) + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        };
        
        requestAnimationFrame(update);
    }
    
    updateRecordCount() {
        const filtered = this.filteredPredictions.length;
        const total = this.predictions.length;
        
        if (filtered === total) {
            this.recordCount.textContent = `Showing ${total} records`;
        } else {
            this.recordCount.textContent = `Showing ${filtered} of ${total} records`;
        }
    }
    
    exportToCSV() {
        if (this.filteredPredictions.length === 0) {
            alert('No data to export');
            return;
        }
        
        // CSV Header
        const headers = ['ID', 'Timestamp', 'Activity', 'Confidence', 'Persons', 'FPS', 'Latency (ms)', 'Image'];
        
        // CSV Rows
        const rows = this.filteredPredictions.map(pred => [
            pred.id,
            new Date(pred.created_at).toISOString(),
            pred.prediction,
            (pred.confidence * 100).toFixed(2),
            pred.person_count || 0,
            pred.fps ? pred.fps.toFixed(2) : 'N/A',
            pred.latency ? pred.latency.toFixed(2) : 'N/A',
            pred.input_data
        ]);
        
        // Combine
        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');
        
        // Download
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `neuralpose_history_${Date.now()}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        console.log('✅ CSV exported successfully');
    }
    
    showLoading() {
        this.tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="loading-cell">
                    <i class="fas fa-spinner fa-spin"></i> Loading data...
                </td>
            </tr>
        `;
    }
    
    showEmpty() {
        this.tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No predictions found</p>
                </td>
            </tr>
        `;
    }
    
    showError(message) {
        this.tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state" style="color: var(--danger);">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Error loading data: ${message}</p>
                </td>
            </tr>
        `;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.historyManager = new HistoryManager();
});