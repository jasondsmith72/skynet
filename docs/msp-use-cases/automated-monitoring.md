# MSP Use Case: Automated Monitoring in Clarity

This example demonstrates how Clarity would excel at creating automated monitoring systems for MSPs, with built-in error handling, self-healing capabilities, and easy integration with common MSP tools.

## System Monitor Example

```clarity
// SystemMonitor.clarity
module SystemMonitor {
    // Configuration with environment awareness
    const config = match environment {
        production => from json "/etc/sysmon/prod-config.json"
        staging => from json "/etc/sysmon/staging-config.json"
        development => {
            "checkInterval": 30, // seconds
            "alertThreshold": "warning",
            "notificationTargets": ["developer@example.com"]
        }
    }
    
    // Main monitoring service
    service Monitor on schedule config.checkInterval seconds {
        // Run all checks in parallel
        let results = for each check in CheckRegistry.all parallel {
            check.execute()
        }
        
        // Process results
        let alerts = results
            .filter(result => result.severity >= SeverityLevel.fromString(config.alertThreshold))
            .map(result => Alert.fromCheckResult(result))
        
        // Take action on alerts
        if alerts.isNotEmpty {
            NotificationService.send(alerts)
            
            // Auto-remediation for known issues
            for each alert in alerts {
                if RemediationRegistry.hasAutomation(alert.type) {
                    RemediationRegistry.execute(alert)
                }
            }
        }
        
        // Store historical data
        MetricsStore.save(results)
    }
}

// Example check implementation
class DiskSpaceCheck implements SystemCheck {
    path: String
    threshold: Percentage
    
    constructor(path: String, threshold: Percentage = 90%) {
        this.path = path
        this.threshold = threshold
    }
    
    function execute() -> CheckResult {
        // Safe file system operations with proper error handling
        let stats = try {
            FileSystem.getStats(this.path)
        } catch (error) {
            return CheckResult(
                check: this,
                status: "error",
                severity: SeverityLevel.Critical,
                message: "Cannot check disk space: ${error.message}"
            )
        }
        
        let usedPercentage = stats.used / stats.total * 100
        
        if usedPercentage >= this.threshold {
            return CheckResult(
                check: this,
                status: "warning",
                severity: SeverityLevel.Warning,
                message: "Disk usage at ${usedPercentage}% (threshold: ${this.threshold}%)",
                data: {
                    "path": this.path,
                    "used": stats.used,
                    "total": stats.total,
                    "percentage": usedPercentage
                }
            )
        }
        
        return CheckResult(
            check: this,
            status: "ok",
            severity: SeverityLevel.Info,
            message: "Disk usage normal at ${usedPercentage}%"
        )
    }
}

// Auto-remediation example
class DiskCleanupRemediation implements Remediation {
    function canHandle(alert: Alert) -> Boolean {
        return alert.type == "DiskSpaceCheck" && 
               alert.severity <= SeverityLevel.Warning
    }
    
    async function execute(alert: Alert) -> RemediationResult {
        let path = alert.data.path
        
        // Log rotation and compression
        if path == "/var/log" {
            try {
                await Shell.execute("logrotate -f /etc/logrotate.conf")
                return RemediationResult(
                    success: true,
                    message: "Forced log rotation to free up space"
                )
            } catch (error) {
                return RemediationResult(
                    success: false,
                    message: "Failed to rotate logs: ${error.message}"
                )
            }
        }
        
        // Remove temp files
        if path.contains("/tmp") {
            try {
                // Safe command execution with timeouts
                await Shell.execute(
                    "find ${path} -type f -atime +7 -delete",
                    timeout: 5 minutes
                )
                return RemediationResult(
                    success: true,
                    message: "Removed temp files older than 7 days"
                )
            } catch (error) {
                return RemediationResult(
                    success: false,
                    message: "Failed to clean temp files: ${error.message}"
                )
            }
        }
        
        return RemediationResult(
            success: false,
            message: "No automated remediation available for ${path}"
        )
    }
}

// ConnectWise integration example
class ConnectWiseNotifier implements NotificationService {
    credentials: ConnectWiseCredentials
    companyId: String
    boardId: String
    
    constructor(config: Map<String, String>) {
        this.credentials = ConnectWiseCredentials.fromConfig(config)
        this.companyId = config.companyId
        this.boardId = config.boardId
    }
    
    async function send(alerts: List<Alert>) -> Result<void> {
        // Connection pooling and retry logic built in
        using connection = await ConnectWise.connect(this.credentials) {
            for each alert in alerts {
                // Only create tickets for critical alerts
                if alert.severity >= SeverityLevel.Critical {
                    let ticket = TicketBuilder()
                        .withSummary("Alert: ${alert.message}")
                        .withDescription(alert.detailedMessage)
                        .withPriority(mapSeverityToTicketPriority(alert.severity))
                        .withCompany(this.companyId)
                        .withBoard(this.boardId)
                        .build()
                    
                    try {
                        await connection.service.ticket.create(ticket)
                    } catch (error) {
                        log.error("Failed to create ticket: ${error.message}")
                    }
                }
            }
        }
        
        return Success
    }
    
    private function mapSeverityToTicketPriority(severity: SeverityLevel) -> Integer {
        match severity {
            SeverityLevel.Critical => 1  // Emergency
            SeverityLevel.Error => 2     // High
            SeverityLevel.Warning => 3   // Normal
            _ => 4                       // Low
        }
    }
}
```

