# CodeGraph Production Runtime

## Execution Backends

1. **LocalExecutionBackend**: Synchronous execution engine for local CLI commands and single-user development.
2. **WorkerExecutionBackend**: Distributed asynchronous worker backend submitting jobs to Redis job queue.
