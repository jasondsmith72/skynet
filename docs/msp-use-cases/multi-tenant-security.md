# Multi-Tenant Security in Clarity

One of the core challenges for MSPs is securely managing multiple client environments within a single system. Clarity provides built-in constructs for handling multi-tenancy safely and efficiently.

## Tenant Isolation Models

Clarity offers several built-in tenant isolation models:

```clarity
// Database-per-tenant model
@multiTenant(isolation: physical, mechanism: database)
service ClientDataService {
    // Each tenant gets its own database
    // Connection strings configured per tenant
}

// Schema-per-tenant model
@multiTenant(isolation: logical, mechanism: schema)
service ResourceService {
    // Each tenant gets its own schema in a shared database
    // Automatic schema prefixing
}

// Row-level-security model
@multiTenant(isolation: row, mechanism: filter)
service SharedService {
    // Tenants share tables, but rows are filtered by tenant ID
    // Automatic WHERE clause injection
}

// Hybrid model
@multiTenant(isolation: adaptive)
service AdaptiveService {
    // System automatically selects the appropriate isolation model
    // based on tenant requirements, data volume, and usage patterns
}
```

## Tenant Context Management

```clarity
// Tenant context is propagated automatically
service ClientAPI {
    // Authentication establishes tenant context
    function authenticate(credentials: Credentials) {
        // Successful authentication sets TenantContext
        let user = UserDatabase.verifyCredentials(credentials)
        
        if user != null {
            // Set the tenant context for this session
            TenantContext.set(user.tenantId)
            return AuthResult.success(user)
        }
        
        return AuthResult.failure("Invalid credentials")
    }
    
    // All data access automatically filtered by tenant
    function getUserData(userId: UUID) {
        // No need to explicitly filter by tenant
        // Current tenant context is automatically applied
        return UserDatabase.find(userId)
    }
    
    // Cross-tenant operations require explicit permission
    @requiresPermission(CrossTenantAccess)
    function compareTenantMetrics(tenantIds: List<TenantId>) {
        // Each access is checked and logged
        let results = []
        
        for each tenantId in tenantIds {
            // Explicitly switch context with audit logging
            using temporary TenantContext(tenantId) {
                results.add(MetricsService.getSummary())
            }
        }
        
        return results
    }
}
```

## Tenant Data Segregation

```clarity
// Automatic tenant data separation
module ClientData {
    // Collection with tenant isolation
    @tenantIsolated
    collection ClientRecords {
        id: UUID
        name: String
        data: Map<String, Any>
    }
    
    // All operations automatically scoped to current tenant
    function getClient(id: UUID) {
        // Equivalent to:
        // SELECT * FROM ClientRecords WHERE id = ? AND tenant_id = current_tenant_id
        return ClientRecords.find(id)
    }
    
    // Data migration between tenants
    @requiresPermission(DataMigration)
    function migrateClient(clientId: UUID, targetTenant: TenantId) {
        let client = ClientRecords.find(clientId)
        
        if client == null {
            return Error("Client not found")
        }
        
        // Operations on other tenants require explicit context
        using TenantContext(targetTenant) {
            // Record is copied to target tenant
            ClientRecords.insert(client)
        }
        
        // Original record in current tenant
        ClientRecords.archive(clientId)
        
        // Create audit trail for compliance
        AuditLog.record({
            action: "client_migration",
            clientId: clientId,
            fromTenant: TenantContext.current,
            toTenant: targetTenant,
            timestamp: now(),
            performedBy: Authentication.currentUser
        })
        
        return Success
    }
}
```

## Tenant-Aware Permission Model

```clarity
// Role-based access control with tenant context
module Permissions {
    // Define roles and permissions
    enum Permission {
        ViewClient,
        EditClient,
        DeleteClient,
        AdminAccess,
        CrossTenantAccess,
        // ...other permissions
    }
    
    // Define role hierarchy
    role Viewer {
        permissions: [Permission.ViewClient]
    }
    
    role Editor extends Viewer {
        permissions: [Permission.EditClient]
    }
    
    role Admin extends Editor {
        permissions: [Permission.DeleteClient, Permission.AdminAccess]
    }
    
    role SuperAdmin extends Admin {
        permissions: [Permission.CrossTenantAccess]
    }
    
    // Check permissions with tenant awareness
    function hasPermission(user: User, permission: Permission, targetTenant: TenantId) -> Boolean {
        // Super users can do anything
        if user.role == SuperAdmin {
            return true
        }
        
        // Cross-tenant access requires special permission
        if targetTenant != user.tenantId && permission != Permission.CrossTenantAccess {
            return user.hasPermission(Permission.CrossTenantAccess)
        }
        
        // Normal permission check within tenant
        return user.hasPermission(permission)
    }
    
    // Apply permission check with tenant context
    function enforcePermission(permission: Permission) {
        let user = Authentication.currentUser
        let targetTenant = TenantContext.current
        
        guard hasPermission(user, permission, targetTenant) else {
            throw PermissionDeniedException(
                "User ${user.id} does not have permission ${permission} in tenant ${targetTenant}"
            )
        }
    }
}
```