## Key MSP Features Demonstrated

### 1. Multi-client Management

Clarity's first-class support for multi-tenancy makes it ideal for MSPs:

```clarity
// Client-specific configuration with inheritance
module ClientConfiguration {
    // Base configuration for all clients
    const baseConfig = from json "/etc/msp/base-config.json"
    
    // Client-specific overrides
    const clientConfigs = from directory "/etc/msp/clients/*.json"
    
    // Get configuration for specific client
    function forClient(clientId: String) -> Configuration {
        if clientConfigs.has(clientId) {
            // Deep merge client config with base config
            return baseConfig merge clientConfigs[clientId]
        }
        
        return baseConfig
    }
    
    // Apply configuration to all clients
    function applyToAll(action: Function<Configuration, void>) {
        for each clientId in clientConfigs.keys {
            action(forClient(clientId))
        }
    }
}
```

### 2. Integration with PSA and RMM Tools

Clarity's integration capabilities make connecting with existing MSP tools simple:

```clarity
// PSA and RMM integrations automatically discovered
service MSPIntegrations {
    // Auto-discover available integrations
    const availableIntegrations = discover integrations in "/opt/msp/integrations"
    
    // Connect to RMM platform
    const rmm = integration("rmm") {
        type: availableIntegrations.findByType("rmm"),
        credentials: SecureStore.get("rmm_credentials"),
        options: {
            batchSize: 100,
            timeout: 30 seconds
        }
    }
    
    // Connect to PSA platform
    const psa = integration("psa") {
        type: availableIntegrations.findByType("psa"),
        credentials: SecureStore.get("psa_credentials"),
        options: {
            cacheTimeToLive: 5 minutes
        }
    }
    
    // Bidirectional sync example
    function syncTickets() {
        // Get new tickets from PSA
        let psaTickets = psa.getTicketsUpdatedSince(lastSyncTime)
        
        // Update RMM alerts based on ticket status
        for each ticket in psaTickets {
            if ticket.status == "Resolved" {
                rmm.closeAlertsByTicketId(ticket.id)
            }
        }
        
        // Get new alerts from RMM
        let rmmAlerts = rmm.getAlertsCreatedSince(lastSyncTime)
        
        // Create tickets for new alerts
        for each alert in rmmAlerts where not alert.hasTicket {
            let ticket = psa.createTicket({
                summary: alert.name,
                description: alert.description,
                priority: mapPriority(alert.severity),
                clientId: alert.clientId
            })
            
            // Link ticket back to alert
            rmm.linkTicketToAlert(ticket.id, alert.id)
        }
    }
}
```

### 3. Secure Credential Management

Built-in security features for handling client credentials:

