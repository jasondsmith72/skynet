# Remote Script Execution

MSPs frequently need to execute scripts on client systems. Clarity provides a secure, auditable pattern for remote script execution with comprehensive safety controls.

## Pattern Example

```clarity
// Securely execute scripts on remote client machines
module RemoteExecution {
    // Define execution environments
    enum ExecutionEnvironment {
        Windows,
        Linux,
        MacOS
    }
    
    // Define script types
    enum ScriptType {
        PowerShell,
        Bash,
        Python,
        Ruby
    }
    
    // Execute a script on a remote machine
    @requiresPermission(RemoteExecution)
    async function executeScript(
        clientId: UUID,
        machineId: UUID,
        script: Script,
        parameters: Map<String, String> = {},
        options: ExecutionOptions = ExecutionOptions.default
    ) -> ExecutionResult {
        // Log execution attempt
        AuditLog.record("script_execution_attempt", {
            clientId: clientId,
            machineId: machineId,
            scriptId: script.id,
            executedBy: Authentication.currentUser.username,
            timestamp: now()
        })
        
        // Validate script for the target environment
        let machine = DeviceInventory.getMachine(clientId, machineId)
        
        if machine == null {
            return ExecutionResult(
                status: "failed",
                message: "Machine not found",
                output: null,
                exitCode: -1
            )
        }
        
        // Validate script compatibility
        if !script.supportsEnvironment(machine.environment) {
            return ExecutionResult(
                status: "failed",
                message: "Script not supported on target environment: ${machine.environment}",
                output: null,
                exitCode: -1
            )
        }
        
        // Prepare script with parameters
        let preparedScript = script.prepare(parameters)
        
        // Check for malicious content if enabled
        if options.performSecurityScan {
            let scanResult = SecurityScanner.scan(preparedScript)
            
            if scanResult.hasThreat {
                AuditLog.record("script_security_threat", {
                    clientId: clientId,
                    machineId: machineId,
                    scriptId: script.id,
                    threatDetails: scanResult.threatDetails,
                    timestamp: now()
                })
                
                return ExecutionResult(
                    status: "blocked",
                    message: "Security scan detected potential threat: ${scanResult.threatDetails}",
                    output: null,
                    exitCode: -1
                )
            }
        }
        
        // Execute the script
        try {
            let agent = ConnectedAgents.getAgent(clientId, machineId)
            
            if agent == null || !agent.isConnected {
                return ExecutionResult(
                    status: "failed",
                    message: "Agent not connected",
                    output: null,
                    exitCode: -1
                )
            }
            
            // Send script to agent
            let execution = await agent.executeScript(
                preparedScript,
                options.timeoutSeconds,
                options.runAs
            )
            
            // Record successful execution
            AuditLog.record("script_executed", {
                clientId: clientId,
                machineId: machineId,
                scriptId: script.id,
                executedBy: Authentication.currentUser.username,
                exitCode: execution.exitCode,
                timestamp: now()
            })
            
            return ExecutionResult(
                status: execution.exitCode == 0 ? "success" : "failed",
                message: execution.exitCode == 0 ? "Script executed successfully" : "Script failed with exit code ${execution.exitCode}",
                output: execution.output,
                exitCode: execution.exitCode
            )
        } catch (error) {
            // Record execution error
            AuditLog.record("script_execution_error", {
                clientId: clientId,
                machineId: machineId,
                scriptId: script.id,
                error: error.message,
                timestamp: now()
            })
            
            return ExecutionResult(
                status: "error",
                message: "Execution error: ${error.message}",
                output: null,
                exitCode: -1
            )
        }
    }
    
    // Schedule a script to run at a specified time
    @requiresPermission(ScheduleScript)
    function scheduleScript(
        clientId: UUID,
        machineId: UUID,
        script: Script,
        parameters: Map<String, String> = {},
        schedule: Schedule,
        options: ExecutionOptions = ExecutionOptions.default
    ) -> ScheduleResult {
        // Validate input
        let machine = DeviceInventory.getMachine(clientId, machineId)
        
        if machine == null {
            return ScheduleResult(
                status: "failed",
                message: "Machine not found",
                scheduleId: null
            )
        }
        
        // Create schedule entry
        let scheduleEntry = ScheduledTasks.create({
            clientId: clientId,
            machineId: machineId,
            scriptId: script.id,
            parameters: parameters,
            schedule: schedule,
            options: options,
            createdBy: Authentication.currentUser.username,
            createdAt: now(),
            status: "scheduled"
        })
        
        // Log scheduling
        AuditLog.record("script_scheduled", {
            scheduleId: scheduleEntry.id,
            clientId: clientId,
            machineId: machineId,
            scriptId: script.id,
            schedule: schedule.toString(),
            scheduledBy: Authentication.currentUser.username,
            timestamp: now()
        })
        
        return ScheduleResult(
            status: "scheduled",
            message: "Script scheduled successfully",
            scheduleId: scheduleEntry.id
        )
    }
}
```

