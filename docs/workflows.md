# Human Approval Workflow State Engine

## State Transitions & Approval Gates

```text
ANALYZE
  │
  ▼
INVESTIGATE
  │
  ▼
PLAN
  │
  ▼
AWAITING_APPROVAL ──(Human Approval Gate 1)──► PATCH
                                                 │
                                                 ▼
                                                TEST
                                                 │
                                                 ▼
COMMIT ◄──(Human Approval Gate 2)── AWAITING_GIT_APPROVAL
  │
  ▼
  PR
  │
  ▼
  CI ──► REVIEW ──► COMPLETED / FAILED
```
