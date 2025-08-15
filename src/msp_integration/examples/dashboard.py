"""
Simple web dashboard for MSP monitoring.

This module provides a simple Flask-based web dashboard to visualize
the monitoring data from the MSP integration module.
"""

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

try:
    from flask import Flask, render_template, jsonify, request
except ImportError:
    print("Flask is required for the dashboard. Install with: pip install flask")
    sys.exit(1)

from ..config import MSPConfiguration
from ..integration import MSPIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dashboard.log')
    ]
)

logger = logging.getLogger(__name__)

# Global variables
config = MSPConfiguration('config.yaml')
integration = None
monitor_thread = None
running = False
dashboard_data = {
    'last_update': None,
    'clients': {},
    'anomalies': []
}


def load_config():
    """Load configuration for the dashboard."""
    global config
    
    # Create config if it doesn't exist
    if not os.path.exists('config.yaml'):
        logger.info("Creating initial configuration...")
        
        config.config = {
            'platforms': {
                'connectwise': {
                    'url': 'https://your-instance.connectwise.com',
                    'company_id': 'your_company',
                    'public_key': 'your_public_key',
                    'private_key': 'your_private_key',
                    'client_id': 'your_client_id',
                    'automate_url': 'https://your-instance.automate.net'
                }
            },
            'monitoring': {
                'scan_interval': 15,  # minutes
                'anomaly_threshold': 0.8,
                'auto_remediate': False
            },
            'clients': [
                {
                    'id': 'client1',
                    'name': 'Client One',
                    'enabled': True
                },
                {
                    'id': 'client2',
                    'name': 'Client Two',
                    'enabled': True
                }
            ],
            'dashboard': {
                'update_interval': 5,  # minutes
                'port': 5000,
                'host': '0.0.0.0'
            }
        }
        
        config.save()
        logger.info("Created initial configuration file. Please edit config.yaml with your actual credentials.")
    
    # Load existing config
    config.load()


def initialize_integration():
    """Initialize the MSP integration module."""
    global integration
    
    try:
        integration = MSPIntegration(config_path='config.yaml')
        logger.info("MSP integration initialized")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize MSP integration: {str(e)}")
        return False


def update_dashboard_data():
    """Update dashboard data with current client status."""
    global dashboard_data
    
    if not integration:
        logger.error("Integration not initialized")
        return
    
    platform = 'connectwise'
    clients = config.get('clients', [])
    enabled_clients = [c for c in clients if c.get('enabled', False)]
    
    # Connect to platform
    connection_results = integration.connect(platform)
    
    if not connection_results.get(platform, False):
        logger.error(f"Failed to connect to {platform}")
        return
    
    # Process each client
    all_anomalies = []
    clients_data = {}
    
    for client in enabled_clients:
        client_id = client.get('id')
        client_name = client.get('name', client_id)
        
        if not client_id:
            continue
        
        logger.info(f"Processing client: {client_name}")
        
        # Get client data
        client_data = {
            'id': client_id,
            'name': client_name,
            'devices': [],
            'status': 'Unknown',
            'anomaly_count': 0
        }
        
        # Get client devices
        success, devices, error = integration.get_devices(platform, client_id)
        
        if success and devices:
            client_data['devices'] = devices
            
            # Setup monitoring for client
            try:
                # Initialize monitoring if not already set up
                if client_id not in getattr(integration, 'anomaly_detectors', {}):
                    success = integration.setup_client_monitoring(platform, client_id)
                    
                    if not success:
                        logger.error(f"Failed to set up monitoring for client {client_name}")
                        client_data['status'] = 'Setup Failed'
                        clients_data[client_id] = client_data
                        continue
                
                # Get anomaly threshold from config
                anomaly_threshold = config.get('monitoring.anomaly_threshold', 0.8)
                
                # Process current metrics
                anomalies = integration.process_current_metrics(
                    platform=platform,
                    client_id=client_id,
                    threshold=anomaly_threshold,
                    auto_remediate=False  # Don't auto-remediate from dashboard
                )
                
                if anomalies:
                    client_data['anomaly_count'] = len(anomalies)
                    client_data['status'] = 'Warning'
                    all_anomalies.extend(anomalies)
                else:
                    client_data['status'] = 'Healthy'
                    
            except Exception as e:
                logger.error(f"Error processing client {client_name}: {str(e)}")
                client_data['status'] = 'Error'
                
        else:
            logger.warning(f"Failed to get devices for client {client_name}: {error}")
            client_data['status'] = 'No Devices'
            
        clients_data[client_id] = client_data
    
    # Disconnect from platform
    integration.disconnect(platform)
    
    # Update dashboard data
    dashboard_data = {
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'clients': clients_data,
        'anomalies': all_anomalies
    }


