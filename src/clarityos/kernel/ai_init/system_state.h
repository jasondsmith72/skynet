#ifndef SYSTEM_STATE_H
#define SYSTEM_STATE_H

#include <time.h>

// System state structure
typedef struct {
    time_t boot_time;          // System boot time
    time_t last_update_time;   // Last state update time
    double cpu_usage;          // CPU usage (0.0 to 1.0)
    double memory_usage;       // Memory usage (0.0 to 1.0)
    double io_usage;           // I/O usage (0.0 to 1.0)
    double network_usage;      // Network usage (0.0 to 1.0)
    int num_processes;         // Number of running processes
    int num_users;             // Number of logged-in users
    double battery_level;      // Battery level (0.0 to 100.0)
    int on_ac_power;           // Whether on AC power (1) or battery (0)
} SystemState;

// Function prototypes
void init_system_state();
SystemState get_current_system_state();
void update_system_state();

// Helper functions
double get_cpu_usage();
double get_memory_usage();
double get_io_usage();
double get_network_usage();
int count_processes();
int count_users();
void update_power_state();
void record_state_update();

#endif /* SYSTEM_STATE_H */