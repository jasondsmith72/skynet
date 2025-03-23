# Secure API Patterns in Clarity

Clarity provides built-in constructs for creating secure APIs with minimal code. This example demonstrates how to build APIs that are secure by default while remaining flexible and efficient.

## Basic Secure API

```clarity
// A simple secure API with authentication and authorization
service CustomerAPI on port 443 {
    // TLS configuration is declarative and enforced
    @tls(minVersion: "1.2", preferredCiphers: ["TLS_AES_256_GCM_SHA384"])
    
    // Security headers automatically applied to all responses
    @securityHeaders(
        hsts: true,
        contentSecurity: "default-src 'self'",
        frameOptions: "DENY",
        xssProtection: true
    )
    
    // Rate limiting to prevent abuse
    @rateLimit(
        limit: 100 per minute,
        burstLimit: 20,
        keyBy: "ip"
    )
    
    // Authentication options
    @authenticate(
        methods: [JWT, OAuth2, APIKey],
        headerName: "Authorization",
        cookieName: "session",
        failureResponse: "Unauthorized",
        redirectTo: "/login"
    )
    
    // Define routes with authorization
    @authorize(roles: ["admin", "support"])
    GET "/customers" -> List<CustomerSummary> {
        return CustomerDatabase.listAll()
    }
    
    @authorize(roles: ["admin", "support", "customer"])
    GET "/customers/:id" (id: UUID) -> CustomerDetail {
        // Automatic tenant isolation applied
        return CustomerDatabase.find(id)
    }
    
    @authorize(roles: ["admin"])
    POST "/customers" (customer: NewCustomerRequest) -> CustomerDetail {
        // Input validation happens automatically based on types
        // SQL injection prevention is automatic
        let newCustomer = CustomerDatabase.create(customer)
        
        // Audit logging for sensitive operations
        AuditLog.record("customer_created", { id: newCustomer.id })
        
        return newCustomer
    }
    
    @authorize(roles: ["admin"])
    PUT "/customers/:id" (id: UUID, update: CustomerUpdateRequest) -> CustomerDetail {
        // Check if customer exists
        let customer = CustomerDatabase.find(id)
        
        if customer == null {
            return HttpResponse.notFound("Customer not found")
        }
        
        // Update and save
        let updated = CustomerDatabase.update(id, update)
        
        // Audit logging
        AuditLog.record("customer_updated", {
            id: id,
            changes: detectChanges(customer, updated)
        })
        
        return updated
    }
    
    // Error handling is built in
    on error DatabaseError {
        // Log database errors but don't expose details to client
        log.error("Database error: ${error.message}")
        return HttpResponse.serverError("A database error occurred")
    }
    
    on error ValidationError {
        // Return validation errors with details
        return HttpResponse.badRequest(error.validationMessages)
    }
    
    on error {
        // Generic error handler
        log.error("Unhandled error: ${error.message}")
        return HttpResponse.serverError("An unexpected error occurred")
    }
}
```

## Multi-Authentication Methods

