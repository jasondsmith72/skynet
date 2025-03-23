# Batch Client Processing

MSPs often need to perform the same operation across multiple client environments. Clarity provides safe, efficient patterns for batch processing with built-in safeguards.

## Pattern Example

```clarity
// Process operations across multiple clients with safety controls
module BatchProcessor {
    // Process an operation across multiple clients
    function batchProcess(
        clients: List<Client>,
        operation: Function<Client, Result<void>>,
        options: BatchOptions = BatchOptions.default
    ) -> BatchResult {
        // Initialize result tracking
        let results = BatchResult()
        
        // Validate operation on test client if available
        if options.validateFirst && options.testClient != null {
            let testResult = try {
                operation(options.testClient)
                return "success"
            } catch (error) {
                return "failed: ${error.message}"
            }
            
            if testResult != "success" {
                return BatchResult(
                    overallStatus: "aborted",
                    message: "Validation failed on test client: ${testResult}",
                    processed: 0,
                    succeeded: 0,
                    failed: 0,
                    details: {}
                )
            }
        }
        
        // Process clients based on concurrency option
        if options.concurrent {
            // Process in parallel with rate limiting
            let processedClients = for each client in clients 
                parallel(maxConcurrent: options.maxConcurrent) {
                processClient(client, operation)
            }
            
            for each result in processedClients {
                results.addResult(result)
            }
        } else {
            // Process sequentially
            for each client in clients {
                let result = processClient(client, operation)
                results.addResult(result)
                
                // Check for abort conditions
                if options.abortThreshold > 0 && 
                   results.failureRate >= options.abortThreshold {
                    results.overallStatus = "aborted"
                    results.message = "Batch processing aborted: failure rate exceeded threshold"
                    break
                }
            }
        }
        
        return results
    }
    
    // Process a single client
    private function processClient(
        client: Client, 
        operation: Function<Client, Result<void>>
    ) -> ClientResult {
        try {
            // Create tenant context for the client
            using TenantContext(client.id) {
                // Execute the operation
                let startTime = now()
                let result = operation(client)
                let duration = now() - startTime
                
                if result is Success {
                    return ClientResult(
                        clientId: client.id,
                        status: "success",
                        duration: duration,
                        error: null
                    )
                } else {
                    return ClientResult(
                        clientId: client.id,
                        status: "failed",
                        duration: duration,
                        error: result.error.message
                    )
                }
            }
        } catch (error) {
            // Handle any uncaught exceptions
            return ClientResult(
                clientId: client.id,
                status: "error",
                duration: 0,
                error: error.message
            )
        }
    }
}

// Example usage
function updateAntivirusOnAllClients() {
    let clients = ClientDirectory.getActive()
    
    let results = BatchProcessor.batchProcess(
        clients,
        client => AVService.updateDefinitions(client),
        {
            concurrent: true,
            maxConcurrent: 5,
            validateFirst: true,
            testClient: ClientDirectory.getTestClient(),
            abortThreshold: 0.2  // Abort if more than 20% of clients fail
        }
    )
    
    // Generate report
    let report = BatchReportGenerator.generate(results)
    
    // Notify admin
    NotificationService.email(
        to: "admin@msp.com",
        subject: "Antivirus Update Results",
        body: report.toEmailBody()
    )
}
```

## Key Features Highlighted

### 1. Safety First Approach

The pattern includes multiple safety mechanisms, including pre-validation on a test client, failure thresholds, and comprehensive error handling.

```clarity
// Validate operation on test client if available
if options.validateFirst && options.testClient != null {
    let testResult = try {
        operation(options.testClient)
        return "success"
    } catch (error) {
        return "failed: ${error.message}"
    }
    
    if testResult != "success" {
        return BatchResult(
            overallStatus: "aborted",
            message: "Validation failed on test client: ${testResult}",
            // ...
        )
    }
}
```

### 2. Flexible Concurrency

Operations can be performed sequentially or in parallel with configurable concurrency limits, adapting to available resources and client requirements.

```clarity
// Process in parallel with rate limiting
let processedClients = for each client in clients 
    parallel(maxConcurrent: options.maxConcurrent) {
    processClient(client, operation)
}
```

### 3. Tenant Context Isolation

Each client operation runs in its own tenant context, ensuring proper isolation and preventing cross-client data leakage.

```clarity
// Create tenant context for the client
using TenantContext(client.id) {
    // Execute the operation within this context
    let result = operation(client)
    // ...
}
```

### 4. Automatic Failure Handling

The pattern includes abort thresholds to prevent continued processing when too many failures occur, protecting against systemic issues.

```clarity
// Check for abort conditions
if options.abortThreshold > 0 && 
   results.failureRate >= options.abortThreshold {
    results.overallStatus = "aborted"
    results.message = "Batch processing aborted: failure rate exceeded threshold"
    break
}
```

### 5. Comprehensive Result Tracking

All operations are tracked with detailed results, including success/failure status, duration, and error messages.

```clarity
return ClientResult(
    clientId: client.id,
    status: "failed",
    duration: duration,
    error: result.error.message
)
```

### 6. Higher-Order Functions

The pattern uses higher-order functions to accept operations as parameters, making it highly reusable across different types of batch operations.

```clarity
function batchProcess(
    clients: List<Client>,
    operation: Function<Client, Result<void>>,
    options: BatchOptions = BatchOptions.default
) -> BatchResult {
    // ...
}
```

## Benefits for MSPs

- **Reduced Risk**: Test operations before applying them broadly
- **Operational Efficiency**: Process multiple clients simultaneously with controlled parallelism
- **Proper Isolation**: Ensure operations on one client don't affect others
- **Fail-Safe Mechanisms**: Abort processing when too many failures occur
- **Comprehensive Reporting**: Generate detailed reports of batch operations
- **Resource Management**: Control concurrency to manage system load
- **Reusability**: Apply the same pattern to different types of operations

## Common Usage Scenarios

1. **Software Updates**: Deploying patches or updates across client environments
2. **Security Policy Updates**: Implementing new security policies for all clients
3. **Compliance Checks**: Running compliance scans across client systems
4. **Configuration Changes**: Applying standardized configuration changes
5. **Data Collection**: Gathering metrics or reports from client environments
6. **Backup Verification**: Validating backups across multiple clients
7. **System Health Checks**: Running diagnostics across client infrastructure
