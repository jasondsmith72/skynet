#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "system_state.h"

static SystemState current_state;

void init_system_state() {
    // Initialize system state
    memset(&current_state, 0, sizeof(SystemState));
    
    // Set initial values
    current_state.boot_time = time(NULL);
    current_state.last_update_time = current_state.boot_time;
    current_state.cpu_usage = 0.0;
    current_state.memory_usage = 0.0;
    current_state.io_usage = 0.0;
    current_state.network_usage = 0.0;
    current_state.num_processes = 0;
    current_state.num_users = 0;
    current_state.battery_level = 100.0;  // Assume fully charged
    current_state.on_ac_power = 1;        // Assume AC power
    
    printf("System state initialized\n");
}

SystemState get_current_system_state() {
    return current_state;
}

void update_system_state() {
    // Update timestamp
    current_state.last_update_time = time(NULL);
    
    // Update resource usage (in a real implementation, would read from /proc)
    current_state.cpu_usage = get_cpu_usage();
    current_state.memory_usage = get_memory_usage();
    current_state.io_usage = get_io_usage();
    current_state.network_usage = get_network_usage();
    
    // Update process count (in a real implementation, would read from /proc)
    current_state.num_processes = count_processes();
    
    // Update user count (in a real implementation, would use getutent())
    current_state.num_users = count_users();
    
    // Update power state (in a real implementation, would read from /sys)
    update_power_state();
    
    // Record state update for learning
    record_state_update();
}

// Helper functions to get system metrics
double get_cpu_usage() {
    // In a real implementation, this would read from /proc/stat
    // For this prototype, return a dummy value that changes slightly each time
    static double last_cpu = 0.3;
    double change = ((double)rand() / RAND_MAX - 0.5) * 0.1;  // -0.05 to +0.05
    double new_cpu = last_cpu + change;
    
    // Keep within bounds
    if (new_cpu < 0.05) new_cpu = 0.05;
    if (new_cpu > 0.95) new_cpu = 0.95;
    
    last_cpu = new_cpu;
    return new_cpu;
}

double get_memory_usage() {
    // In a real implementation, this would read from /proc/meminfo
    // For this prototype, return a dummy value
    return 0.4 + ((double)rand() / RAND_MAX - 0.5) * 0.1;  // 0.35 to 0.45
}

double get_io_usage() {
    // In a real implementation, this would read from /proc/diskstats
    // For this prototype, return a dummy value
    return 0.2 + ((double)rand() / RAND_MAX - 0.5) * 0.1;  // 0.15 to 0.25
}

double get_network_usage() {
    // In a real implementation, this would read from /proc/net/dev
    // For this prototype, return a dummy value
    return 0.1 + ((double)rand() / RAND_MAX - 0.5) * 0.05;  // 0.075 to 0.125
}

int count_processes() {
    // In a real implementation, this would read from /proc
    // For this prototype, return a dummy value
    return 50 + rand() % 10;  // 50 to 59
}

int count_users() {
    // In a real implementation, this would use getutent()
    // For this prototype, return a dummy value
    return 1 + rand() % 2;  // 1 to 2
}

void update_power_state() {
    // In a real implementation, this would read from /sys
    // For this prototype, use dummy values
    
    // Only update occasionally to simulate stability
    if (rand() % 10 == 0) {
        current_state.on_ac_power = rand() % 2;  // 0 or 1
    }
    
    // If on battery, decrease battery level
    if (!current_state.on_ac_power) {
        current_state.battery_level -= 0.1;
        if (current_state.battery_level < 0) current_state.battery_level = 0;
    } else {
        // If on AC, charge battery
        current_state.battery_level += 0.2;
        if (current_state.battery_level > 100) current_state.battery_level = 100;
    }
}

void record_state_update() {
    // In a real implementation, this would record the state for learning
    // For this prototype, just print the action
    printf("Recording system state update\n");
}