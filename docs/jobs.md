# Asynchronous Job System

## Job Lifecycle

```text
PENDING ──► RUNNING ──► SUCCEEDED
               │
               ▼ (on failure, retries < max_retries)
            PENDING ──► FAILED
```

- Infrastructure controls retries, timeouts, and cancellations. LLMs cannot override job lifecycle states.