## Shared Resource Management

```clarity
// Handling shared resources across tenants
module SharedResources {
    // Define resource with tenant-specific configurations
    @shared
    resource EmailService {
        // Global configuration
        serverUrl: String = "smtp.example.com"
        port: Integer = 587
        
        // Tenant-specific configuration
        @perTenant
        settings: EmailSettings
        
        // Usage tracking per tenant
        @perTenant
        usageMetrics: UsageMetrics
    }
    
    // Access shared resource with tenant context
    function sendEmail(to: String, subject: String, body: String) {
        // Get the tenant-specific settings
        let settings = EmailService.settings.forTenant(TenantContext.current)
        
        // Send email using tenant-specific settings
        let result = EmailService.send({
            to: to,
            subject: subject,
            body: body,
            from: settings.fromAddress,
            replyTo: settings.replyToAddress,
            signature: settings.emailSignature
        })
        
        // Update usage metrics for current tenant
        let metrics = EmailService.usageMetrics.forTenant(TenantContext.current)
        metrics.emailsSent += 1
        metrics.lastSentAt = now()
        
        return result
    }
    
    // Administrator functions to view all tenant metrics
    @requiresPermission(ViewAllTenantMetrics)
    function getResourceUsageReport() -> ResourceUsageReport {
        let report = ResourceUsageReport()
        
        // Get all active tenants
        let tenants = TenantDirectory.active()
        
        for each tenant in tenants {
            let metrics = EmailService.usageMetrics.forTenant(tenant.id)
            report.addTenantMetrics(tenant.id, tenant.name, metrics)
        }
        
        return report
    }
}
```

## Tenant Data Backup and Recovery

```clarity
// Tenant-aware backup and recovery
module BackupService {
    // Schedule backups for each tenant
    @schedule("0 1 * * *")  // Daily at 1 AM
    function backupAllTenants() {
        let tenants = TenantDirectory.active()
        
        // Process each tenant in parallel with rate limiting
        for each tenant in tenants parallel(maxConcurrent: 5) {
            backupTenant(tenant.id)
        }
    }
    
    // Backup a specific tenant's data
    function backupTenant(tenantId: TenantId) {
        // Create context for the tenant
        using TenantContext(tenantId) {
            // Get tenant-specific backup configuration
            let config = BackupConfig.forTenant(tenantId)
            
            // Create backup with tenant isolation
            let backup = TenantBackup.create({
                tenantId: tenantId,
                timestamp: now(),
                retentionPeriod: config.retentionPeriod,
                encryptionKey: SecureKeyGenerator.generateKey()
            })
            
            // Back up each data collection
            for each collection in TenantSchema.collections {
                backup.addCollection(collection)
            }
            
            // Store backup with tenant isolation
            BackupStorage.store(backup)
            
            // Notify tenant administrators
            NotificationService.notifyTenant(
                tenantId,
                "backup_complete",
                { backupId: backup.id, timestamp: backup.timestamp }
            )
        }
    }
    
    // Restore a specific tenant from backup
    @requiresPermission(RestoreTenantData)
    function restoreTenant(tenantId: TenantId, backupId: UUID) {
        // Verify the backup belongs to the tenant
        let backup = BackupStorage.find(backupId)
        
        guard backup != null && backup.tenantId == tenantId else {
            return Error("Invalid backup ID or tenant mismatch")
        }
        
        // Create restore job
        let restoreJob = RestoreJob.create({
            tenantId: tenantId,
            backupId: backupId,
            startedAt: now(),
            startedBy: Authentication.currentUser.id
        })
        
        // Execute restore with tenant isolation
        using TenantContext(tenantId) {
            // First create a backup of current state
            let preRestoreBackup = backupTenant(tenantId)
            restoreJob.preRestoreBackupId = preRestoreBackup.id
            
            // Then restore from the selected backup
            for each collection in backup.collections {
                TenantSchema.restore(collection)
            }
            
            restoreJob.complete()
        }
        
        return Success(restoreJob)
    }
}
```

## Benefits for MSPs

- **Reduced Cross-Tenant Vulnerabilities**: The language prevents accidental data leakage between tenants
- **Simplified Compliance**: Built-in controls for tenant separation satisfy regulatory requirements
- **Increased Operational Efficiency**: Developers focus on business logic while the framework handles isolation
- **Flexible Deployment Models**: Support for different isolation approaches based on client requirements
- **Enhanced Auditability**: Automatic logging of all cross-tenant operations

Clarity's multi-tenant architecture enables MSPs to securely manage multiple clients while minimizing the risk of data leakage or unauthorized access between tenants.