```clarity
// Supporting different authentication methods for different clients
service PaymentAPI {
    // Define different authentication schemes
    const authSchemes = {
        internal: AuthScheme.JWT({
            secret: SecretStore.get("jwt_secret"),
            issuer: "payment-system",
            expiresIn: 1 hour
        }),
        
        partner: AuthScheme.OAuth2({
            authorizationServer: "https://auth.partner.com",
            clientId: SecretStore.get("oauth_client_id"),
            clientSecret: SecretStore.get("oauth_client_secret"),
            scopes: ["payments.read", "payments.write"]
        }),
        
        legacy: AuthScheme.APIKey({
            headerName: "X-API-Key",
            keyStore: LegacyKeyStore
        })
    }
    
    // Route with multiple auth options
    @authenticate(schemes: [authSchemes.internal, authSchemes.partner])
    POST "/payments" (payment: PaymentRequest) -> PaymentResult {
        // Both internal JWT and partner OAuth2 tokens are accepted
        return processPayment(payment)
    }
    
    // Legacy endpoint with API key auth
    @authenticate(schemes: [authSchemes.legacy])
    @deprecated("Use /payments endpoint with OAuth2 instead")
    POST "/legacy/process-payment" (payment: LegacyPaymentRequest) -> LegacyPaymentResult {
        // Transform and process
        let modernPayment = transformLegacyPayment(payment)
        let result = processPayment(modernPayment)
        return transformToLegacyResult(result)
    }
    
    // Internal-only endpoint
    @authenticate(schemes: [authSchemes.internal])
    POST "/refunds" (refund: RefundRequest) -> RefundResult {
        // Only internal JWT auth is accepted
        return processRefund(refund)
    }
    
    // Function to handle payments
    function processPayment(payment: PaymentRequest) -> PaymentResult {
        // Get authentication context
        let auth = Authentication.current
        
        // Behavior varies based on authentication method
        let paymentProcessor = match auth.scheme {
            authSchemes.internal => InternalPaymentProcessor
            authSchemes.partner => PartnerPaymentProcessor(auth.partnerId)
            authSchemes.legacy => LegacyPaymentProcessor
            _ => throw AuthenticationError("Invalid authentication scheme")
        }
        
        // Process payment
        return paymentProcessor.process(payment)
    }
}
```

## API Versioning and Compatibility

```clarity
// API versioning with security preservation across versions
service ProductAPI version 2 {
    // Define version compatibility
    @compatibility(
        v1: {
            endpoints: ["/products", "/products/:id"],
            automaticTransforms: true
        }
    )
    
    // Current version endpoints
    GET "/products" -> List<ProductV2> {
        return ProductDatabase.listAllV2()
    }
    
    GET "/products/:id" (id: UUID) -> ProductV2 {
        return ProductDatabase.findV2(id)
    }
    
    // New in v2 - no v1 equivalent
    GET "/products/:id/related" (id: UUID) -> List<ProductV2> {
        return ProductDatabase.findRelated(id)
    }
    
    // Compatibility layer for v1 clients
    // These aren't exposed directly but used for automatic transforms
    transformer ProductV1 to ProductV2 {
        return ProductV2 {
            id: input.id,
            name: input.name,
            description: input.description,
            price: input.price,
            // New in v2
            specifications: extractSpecifications(input.description),
            categoryId: input.category,
            images: [input.imageUrl],
            // Security fields are handled automatically
            createdBy: input.createdBy,
            lastModifiedBy: input.lastModifiedBy
        }
    }
    
    transformer ProductV2 to ProductV1 {
        return ProductV1 {
            id: input.id,
            name: input.name,
            description: input.specifications 
                ? input.description + "\n\nSpecifications: " + input.specifications
                : input.description,
            price: input.price,
            category: input.categoryId,
            imageUrl: input.images?.first(),
            // Security fields are handled automatically
            createdBy: input.createdBy,
            lastModifiedBy: input.lastModifiedBy
        }
    }
    
    // Security features apply across versions
    @authenticate(methods: [JWT])
    @authorize(roles: ["admin", "product-manager"])
    POST "/products" (product: ProductV2) -> ProductV2 {
        // Authorization and audit logging work across versions
        return ProductDatabase.create(product)
    }
}
```

## Secure File Transfers

