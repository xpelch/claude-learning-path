---
name: commit-writer
description: Writes conventional commit messages from the staged diff. Use when the user asks to write, draft or improve a commit message.
---

1. Run `git diff --staged`.
2. Write a subject line under 72 characters in the form `type(scope): summary`.
3. Add a short body explaining why the change was made.
