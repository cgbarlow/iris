# SPEC-258-A: Full Screen Carries Over When Following a Link to Another View

Implements **[ADR-258](../ADR-258-Full-Screen-Follows-View-Links.md)**.

## 1. Changes

| File | Change |
|------|--------|
| `frontend/src/lib/utils/focusCarryOver.ts` | `focusCarryOverTarget(focusMode, from, to, type)` returns the path to go to with `focus=1` added, or `null`. It returns `null` when: focus mode is off, there is no target, the type isn't `link`/`goto`, the target is on another origin, the target isn't `/views/<id>`, the target is the same view, or the target already has `focus=1`. Other query parameters and the hash are kept. |
| `frontend/src/routes/views/[id]/+page.svelte` | A `beforeNavigate` hook, registered before the lock-release hook, calls the helper. When it gets a path back, it runs `nav.cancel()` then `goto(path)`. |

## 2. Tests (TDD)

- `frontend/tests/unit/focusCarryOver.test.ts`: 7 cases covering the rules
  above.
- Checked in a real browser with Playwright against the dev app:
  - Clicking a linked nav-cell in full screen goes to `/views/<other>?focus=1`
    with FocusView shown. Without the fix, the same click lost `focus=1`.
  - Clicking an `<a href="/views/<other>">` inside FocusView also keeps full
    screen.
  - Back returns to the previous view, still with `?focus=1`.
- Frontend vitest: 1331 passed.

## 3. Acceptance criteria

- From full screen, any link or linked node to another diagram opens that
  diagram in full screen.
