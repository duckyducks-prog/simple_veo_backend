# Logging Implementation

## Overview
A centralized logging system has been implemented across the codebase to replace print statements and provide better observability.

## Logging Module
**Location**: [app/logging_config.py](app/logging_config.py)

The `setup_logger()` function provides:
- Consistent log formatting with timestamps
- Function name and line number tracking
- Configurable log levels
- Proper handler management (prevents duplicate handlers)

## Log Format
```
[YYYY-MM-DD HH:MM:SS] LEVEL [module.function:line] message
```

Example:
```
[2025-12-14 13:14:55] INFO [auth.verify_firebase_token:48] User authenticated successfully: user@example.com
```

## Log Levels Used

### INFO
- Application startup
- Successful user authentication
- API endpoint requests (generation, library operations)
- Successful asset saves/deletions
- Firebase initialization

### WARNING
- Failed authentication attempts (missing token, non-whitelisted users)
- Invalid requests (400 errors)
- Asset not found errors
- Permission denied errors

### ERROR
- API failures (500 errors)
- Firebase errors
- Asset save/delete failures
- Token verification failures

### DEBUG
- Video status checks (frequent polling operations)

## Implementation Locations

### Core Modules
- **[app/main.py](app/main.py)**: Application startup logging
- **[app/auth.py](app/auth.py)**: Authentication and authorization logging
- **[app/logging_config.py](app/logging_config.py)**: Logging configuration

### Services
- **[app/services/generation.py](app/services/generation.py)**: Image/video generation and library save operations
- **[app/services/library.py](app/services/library.py)**: Asset management operations

### Routers
- **[app/routers/generation.py](app/routers/generation.py)**: Generation endpoint logging
- **[app/routers/library.py](app/routers/library.py)**: Library endpoint logging

### Scripts
- **[scripts/get_test_token.py](scripts/get_test_token.py)**: Token generation script (errors only)

## Usage

### Import and Setup
```python
from app.logging_config import setup_logger

logger = setup_logger(__name__)
```

### Log Messages
```python
# Informational
logger.info(f"Processing request for user {user_email}")

# Warnings
logger.warning(f"Invalid request: {error_message}")

# Errors
logger.error(f"Operation failed: {str(exception)}")

# Debug
logger.debug(f"Status check: {operation_name}")
```

## Benefits

1. **Structured Logging**: Consistent format makes logs easier to parse and analyze
2. **Contextual Information**: Automatic inclusion of module, function, and line numbers
3. **Traceability**: User emails and operation IDs included for debugging
4. **Production Ready**: Easy to integrate with log aggregation services (CloudWatch, Stackdriver, etc.)
5. **Performance Monitoring**: Track request patterns and identify bottlenecks
6. **Security Auditing**: Track authentication attempts and access patterns

## Future Enhancements

Consider adding:
- Request ID tracking for distributed tracing
- JSON formatted logs for better machine parsing
- Different log levels for dev/staging/production
- Integration with cloud logging services (Google Cloud Logging)
- Request/response time tracking
- Metrics collection alongside logs
