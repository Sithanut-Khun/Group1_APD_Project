
/* ============================================
   Metrics & Activity Detection
   ============================================ */

class MetricsManager {
    constructor() {
        this.fpsElement = document.getElementById('fpsMetric');
        this.confidenceElement = document.getElementById('confidenceMetric');
        this.latencyElement = document.getElementById('latencyMetric');
        this.personsElement = document.getElementById('personsMetric');
        
        this.metrics = {
            fps: 0,
            confidence: 0,
            latency: 0,
            persons: 0
        };
        
        // Initialize with zeros
        this.reset();
    }

    updateMetric(metric, value) {
        // Validate and cap values
        let processedValue = value;
        
        switch(metric) {
            case 'fps':
                processedValue = Math.max(0, Math.min(value, 60));
                this.fpsElement.textContent = processedValue.toFixed(1);
                break;
            case 'confidence':
                processedValue = Math.max(0, Math.min(value, 100));
                this.confidenceElement.textContent = `${processedValue.toFixed(1)}%`;
                break;
            case 'latency':
                processedValue = Math.max(0, value);
                this.latencyElement.textContent = `${Math.round(processedValue)}ms`;
                break;
            case 'persons':
                processedValue = Math.max(0, Math.min(value, 10));
                this.personsElement.textContent = Math.round(processedValue);
                break;
        }
        
        this.metrics[metric] = processedValue;
    }

    reset() {
        this.updateMetric('fps', 0);
        this.updateMetric('confidence', 0);
        this.updateMetric('latency', 0);
        this.updateMetric('persons', 0);
    }

    getMetrics() {
        return { ...this.metrics };
    }
}

class ActivityManager {
    constructor() {
        this.activityList = document.getElementById('activityList');
        this.activities = [];
        this.render();
    }

    render() {
        this.activityList.innerHTML = '';
        
        if (this.activities.length === 0) {
            const placeholder = document.createElement('div');
            placeholder.className = 'activity-placeholder';
            placeholder.textContent = 'No activities detected';
            this.activityList.appendChild(placeholder);
            return;
        }
        
        // Show only the most recent 5 activities
        const recentActivities = this.activities.slice(-5);
        
        recentActivities.forEach(activity => {
            const item = document.createElement('div');
            item.className = 'activity-item';
            
            const confidence = Math.min(activity.confidence, 100);
            
            item.innerHTML = `
                <div class="activity-header">
                    <div class="activity-name">
                        <i class="fas ${activity.icon}"></i>
                        <span>${activity.name}</span>
                    </div>
                    <div class="activity-confidence">${Math.round(confidence)}%</div>
                </div>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${confidence}%;"></div>
                </div>
            `;
            
            this.activityList.appendChild(item);
        });
    }

    updateFromAPI(apiActivities) {
        if (!apiActivities || !Array.isArray(apiActivities)) return;
        apiActivities.forEach(activity => {
            if (activity.name && activity.confidence) {
                this.activities.push({  // Append to persist across processes
                    name: activity.name,
                    icon: activity.icon || 'fa-user',
                    confidence: Math.min(activity.confidence, 100)
                });
            }
        });
        this.render();  // Re-render full list
    }

    reset() {
        this.activities = [];
        this.render();
    }

    getActivities() {
        return [...this.activities];
    }
}

// Global instances
let metricsManager = null;
let activityManager = null;

function initMetricsAndActivities() {
    metricsManager = new MetricsManager();
    activityManager = new ActivityManager();
    return { metricsManager, activityManager };
}

function getExportData() {
    return {
        timestamp: new Date().toISOString(),
        model: 'Activity Recognition',
        metrics: metricsManager ? metricsManager.getMetrics() : {},
        activities: activityManager ? activityManager.getActivities() : []
    };
}