```clarity
// Secure file transfer API
service FileTransferAPI {
    // Upload endpoint with security controls
    @authenticate(methods: [JWT])
    @authorize(roles: ["file-upload"])
    @contentScan(malware: true, sensitive: true)
    @maxFileSize(100 MB)
    @allowedFileTypes(["pdf", "docx", "xlsx", "jpg", "png"])
    POST "/upload" (file: UploadedFile) -> FileReference {
        // Check upload quota
        let user = Authentication.currentUser
        let quota = QuotaService.getRemainingQuota(user.id)
        
        guard file.size <= quota else {
            return Error("Quota exceeded")
        }
        
        // Process upload
        let sanitizedFile = FileSanitizer.sanitize(file)
        
        // Store with encryption
        let reference = SecureFileStore.store(sanitizedFile, {
            ownerId: user.id,
            encryption: EncryptionLevel.AES256,
            retention: 30 days,
            allowedViewers: user.organization.members
        })
        
        // Log upload for compliance
        AuditLog.record("file_uploaded", {
            fileId: reference.id,
            fileName: file.name,
            fileSize: file.size,
            fileType: file.contentType,
            uploadedBy: user.id
        })
        
        return reference
    }
    
    // Download endpoint with security controls
    @authenticate(methods: [JWT])
    @authorize(checkFileAccess: true)  // Check if user can access this file
    @rateLimit(limit: 50 per hour)
    GET "/download/:id" (id: UUID) -> SecureFile {
        let user = Authentication.currentUser
        
        // Get file reference
        let reference = SecureFileStore.getReference(id)
        
        guard reference != null else {
            return Error("File not found")
        }
        
        // Check access permissions
        guard FileAccessControl.canAccess(user, reference) else {
            return Error("Access denied")
        }
        
        // Log download for compliance
        AuditLog.record("file_downloaded", {
            fileId: reference.id,
            fileName: reference.name,
            downloadedBy: user.id
        })
        
        // Stream file with encryption
        return SecureFileStore.stream(reference)
    }
    
    // File sharing endpoint
    @authenticate(methods: [JWT])
    @authorize(checkFileAccess: true)  // Check if user can share this file
    POST "/share/:id" (id: UUID, shareRequest: ShareRequest) -> ShareReference {
        let user = Authentication.currentUser
        
        // Get file reference
        let reference = SecureFileStore.getReference(id)
        
        guard reference != null else {
            return Error("File not found")
        }
        
        // Check sharing permissions
        guard FileAccessControl.canShare(user, reference) else {
            return Error("Sharing not allowed")
        }
        
        // Create secure sharing link
        let share = SecureShareService.create({
            fileId: id,
            createdBy: user.id,
            recipients: shareRequest.recipients,
            expiresAt: shareRequest.expirationDate ?? (now() + 7 days),
            accessCount: shareRequest.maxAccessCount ?? unlimited,
            requiresAuthentication: shareRequest.requireAuth ?? true,
            notifyOnAccess: shareRequest.notifyOnAccess ?? false
        })
        
        // Log sharing for compliance
        AuditLog.record("file_shared", {
            fileId: id,
            sharedBy: user.id,
            recipients: shareRequest.recipients,
            expiresAt: share.expiresAt
        })
        
        return share
    }
}
```

## API Gateway with Advanced Security

