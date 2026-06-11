// Configuration
const MAX_DATA_POINTS = 30;

// Chart Common Options
const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
        duration: 200, // Smooth micro-animations
        easing: 'linear'
    },
    scales: {
        x: { 
            display: false, // Hide X axis for a cleaner look
        },
        y: { 
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8' }
        }
    },
    plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: 'rgba(15, 17, 26, 0.9)',
            titleColor: '#e2e8f0',
            bodyColor: '#e2e8f0',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1
        }
    },
    elements: {
        line: { tension: 0.4 }, // Smooth curves
        point: { radius: 0, hitRadius: 10, hoverRadius: 4 }
    }
};

// Initialize Charts
function createChart(ctxId, colorStr) {
    const ctx = document.getElementById(ctxId).getContext('2d');
    
    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, `rgba(${colorStr}, 0.5)`);
    gradient.addColorStop(1, `rgba(${colorStr}, 0.0)`);

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                data: [],
                borderColor: `rgb(${colorStr})`,
                backgroundColor: gradient,
                borderWidth: 2,
                fill: true,
                segment: {
                    borderColor: ctx => ctx.p0.parsed.y_anomaly ? '#ef4444' : `rgb(${colorStr})`
                }
            }]
        },
        options: commonOptions
    });
}

const charts = {
    temperature: createChart('chart-temp', '250, 204, 21'), // Yellow
    pressure: createChart('chart-press', '59, 130, 246'),   // Blue
    vibration: createChart('chart-vib', '168, 85, 247')     // Purple
};

// Toast Notification System
function showToast(title, message) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <div class="toast-icon">⚠️</div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-desc">${message}</div>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Animate in
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // Remove after 5 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300); // Wait for transition
    }, 5000);
}

// Global Status UI
const globalStatus = document.getElementById('global-status');
const statusText = document.getElementById('status-text');
let alertTimeout;

function setAlertState(isAnomaly, anomalies) {
    if (isAnomaly) {
        globalStatus.classList.add('alert');
        statusText.innerText = "Anomaly Detected!";
        
        // Build toast message
        let msgParts = [];
        for (const [key, info] of Object.entries(anomalies)) {
            msgParts.push(`${key}: ${info.value} (Z:${info.z_score})`);
        }
        showToast("Machine Warning", msgParts.join(' | '));

        clearTimeout(alertTimeout);
        alertTimeout = setTimeout(() => {
            globalStatus.classList.remove('alert');
            statusText.innerText = "System Normal";
        }, 5000);
    }
}

// Update UI
function updateDashboard(data) {
    const timeLabel = new Date(data.timestamp).toLocaleTimeString();

    // Helper to update specific card and chart
    const updateSensor = (key, valId, chartObj) => {
        const val = data[key];
        document.getElementById(valId).innerHTML = `${val.toFixed(2)} <span class="unit"></span>`;
        
        const chartData = chartObj.data;
        chartData.labels.push(timeLabel);
        
        // Check if this specific point is anomalous
        const isPointAnomaly = data.is_anomaly && data.anomalies[key];
        
        // Push data as object to store anomaly state for segment coloring
        chartData.datasets[0].data.push({ x: timeLabel, y: val, y_anomaly: isPointAnomaly });

        if (chartData.labels.length > MAX_DATA_POINTS) {
            chartData.labels.shift();
            chartData.datasets[0].data.shift();
        }
        chartObj.update();
    };

    updateSensor('temperature', 'val-temp', charts.temperature);
    updateSensor('pressure', 'val-press', charts.pressure);
    updateSensor('vibration', 'val-vib', charts.vibration);

    setAlertState(data.is_anomaly, data.anomalies);
}

// WebSocket Connection
function connectWebSocket() {
    // Determine WS URL based on current host
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        } catch (e) {
            console.error("Error parsing WS data", e);
        }
    };

    ws.onclose = () => {
        console.log("WebSocket disconnected. Reconnecting in 3s...");
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (err) => {
        console.error("WebSocket error", err);
        ws.close();
    };
}

// Start connection
connectWebSocket();
