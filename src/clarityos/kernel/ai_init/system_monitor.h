#ifndef SYSTEM_MONITOR_H
#define SYSTEM_MONITOR_H

// Function prototypes
void init_system_monitor();
void stop_system_monitor();
void set_monitoring_interval(int interval_ms);
void detect_anomalies();
void record_anomaly_detection();

#endif /* SYSTEM_MONITOR_H */