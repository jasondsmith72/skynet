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