```clarity
// API Gateway with security controls
service APIGateway {
    // Gateway configuration
    const config = {
        services: [
            {
                name: "customer-service",
                url: "https://customers.internal",
                pathPrefix: "/customers",
                healthCheck: "/health",
                timeout: 5 seconds,
                circuitBreaker: {
                    failureThreshold: 5,
                    resetTimeout: 30 seconds
                }
            },
            {
                name: "product-service",
                url: "https://products.internal",
                pathPrefix: "/products",
                healthCheck: "/health",
                timeout: 5 seconds,
                circuitBreaker: {
                    failureThreshold: 5,
                    resetTimeout: 30 seconds
                }
            },
            {
                name: "order-service",
                url: "https://orders.internal",
                pathPrefix: "/orders",
                healthCheck: "/health",
                timeout: 10 seconds,
                circuitBreaker: {
                    failureThreshold: 3,
                    resetTimeout: 45 seconds
                }
            }
        ],
        
        securityControls: {
            authentication: AuthScheme.JWT({
                secret: SecretStore.get("gateway_jwt_secret"),
                issuer: "api-gateway",
                expiresIn: 1 hour
            }),
            
            rateLimit: {
                default: 1000 per minute,
                byIp: 100 per minute,
                byUser: 500 per minute,
                byApiKey: 2000 per minute
            },
            
            ipWhitelist: Environment.get("ALLOWED_IPS").split(","),
            ipBlacklist: ThreatIntelligence.getBlockedIps(),
            
            requestValidation: {
                enforceHttps: true,
                maxBodySize: 10 MB,
                requestTimeout: 30 seconds
            }
        }
    }
    
    // Initialize monitoring
    on startup {
        // Start health checks for all services
        for each service in config.services {
            startHealthCheck(service)
        }
        
        // Initialize security controls
        SecurityControls.initialize(config.securityControls)
    }
    
    // Route all traffic through the gateway
    ALL "/:service/*" (service: String, path: String) {
        // Find the target service
        let targetService = config.services.find(s => s.name == service)
        
        if targetService == null {
            return HttpResponse.notFound("Service not found")
        }
        
        // Check circuit breaker
        if CircuitBreaker.isOpen(targetService.name) {
            return HttpResponse.serviceUnavailable("Service temporarily unavailable")
        }
        
        // Apply security controls
        let securityResult = SecurityControls.apply(Request.current)
        
        if securityResult.denied {
            return HttpResponse.forbidden(securityResult.reason)
        }
        
        // Proxy the request to the target service
        try {
            let response = HttpClient.forward(
                Request.current,
                targetService.url + path,
                {
                    timeout: targetService.timeout,
                    headers: {
                        // Add internal tracing headers
                        "X-Request-ID": Request.id,
                        "X-Forwarded-For": Request.clientIp,
                        "X-Original-Host": Request.host,
                        "X-Gateway-Service": "api-gateway"
                    }
                }
            )
            
            // Return the service response
            return response
        } catch (error) {
            // Handle errors
            log.error("Gateway error: ${error.message}")
            
            // Update circuit breaker
            CircuitBreaker.recordFailure(targetService.name)
            
            // Return appropriate error response
            if error is TimeoutError {
                return HttpResponse.gatewayTimeout("Service timed out")
            } else if error is ConnectionError {
                return HttpResponse.badGateway("Cannot connect to service")
            } else {
                return HttpResponse.serverError("Gateway error")
            }
        }
    }
    
    // Health check function
    function startHealthCheck(service: ServiceConfig) {
        // Check service health periodically
        on timer every 30 seconds {
            try {
                let response = HttpClient.get(
                    service.url + service.healthCheck,
                    { timeout: 5 seconds }
                )
                
                if response.status == 200 {
                    // Service is healthy
                    CircuitBreaker.recordSuccess(service.name)
                    HealthStatus.update(service.name, "healthy")
                } else {
                    // Service returned non-200 status
                    CircuitBreaker.recordFailure(service.name)
                    HealthStatus.update(service.name, "unhealthy", response.status)
                }
            } catch (error) {
                // Service is unreachable
                CircuitBreaker.recordFailure(service.name)
                HealthStatus.update(service.name, "unreachable", error.message)
            }
        }
    }
}
```

## GraphQL Security

