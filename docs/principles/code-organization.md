# Code Organization Principles in Clarity

## File Size Guidelines

One of Clarity's core principles is maintainable code through appropriate sizing and organization. The language encourages:

### 1. Size Limits

Clarity recommends keeping source files between 200-300 lines of code. This principle is built into the language's design in several ways:

```clarity
// The compiler will warn when files exceed 300 lines
@file(warnLimit=300, errorLimit=500)
module UserService {
    // Implementation
}
```

### 2. Automatic Refactoring Suggestions

When files grow too large, Clarity's IDE integration can suggest logical ways to split the file:

```clarity
// IDE will suggest: "Extract AuthenticationMethods to a separate module"
module UserService {
    // 100 lines of user management code...
    
    // 100 lines of authentication code that could be separated...
    
    // 150 lines of permission checking code that could be separated...
}
```

### 3. Module Composition

Clarity makes it easy to split code into smaller files and compose them together:

```clarity
// UserService.clarity
module UserService {
    include UserCore
    include UserAuthentication
    include UserPermissions
    
    // Only the unique UserService code remains here
    // (now only ~50 lines instead of 350)
}
```

### 4. Smart Imports

Clarity's import system makes working with multiple small files convenient:

```clarity
// Import everything from the user domain
import user.*

// This gives you access to:
// - user.Service
// - user.Authentication
// - user.Permissions
// Without cluttering your namespace or requiring separate imports
```

## Automatic Code Quality Metrics

Clarity includes built-in code quality metrics that help maintain appropriate file sizes:

```clarity
// Run metrics on your codebase
clarity metrics ./src

// Output:
// Files exceeding guidelines (300 lines):
// - UserService.clarity (352 lines) - Extract candidate: AuthenticationMethods
// - DatabaseManager.clarity (412 lines) - Extract candidate: ConnectionPool
// 
// Overall codebase health: 87/100
// - Average file size: 142 lines
// - Average function size: 12 lines
// - Code duplication: 4%
```

## Benefits of Smaller Files

- **Improved readability**: Smaller files are easier to understand in their entirety
- **Better collaboration**: Smaller files reduce merge conflicts in team environments
- **Focused responsibility**: Each file has a clearer, more specific purpose
- **Enhanced testability**: Smaller modules are easier to test in isolation
- **Faster compilation**: The compiler can process smaller files more efficiently

## Domain-Driven Structure

Clarity encourages organizing code not just by technical function but by domain concepts:

```clarity
// Instead of:
/src
  /models
    User.clarity
    Product.clarity
    Order.clarity
  /controllers
    UserController.clarity
    ProductController.clarity
    OrderController.clarity
  /services
    UserService.clarity
    ProductService.clarity
    OrderService.clarity

// Clarity encourages:
/src
  /user
    Model.clarity       // ~100 lines
    Service.clarity     // ~200 lines
    Controller.clarity  // ~150 lines
    Types.clarity       // ~50 lines
  /product
    Model.clarity       // ~120 lines
    Service.clarity     // ~180 lines
    Controller.clarity  // ~140 lines
  /order
    Model.clarity       // ~200 lines
    Service.clarity     // ~250 lines
    Controller.clarity  // ~160 lines
```

This domain-driven organization keeps related code together while still maintaining appropriate file sizes.