## Key Features Highlighted

### 1. Permission-Based Access Control

The pattern uses permission annotations to ensure only authorized users can execute or schedule scripts.

```clarity
@requiresPermission(RemoteExecution)
async function executeScript(...) {
    // ...
}

@requiresPermission(ScheduleScript)
function scheduleScript(...) {
    // ...
}
```

### 2. Comprehensive Audit Logging

Every stage of script execution is logged, from initial attempts to final results, providing a complete audit trail.

```clarity
// Log execution attempt
AuditLog.record("script_execution_attempt", {
    clientId: clientId,
    machineId: machineId,
    scriptId: script.id,
    executedBy: Authentication.currentUser.username,
    timestamp: now()
})
```

### 3. Environment Validation

Scripts are validated against the target environment to ensure compatibility before execution.

```clarity
// Validate script compatibility
if !script.supportsEnvironment(machine.environment) {
    return ExecutionResult(
        status: "failed",
        message: "Script not supported on target environment: ${machine.environment}",
        // ...
    )
}
```

### 4. Security Scanning

Optional security scanning can detect potentially malicious scripts before execution.

```clarity
// Check for malicious content if enabled
if options.performSecurityScan {
    let scanResult = SecurityScanner.scan(preparedScript)
    
    if scanResult.hasThreat {
        // Log and block execution
        // ...
    }
}
```

### 5. Parameter Substitution

Scripts can accept parameters that are safely substituted before execution.

```clarity
// Prepare script with parameters
let preparedScript = script.prepare(parameters)
```

### 6. Async Execution

Script execution is asynchronous, allowing the system to handle long-running scripts without blocking.

```clarity
async function executeScript(...) {
    // ...
    
    // Send script to agent
    let execution = await agent.executeScript(
        preparedScript,
        options.timeoutSeconds,
        options.runAs
    )
    
    // ...
}
```

### 7. Scheduled Execution

Scripts can be scheduled to run at specified times, with full logging and tracking.

```clarity
function scheduleScript(
    // ...
    schedule: Schedule,
    // ...
) {
    // Create schedule entry
    let scheduleEntry = ScheduledTasks.create({
        // ...
        schedule: schedule,
        // ...
    })
    
    // ...
}
```

## Benefits for MSPs

- **Enhanced Security**: Multiple validation and security checks protect against malicious scripts
- **Complete Audit Trail**: Comprehensive logging for compliance and troubleshooting
- **Cross-Platform Support**: Execute scripts across different operating systems
- **Flexible Scheduling**: Run scripts immediately or schedule for later execution
- **Parameterization**: Pass parameters to scripts without modifying the original code
- **Permission Controls**: Restrict script execution to authorized personnel
- **Error Handling**: Comprehensive error detection and reporting

## Common Usage Scenarios

1. **Automated Maintenance**: Schedule routine maintenance tasks
2. **Emergency Remediation**: Execute scripts to fix critical issues
3. **Data Collection**: Gather system information for reporting
4. **Configuration Updates**: Deploy standardized configurations
5. **Software Installation**: Install or update software across client environments
6. **Security Response**: Execute scripts to address security incidents
7. **System Diagnostics**: Run diagnostic scripts to troubleshoot issues
8. **Compliance Checks**: Execute scripts to verify compliance status