def monitoring_thread_func():
    """Background thread function for updating monitoring data."""
    global running
    
    update_interval = config.get('dashboard.update_interval', 5)  # minutes
    
    while running:
        try:
            update_dashboard_data()
            logger.info(f"Dashboard data updated - monitoring {len(dashboard_data['clients'])} clients")
        except Exception as e:
            logger.error(f"Error updating dashboard data: {str(e)}")
            
        # Sleep until next update interval
        for _ in range(update_interval * 60):
            if not running:
                break
            time.sleep(1)


def start_monitoring():
    """Start the background monitoring thread."""
    global monitor_thread, running
    
    if monitor_thread and monitor_thread.is_alive():
        logger.warning("Monitoring thread is already running")
        return
    
    running = True
    monitor_thread = threading.Thread(target=monitoring_thread_func)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    logger.info("Monitoring thread started")


def stop_monitoring():
    """Stop the background monitoring thread."""
    global running
    
    running = False
    logger.info("Monitoring thread stopping...")


# Initialize Flask app
app = Flask(__name__)


@app.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('index.html')


@app.route('/api/data')
def get_data():
    """API endpoint to get the current dashboard data."""
    return jsonify(dashboard_data)


@app.route('/api/clients')
def get_clients():
    """API endpoint to get the list of clients."""
    clients = config.get('clients', [])
    return jsonify(clients)


@app.route('/api/anomalies')
def get_anomalies():
    """API endpoint to get the current anomalies."""
    return jsonify(dashboard_data['anomalies'])


@app.route('/api/devices')
def get_devices():
    """API endpoint to get devices for a specific client."""
    client_id = request.args.get('client_id')
    
    if not client_id:
        return jsonify({'error': 'Missing client_id parameter'}), 400
    
    if client_id not in dashboard_data['clients']:
        return jsonify({'error': 'Client not found'}), 404
    
    return jsonify(dashboard_data['clients'][client_id].get('devices', []))


