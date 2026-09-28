# Web UI

- `apps/web` is the post-MVP Next.js UI; the two-day MVP is backend-first with Swagger, CLI, JSON reports and synthetic notice fixtures.
- Start UI work after the backend-first MVP gate. Use generated TypeScript SDK/types; do not duplicate verification rules or call OpenAI directly.
- Display Verification Status and Lifecycle Status separately. `NOT_REGISTERED` must not be presented as fake; keep legal/security claims measured.
- Cover loading, empty, partial and error states; preserve mobile/desktop accessibility.