```clarity
// Secure GraphQL API
service GraphQLAPI {
    // Security configuration
    @authenticate(methods: [JWT])
    @securityHeaders(standard: true)
    @rateLimit(limit: 100 per minute)
    
    // Define GraphQL schema
    schema {
        types: [User, Product, Order],
        queries: [getUser, getProduct, getOrder, searchProducts],
        mutations: [createOrder, updateUser, updateProduct]
    }
    
    // Define types with access control
    type User {
        id: UUID
        username: String
        email: String @authorize(roles: ["admin", "self"])
        role: String @authorize(roles: ["admin"])
        orders: [Order] @authorize(roles: ["admin", "self"])
    }
    
    type Product {
        id: UUID
        name: String
        description: String
        price: Decimal
        inventory: Integer @authorize(roles: ["admin", "inventory-manager"])
        margin: Decimal @authorize(roles: ["admin", "finance"])
    }
    
    type Order {
        id: UUID
        user: User
        products: [Product]
        total: Decimal
        status: String
        paymentDetails: PaymentDetails @authorize(roles: ["admin", "finance", "self"])
    }
    
    // Define query resolvers with authorization
    @authorize(roles: ["admin", "customer-service", "self"])
    query getUser(id: UUID) -> User {
        let user = UserDatabase.find(id)
        
        // Self-access check
        if Authentication.currentUser.role != "admin" &&
           Authentication.currentUser.role != "customer-service" &&
           Authentication.currentUser.id != id {
            throw AuthorizationError("Cannot access other user's data")
        }
        
        return user
    }
    
    @authorize(roles: ["admin", "customer-service", "customer"])
    query getProduct(id: UUID) -> Product {
        return ProductDatabase.find(id)
    }
    
    @authorize(roles: ["admin", "customer-service", "self"])
    query getOrder(id: UUID) -> Order {
        let order = OrderDatabase.find(id)
        
        // Self-access check for customers
        if Authentication.currentUser.role == "customer" &&
           order.userId != Authentication.currentUser.id {
            throw AuthorizationError("Cannot access other user's orders")
        }
        
        return order
    }
    
    // Define mutation resolvers with authorization
    @authorize(roles: ["admin", "customer"])
    mutation createOrder(userId: UUID, products: [UUID], shippingAddress: Address) -> Order {
        // Self-access check for customers
        if Authentication.currentUser.role == "customer" &&
           userId != Authentication.currentUser.id {
            throw AuthorizationError("Cannot create orders for other users")
        }
        
        // Verify product availability
        for each productId in products {
            let product = ProductDatabase.find(productId)
            
            if product == null || product.inventory <= 0 {
                throw ValidationError("Product not available: " + productId)
            }
        }
        
        // Create the order
        let order = OrderService.createOrder(userId, products, shippingAddress)
        
        // Audit logging
        AuditLog.record("order_created", {
            orderId: order.id,
            userId: userId,
            createdBy: Authentication.currentUser.id
        })
        
        return order
    }
    
    // GraphQL security features
    @queryComplexityLimit(100)  // Prevent expensive queries
    @queryDepthLimit(5)         // Prevent deeply nested queries
    @disableIntrospection(Environment.isProd)  // Disable introspection in production
    
    // Handle common GraphQL attacks
    on GQLAttack {
        // Log the attack
        SecurityLog.record("graphql_attack", {
            type: error.type,
            query: error.query,
            ip: Request.clientIp,
            user: Authentication.currentUser?.id
        })
        
        // Block repeated offenders
        let attackCount = SecurityLog.countAttacks(Request.clientIp, last=1 hour)
        
        if attackCount > 5 {
            IPBlocker.blockTemporary(Request.clientIp, duration=1 hour)
        }
        
        return HttpResponse.forbidden("Invalid GraphQL request")
    }
}
```

## Benefits for MSPs

Clarity's secure API features provide several advantages for MSPs:

1. **Secure by Default**: Security features are built into the language rather than bolted on
2. **Reduced Attack Surface**: Common vulnerabilities are eliminated through language design
3. **Compliance Simplification**: Built-in audit logging and access controls help meet regulatory requirements
4. **Developer Productivity**: Less security boilerplate code means faster development
5. **API Gateway Capabilities**: Built-in support for routing, load balancing, and circuit breaking
6. **Multi-Authentication Support**: Flexible authentication options for different client needs
7. **Versioning Support**: Maintain backward compatibility while adding new features
8. **Comprehensive Error Handling**: Clean error recovery with appropriate client responses
9. **GraphQL Security**: Built-in protections against common GraphQL vulnerabilities

The language's declarative approach to API security allows MSPs to create robust, secure APIs with less code and fewer potential security vulnerabilities.