@app.route('/api/remediate', methods=['POST'])
def remediate_issue():
    """API endpoint to perform remediation action."""
    data = request.json
    
    if not data:
        return jsonify({'error': 'Missing request data'}), 400
    
    client_id = data.get('client_id')
    device_id = data.get('device_id')
    metric = data.get('metric')
    action = data.get('action')
    
    if not all([client_id, device_id, metric, action]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    if not integration:
        return jsonify({'error': 'Integration not initialized'}), 500
    
    platform = 'connectwise'
    
    # Connect to platform
    connection_results = integration.connect(platform)
    
    if not connection_results.get(platform, False):
        return jsonify({'error': f'Failed to connect to {platform}'}), 500
    
    try:
        # Determine action parameters
        action_params = {'device_id': device_id}
        
        if action == 'restart_service':
            action_params['service_name'] = data.get('service_name', 'Spooler')
            success, message = integration.restart_service(
                platform=platform,
                device_id=device_id,
                service_name=action_params['service_name']
            )
        elif action == 'clear_disk':
            success, message = integration._perform_remediation(
                platform=platform,
                action='clear_temp_files',
                params=action_params
            )
        elif action == 'restart_device':
            success, message = integration.reboot_device(
                platform=platform,
                device_id=device_id,
                force=False
            )
        else:
            success, message = False, f"Unknown action: {action}"
        
        # Disconnect from platform
        integration.disconnect(platform)
        
        if success:
            return jsonify({'success': True, 'message': message or 'Remediation action performed successfully'})
        else:
            return jsonify({'success': False, 'message': message or 'Remediation action failed'}), 500
            
    except Exception as e:
        # Disconnect from platform
        integration.disconnect(platform)
        return jsonify({'error': str(e)}), 500


def create_template_directory():
    """Create a basic template directory for the dashboard."""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    # Create a basic index.html template
    index_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MSP Monitoring Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .client-card { margin-bottom: 20px; }
        .status-healthy { color: green; }
        .status-warning { color: orange; }
        .status-error { color: red; }
        .status-unknown { color: gray; }
        .anomaly-item { border-left: 4px solid orange; padding-left: 10px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container mt-4">
        <h1>MSP Monitoring Dashboard</h1>
        <div class="row">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h5>Client Status</h5>
                    </div>
                    <div class="card-body">
                        <div id="client-container">Loading client data...</div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5>Recent Anomalies</h5>
                    </div>
                    <div class="card-body">
                        <div id="anomaly-container">Loading anomaly data...</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="row mt-3">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5>Device Details</h5>
                    </div>
                    <div class="card-body">
                        <select id="client-select" class="form-select mb-3">
                            <option value="">Select a client</option>
                        </select>
                        <div id="device-container">Select a client to view devices</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="row mt-3">
            <div class="col-12">
                <div class="alert alert-info">
                    <span id="last-update">Last updated: Never</span>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Function to update the dashboard
        function updateDashboard() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    // Update last update time
                    document.getElementById('last-update').textContent = 'Last updated: ' + data.last_update;
                    
                    // Update client data
                    const clientContainer = document.getElementById('client-container');
                    clientContainer.innerHTML = '';
                    
                    if (Object.keys(data.clients).length === 0) {
                        clientContainer.innerHTML = '<p>No clients available</p>';
                    } else {
                        for (const [clientId, client] of Object.entries(data.clients)) {
                            const statusClass = 'status-' + (
                                client.status === 'Healthy' ? 'healthy' :
                                client.status === 'Warning' ? 'warning' :
                                client.status === 'Error' ? 'error' : 'unknown'
                            );
                            
                            const clientCard = document.createElement('div');
                            clientCard.className = 'client-card card mb-2';
                            clientCard.innerHTML = `
                                <div class="card-body">
                                    <div class="d-flex justify-content-between">
                                        <h5 class="card-title">${client.name}</h5>
                                        <span class="${statusClass}">${client.status}</span>
                                    </div>
                                    <p class="card-text">
                                        Devices: ${client.devices.length}<br>
                                        Anomalies: ${client.anomaly_count}
                                    </p>
                                </div>
                            `;
                            clientContainer.appendChild(clientCard);
                        }
                    }
                    
                    // Update anomaly data
                    const anomalyContainer = document.getElementById('anomaly-container');
                    anomalyContainer.innerHTML = '';
                    
                    if (data.anomalies.length === 0) {
                        anomalyContainer.innerHTML = '<p>No anomalies detected</p>';
                    } else {
                        for (const anomaly of data.anomalies) {
                            const anomalyItem = document.createElement('div');
                            anomalyItem.className = 'anomaly-item';
                            anomalyItem.innerHTML = `
                                <p><strong>${anomaly.device_name}</strong></p>
                                <p>
                                    Metric: ${anomaly.metric}<br>
                                    Value: ${anomaly.value.toFixed(1)}%<br>
                                    Score: ${anomaly.anomaly_score.toFixed(2)}
                                </p>
                                <div class="d-flex gap-2">
                                    <button class="btn btn-sm btn-outline-primary remediate-btn" 
                                      data-client-id="${anomaly.client_id}" 
                                      data-device-id="${anomaly.device_id}" 
                                      data-metric="${anomaly.metric}">
                                      Remediate
                                    </button>
                                </div>
                            `;
                            anomalyContainer.appendChild(anomalyItem);
                        }
                        
                        // Add event listeners to remediate buttons
                        document.querySelectorAll('.remediate-btn').forEach(button => {
                            button.addEventListener('click', function() {
                                const clientId = this.getAttribute('data-client-id');
                                const deviceId = this.getAttribute('data-device-id');
                                const metric = this.getAttribute('data-metric');
                                
                                // Determine action based on metric
                                let action;
                                if (metric === 'cpu') {
                                    action = 'restart_service';
                                } else if (metric === 'disk') {
                                    action = 'clear_disk';
                                } else if (metric === 'memory') {
                                    action = 'restart_device';
                                } else {
                                    action = 'restart_device';
                                }
                                
                                // Send remediation request
                                fetch('/api/remediate', {
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/json'
                                    },
                                    body: JSON.stringify({
                                        client_id: clientId,
                                        device_id: deviceId,
                                        metric: metric,
                                        action: action
                                    })
                                })
                                .then(response => response.json())
                                .then(data => {
                                    if (data.success) {
                                        alert('Remediation initiated: ' + data.message);
                                    } else {
                                        alert('Remediation failed: ' + data.message);
                                    }
                                })
                                .catch(error => {
                                    alert('Error: ' + error);
                                });
                            });
                        });
                    }
                    
                    // Update client select
                    const clientSelect = document.getElementById('client-select');
                    // Keep the current selection
                    const currentSelection = clientSelect.value;
                    
                    // Clear all options except the first one
                    while (clientSelect.options.length > 1) {
                        clientSelect.remove(1);
                    }
                    
                    // Add client options
                    for (const [clientId, client] of Object.entries(data.clients)) {
                        const option = document.createElement('option');
                        option.value = clientId;
                        option.textContent = client.name;
                        clientSelect.appendChild(option);
                    }
                    
                    // Restore selection if possible
                    if (currentSelection && Array.from(clientSelect.options).some(o => o.value === currentSelection)) {
                        clientSelect.value = currentSelection;
                        // Trigger change event to update device list
                        const changeEvent = new Event('change');
                        clientSelect.dispatchEvent(changeEvent);
                    }
                })
                .catch(error => {
                    console.error('Error fetching dashboard data:', error);
                });
        }
        
        // Function to load devices for a client
        function loadDevices(clientId) {
            if (!clientId) {
                document.getElementById('device-container').innerHTML = 'Select a client to view devices';
                return;
            }
            
            fetch(`/api/devices?client_id=${clientId}`)
                .then(response => response.json())
                .then(devices => {
                    const deviceContainer = document.getElementById('device-container');
                    
                    if (devices.length === 0) {
                        deviceContainer.innerHTML = '<p>No devices found for this client</p>';
                    } else {
                        let html = '<div class="table-responsive"><table class="table table-striped">';
                        html += '<thead><tr><th>Device</th><th>Type</th><th>Status</th><th>Last Seen</th></tr></thead>';
                        html += '<tbody>';
                        
                        for (const device of devices) {
                            const lastSeen = device.lastSeen ? new Date(device.lastSeen).toLocaleString() : 'Unknown';
                            html += `
                                <tr>
                                    <td>${device.name || 'Unnamed Device'}</td>
                                    <td>${device.type || 'Unknown'}</td>
                                    <td>${device.status || 'Unknown'}</td>
                                    <td>${lastSeen}</td>
                                </tr>
                            `;
                        }
                        
                        html += '</tbody></table></div>';
                        deviceContainer.innerHTML = html;
                    }
                })
                .catch(error => {
                    console.error('Error fetching devices:', error);
                    document.getElementById('device-container').innerHTML = 'Error loading devices';
                });
        }
        
        // Event listener for client select
        document.getElementById('client-select').addEventListener('change', function() {
            loadDevices(this.value);
        });
        
        // Initial dashboard update
        updateDashboard();
        
        // Auto-refresh every 30 seconds
        setInterval(updateDashboard, 30000);
    </script>
</body>
</html>'''
    
    index_path = os.path.join(template_dir, 'index.html')
    with open(index_path, 'w') as f:
        f.write(index_html)
    
    logger.info(f"Created template file: {index_path}")


def main():
    """Main function to run the dashboard."""
    # Load configuration
    load_config()
    
    # Initialize integration
    if not initialize_integration():
        print("Failed to initialize MSP integration. Exiting...")
        return
    
    # Create template directory
    create_template_directory()
    
    # Start monitoring thread
    start_monitoring()
    
    try:
        # Get dashboard settings from config
        port = config.get('dashboard.port', 5000)
        host = config.get('dashboard.host', '0.0.0.0')
        
        # Run Flask app
        logger.info(f"Starting dashboard on http://{host}:{port}")
        app.run(host=host, port=port, debug=False)
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user")
    finally:
        # Stop monitoring thread
        stop_monitoring()


if __name__ == "__main__":
    main()
