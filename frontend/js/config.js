

// API Configuration
const API_CONFIG = {
    BASE_URL: '/api',
    ENDPOINTS: {
        PREDICT: '/predict',
        HEALTH: '/health',
        HISTORY: '/history'
    },
    TIMEOUT: 30000
};

// Activity detection sample data
const SAMPLE_ACTIVITIES = [
    {name: 'Running', icon: 'fa-running', confidence: 85},
    {name: 'Walking', icon: 'fa-walking', confidence: 72},
    {name: 'Standing', icon: 'fa-user', confidence: 68},
    {name: 'Sitting', icon: 'fa-chair', confidence: 91},
    {name: 'Jumping', icon: 'fa-child', confidence: 79}
];

// Model configurations
const MODELS = {
    'mediapipe': {
        name: 'MediaPipe Pose',
        description: 'Activity recognition',
        fps: 30,
        accuracy: 0.90
    }
};

// Export configuration
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        API_CONFIG,
        SAMPLE_ACTIVITIES,
        MODELS
    };
}