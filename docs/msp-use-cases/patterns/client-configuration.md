# Client Configuration Management

In MSP environments, managing configurations for multiple clients is a common challenge. Clarity provides elegant solutions for handling client-specific configurations with inheritance and overrides.

## Pattern Example

```clarity
// Manage client configurations with inheritance and overrides
module ClientConfigManager {
    // Base configuration for all clients
    const baseConfig = {
        monitoring: {
            checkInterval: 5 minutes,
            alertThreshold: "warning",
            retentionPeriod: 90 days
        },
        security: {
            passwordPolicy: {
                minLength: 12,
                requireSpecialChars: true,
                requireNumbers: true,
                maxAge: 90 days
            },
            mfaRequired: true,
            sessionTimeout: 15 minutes
        },
        backup: {
            schedule: "0 1 * * *",  // Daily at 1 AM
            retentionPolicy: {
                daily: 7 days,
                weekly: 4 weeks,
                monthly: 12 months
            },
            validationFrequency: 7 days
        }
    }
    
    // Client-specific overrides
    @multiTenant
    collection ClientConfigs {
        clientId: UUID
        configOverrides: Map<String, Any>
        lastUpdated: DateTime
        updatedBy: String
    }
    
    // Get effective configuration for a client
    function getConfig(clientId: UUID) -> ClientConfig {
        // Get client-specific overrides
        let clientOverrides = ClientConfigs.find(clientId)?.configOverrides ?? {}
        
        // Deep merge with base config, with client overrides taking precedence
        return deepMerge(baseConfig, clientOverrides)
    }
    
    // Update client configuration
    function updateConfig(clientId: UUID, overrides: Map<String, Any>) -> Result<void> {
        // Validate configuration changes
        let validationResult = validateConfigChanges(overrides)
        
        if validationResult.hasErrors {
            return Error(validationResult.errors)
        }
        
        // Find existing config or create new one
        let existing = ClientConfigs.find(clientId)
        
        if existing != null {
            // Update existing config
            existing.configOverrides = deepMerge(existing.configOverrides, overrides)
            existing.lastUpdated = now()
            existing.updatedBy = Authentication.currentUser.username
            
            ClientConfigs.update(existing)
        } else {
            // Create new config
            ClientConfigs.insert({
                clientId: clientId,
                configOverrides: overrides,
                lastUpdated: now(),
                updatedBy: Authentication.currentUser.username
            })
        }
        
        // Trigger config refresh for affected services
        EventBus.publish(ConfigUpdatedEvent(clientId))
        
        return Success
    }
    
    // Apply configuration to a client system
    function applyConfig(clientId: UUID, system: ClientSystem) -> Result<void> {
        // Get effective configuration
        let config = getConfig(clientId)
        
        // Apply configuration to the system
        try {
            system.configure(config)
            
            // Log successful configuration
            AuditLog.record("config_applied", {
                clientId: clientId,
                systemId: system.id,
                timestamp: now(),
                appliedBy: Authentication.currentUser.username
            })
            
            return Success
        } catch (error) {
            // Log configuration failure
            AuditLog.record("config_failed", {
                clientId: clientId,
                systemId: system.id,
                timestamp: now(),
                error: error.message,
                attemptedBy: Authentication.currentUser.username
            })
            
            return Error(error)
        }
    }
}
```

## Key Features Highlighted

### 1. Default Configuration with Overrides

The pattern establishes a standard `baseConfig` that applies to all clients by default. Client-specific overrides are stored in a multi-tenant collection, ensuring each client can have customized settings without duplicating the entire configuration.

```clarity
// Base configuration for all clients
const baseConfig = {
    monitoring: {
        checkInterval: 5 minutes,
        // More settings...
    },
    // More categories...
}

// Client-specific overrides
@multiTenant
collection ClientConfigs {
    clientId: UUID
    configOverrides: Map<String, Any>
    // More fields...
}
```

### 2. Tenant Isolation

Using the `@multiTenant` annotation ensures that client configuration data is properly isolated, preventing one client's settings from leaking into another's.

### 3. Deep Merging

The pattern uses deep merging to combine base configurations with client-specific overrides, allowing clients to override only the specific settings they need without having to redefine everything.

```clarity
// Deep merge with base config, with client overrides taking precedence
return deepMerge(baseConfig, clientOverrides)
```

### 4. Validation

Configuration changes are validated before being applied, ensuring they meet required standards and preventing invalid configurations.

```clarity
// Validate configuration changes
let validationResult = validateConfigChanges(overrides)

if validationResult.hasErrors {
    return Error(validationResult.errors)
}
```

### 5. Audit Logging

All configuration changes and applications are automatically logged, providing a complete audit trail for compliance and troubleshooting.

```clarity
// Log successful configuration
AuditLog.record("config_applied", {
    clientId: clientId,
    systemId: system.id,
    timestamp: now(),
    appliedBy: Authentication.currentUser.username
})
```

### 6. Event-Based Notifications

When configurations change, the system publishes events that other components can subscribe to, enabling real-time updates across the system.

```clarity
// Trigger config refresh for affected services
EventBus.publish(ConfigUpdatedEvent(clientId))
```

## Benefits for MSPs

- **Standardization with Flexibility**: Maintain standard configurations while accommodating client-specific needs
- **Reduced Duplication**: Store only the differences for each client, not the entire configuration
- **Controlled Changes**: Validate changes before applying them to prevent misconfiguration
- **Comprehensive Auditing**: Track all configuration changes for compliance and troubleshooting
- **Simplified Management**: Easily see what's different about a particular client's configuration
- **Scalable**: Works efficiently whether you have dozens or thousands of clients

## Common Usage Scenarios

1. **Standardizing Security Policies**: Define baseline security requirements with client-specific adjustments
2. **Backup Configuration**: Standardize backup schedules and retention policies with client-specific exceptions
3. **Monitoring Settings**: Set standard monitoring thresholds while accommodating different client needs
4. **Service Level Configurations**: Adjust service levels based on client agreements
5. **Compliance Requirements**: Handle different regulatory requirements across client industries
