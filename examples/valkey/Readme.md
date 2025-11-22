# Valkey Backend Example

This example demonstrates using FastAPI-Cache with Valkey as the backend.

## Prerequisites

1. Install Valkey:
   ```bash
   # Using Docker
   docker run -d -p 6379:6379 valkey/valkey:latest
   
   # Or install locally
   # See: https://valkey.io/download/
   ```

2. Install dependencies:
   ```bash
   poetry install
   # or
   pip install fastapi-cache2[valkey]
   ```

## Running the Example

```bash
cd examples/valkey
fastapi dev main.py
```

## Endpoints

- `GET /` - Cached endpoint (10s TTL)
- `GET /clear` - Clear cache
- `GET /date` - Get cached date
- `GET /datetime` - Get cached datetime
- `GET /blocking` - Sync cached endpoint
- `GET /html` - Cached HTML response
- `GET /cache_response_obj` - Cached JSON response

## Configuration

The example uses these Valkey settings:
- Host: localhost
- Port: 6379
- DB: 0
- decode_responses: False (required for pickle coder)
```