# packages/domain-types

TypeScript interfaces mirroring the Python Pydantic models in `apps/api`.
Both `apps/web` and `apps/mobile` import from `@agentic-control-plane/domain-types`.

## Usage

```typescript
import type { MyType } from '@agentic-control-plane/domain-types'
```

## Sync rule

**Source of truth:** Python Pydantic models in `apps/api/app/features/*/models.py`.
**Mirror:** TypeScript interfaces here.

When Python models change, update this package.
