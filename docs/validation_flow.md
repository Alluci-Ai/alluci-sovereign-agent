# Validation Flow Overview

```mermaid
flowchart TD
    A[Incoming RPC Request] --> B{Validate JSON-RPC schema}
    B -->|Valid| C[Dispatch to registered method]
    B -->|Invalid| D[_rpc_error] --> E[Return error to client]
    C -->|Method raises Exception| F[_rpc_error (internal)] --> E
    C -->|Success| G[_rpc_success] --> H[Return result]
    style A fill:#2a9d8f,color:#fff
    style B fill:#e9c46a,color:#000
    style D fill:#e76f51,color:#fff
    style F fill:#e76f51,color:#fff
    style G fill:#2a9d8f,color:#fff
```

The flow respects the `settings.DEBUG` flag: when disabled, the `data` field is omitted from error objects.
