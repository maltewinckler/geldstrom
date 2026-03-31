## Description

<!-- Briefly describe the changes in this PR -->

## Type of Change

<!-- Mark the appropriate option with an 'x' -->

- [ ] `[Feat]` — New feature
- [ ] `[Fix]` — Bug fix
- [ ] `[Refactor]` — Code refactoring (no functional change)
- [ ] `[Docs]` — Documentation update
- [ ] `[Test]` — Test additions or updates
- [ ] `[Chore]` — Maintenance (dependencies, CI, configs)
- [ ] `[Security]` — Security fix or hardening

## Checklist

- [ ] PR title follows the format: `[Type] Short description`
- [ ] Lint passes (`uv run ruff check packages/ apps/ tests/`)
- [ ] Tests pass locally (`uv run pytest tests/packages/geldstrom/unit/ tests/apps/ --ignore=tests/apps/gateway/infrastructure/`)
- [ ] If `packages/geldstrom` changed: version bumped in `packages/geldstrom/pyproject.toml`

## Related Issues

<!-- Link any related issues: Fixes #123, Relates to #456 -->
