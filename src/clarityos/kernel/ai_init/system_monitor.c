#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <pthread.h>
#include "system_monitor.h"
#include "system_state.h"

// Thread handle for the monitoring thread
static pthread_t monitor_thread;
static int monitor_running = 0;

// Monitoring interval in microseconds
static int monitoring_interval = 1000000;  // 1 second

// Monitoring thread function
void *monitoring_thread_func(void *arg) {
    while (monitor_running) {
        // Update system state
        update_system_state();
        
        // Analyze for anomalies
        detect_anomalies();
        
        // Sleep for monitoring interval
        usleep(monitoring_interval);
    }
    
    return NULL;
}

void init_system_monitor() {
    // Initialize system state
    init_system_state();
    
    // Start monitoring thread
    monitor_running = 1;
    if (pthread_create(&monitor_thread, NULL, monitoring_thread_func, NULL) != 0) {
        fprintf(stderr, "Failed to create monitoring thread\n");
        exit(EXIT_FAILURE);
    }
    
    printf("System monitor initialized\n");
}

void stop_system_monitor() {
    // Stop monitoring thread
    monitor_running = 0;
    pthread_join(monitor_thread, NULL);
    
    printf("System monitor stopped\n");
}

void set_monitoring_interval(int interval_ms) {
    monitoring_interval = interval_ms * 1000;  // Convert to microseconds
    printf("Monitoring interval set to %d ms\n", interval_ms);
}

void detect_anomalies() {
    // Get current system state
    SystemState state = get_current_system_state();
    
    // Check for high CPU usage
    if (state.cpu_usage > 0.9) {
        printf("ANOMALY: High CPU usage detected (%.1f%%)\n", state.cpu_usage * 100);
        // In a real implementation, would take corrective action
    }
    
    // Check for high memory usage
    if (state.memory_usage > 0.9) {
        printf("ANOMALY: High memory usage detected (%.1f%%)\n", state.memory_usage * 100);
        // In a real implementation, would take corrective action
    }
    
    // Check for low battery
    if (!state.on_ac_power && state.battery_level < 10.0) {
        printf("ANOMALY: Low battery level (%.1f%%)\n", state.battery_level);
        // In a real implementation, would take corrective action
    }
    
    // Record anomaly detection for learning
    record_anomaly_detection();
}

void record_anomaly_detection() {
    // In a real implementation, this would record anomaly detection for learning
    // For this prototype, just print the action
    printf("Recording anomaly detection\n");
}