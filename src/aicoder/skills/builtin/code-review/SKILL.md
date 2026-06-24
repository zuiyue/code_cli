---
name: code-review
description: Code review checklist for identifying bugs, anti-patterns, security issues, and code quality problems.
---

# Code Review

## When to Use
- Reviewing code changes before merging
- Self-reviewing own code

## Checklist
- [ ] Follows existing conventions?
- [ ] Edge cases handled?
- [ ] Error handling appropriate?
- [ ] Security concerns?
- [ ] Code testable?
- [ ] Names clear and descriptive?

## Common Issues
- Exception swallowing (bare `except:`)
- Hardcoded secrets
- Missing input validation
- Race conditions
- SQL injection via string formatting

## What NOT to Flag
- Minor style preferences
- "I would have written it differently" without concrete issue