```clarity
// Secure credential management
module CredentialManager {
    // Hardware-backed secure storage when available
    const store = match system.securityCapabilities {
        hasTPM => TPMBackedStore()
        hasSecureEnclave => SecureEnclaveStore()
        _ => EncryptedFileStore(key: Environment.get("MASTER_KEY"))
    }
    
    // Store credentials securely
    function store(clientId: String, credentialType: String, credentials: Credentials) {
        // Automatic encryption and access control
        store.set(
            key: "${clientId}:${credentialType}",
            value: credentials,
            access: {
                roles: ["admin", "service_account"],
                audit: true  // Automatically log all access
            }
        )
    }
    
    // Retrieve credentials with automatic audit logging
    function retrieve(clientId: String, credentialType: String) -> Result<Credentials> {
        return store.get("${clientId}:${credentialType}")
    }
}
```

### 4. Automated Reporting

Generate client-ready reports with minimal code:

```clarity
// Automated report generation
service ReportGenerator on schedule "0 0 * * 1" {  // Every Monday at midnight
    function generateClientReports() {
        // For each client
        for each client in ClientRegistry.activeClients {
            // Generate report using data from multiple sources
            let report = Report.create("WeeklyStatus") {
                client: client,
                period: DateRange.lastWeek(),
                sections: [
                    SystemStatusSection(
                        data: MetricsStore.forClient(client.id).lastWeek()
                    ),
                    TicketSummarySection(
                        data: psa.getTicketsForClient(client.id, DateRange.lastWeek())
                    ),
                    SecurityIncidentSection(
                        data: SecurityMonitor.getIncidentsForClient(client.id, DateRange.lastWeek())
                    ),
                    RecommendationsSection(
                        data: RecommendationEngine.forClient(client.id)
                    )
                ]
            }
            
            // Store report
            ReportStore.save(report)
            
            // Email if client has email reporting enabled
            if client.preferences.emailReports {
                EmailService.send({
                    to: client.reportRecipients,
                    subject: "Weekly Status Report - ${DateRange.lastWeek().toShortString()}",
                    body: report.toEmailBody(),
                    attachments: [report.toPDF()]
                })
            }
        }
    }
}
```

### 5. Self-Healing Systems

Clarity makes it easy to build resilient, self-healing solutions:

```clarity
// Self-healing agent
service SelfHealingAgent daemon {
    // Health check runs regularly
    on schedule "*/5 * * * *" {  // Every 5 minutes
        healthCheck()
    }
    
    // Deployment verification after updates
    on event SystemUpdated {
        verifyDeployment()
    }
    
    // Main health check function
    private function healthCheck() {
        // Check all vital services
        let serviceStatuses = for each service in VitalServices.all {
            monitor(service)
        }
        
        // Handle any failed services
        for each status in serviceStatuses where status.state != "running" {
            log.warning("Service ${status.name} is in state ${status.state}")
            
            // Try to restart the service
            if status.canRestart {
                let result = try {
                    status.service.restart()
                    return "restarted"
                } catch (error) {
                    log.error("Failed to restart ${status.name}: ${error.message}")
                    return "restart_failed"
                }
            } else {
                log.error("Service ${status.name} cannot be automatically restarted")
                NotificationService.alert("Service ${status.name} requires manual intervention")
            }
        }
    }
    
    // Verify system is healthy after updates
    private function verifyDeployment() {
        // Series of checks to verify successful deployment
        let checks = [
            checkDiskSpace(),
            checkMemoryUsage(),
            checkNetworkConnectivity(),
            checkRequiredServices(),
            checkLogForErrors()
        ]
        
        if checks.all(check => check.passed) {
            log.info("Deployment verification successful")
        } else {
            let failedChecks = checks.filter(check => !check.passed)
            log.error("Deployment verification failed: ${failedChecks.map(c => c.name).join(', ')}")
            
            // Attempt to rollback if possible
            if canRollback() {
                log.warning("Attempting to rollback to previous version")
                rollback()
            } else {
                NotificationService.alert("System in potentially unstable state after update")
            }
        }
    }
}
```

## Benefits for MSPs

- **Reduced Complexity**: Clarity's natural language syntax makes complex MSP automation more approachable
- **Improved Reliability**: Built-in error handling and self-healing capabilities reduce outages
- **Automatic Safeguards**: The language prevents common security and operational mistakes
- **Maintenance Efficiency**: Code organization principles keep systems maintainable as they grow
- **Integration Simplicity**: First-class integration capabilities make connecting to various client systems easier

By combining these features, Clarity allows MSPs to create more reliable, secure, and efficient monitoring and management solutions with less code and fewer bugs.