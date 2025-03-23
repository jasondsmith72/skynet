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