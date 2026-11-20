## Summary

Describe the changes made in this pull request and why they are needed.

## Verification Checklist

- [ ] `uv run ruff format --check .` passes
- [ ] `uv run ruff check .` passes
- [ ] `uv run pyrefly check` passes with 0 errors
- [ ] `uv run pytest -v` passes all unit, service, and UI tests
- [ ] No runtime dependencies added to `[project].dependencies` and no secrets written to disk
