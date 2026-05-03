# Contributing to Alluci Sovereign Agent

First off, thank you for considering contributing to Alluci! It's people like you that make Alluci such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report for Alluci. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for Alluci, including completely new features and minor improvements to existing functionality.

### Your First Code Contribution

Unsure where to begin contributing to Alluci? You can start by looking through these `beginner` and `help-wanted` issues.

## Styleguides

### Git Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

### JavaScript / TypeScript Styleguide

* Use TypeScript for all new code.
* Follow the existing linting rules.
* Ensure all sensitive operations use the `SovereignSecurityManager`.

### Python Styleguide

* Use Python 3.12+.
* Use `Ruff` for linting and formatting.
* Ensure all API calls are proxied through `router.py`.

### Third-Party Subtree Management

* Changes to `third-party/*` subtrees are discouraged.
* Any changes to vendored code must include a `PROVENANCE.md` file explaining the rationale, version drift, and security impact.
* Pull Requests modifying `third-party/` must be labeled with `third-party-review` and require explicit sign-off from a security maintainer.

## Production Readiness

Every Pull Request must pass the automated quality gates:
1. `make quality` must return a PASS.
2. A `Release Readiness Report` must be attached to the PR.
3. No placeholder digests (`PIN_THIS_DIGEST`) are allowed in deployment manifests.

## Security

Please report security vulnerabilities for the Alluci project responsibly. Do not open public issues for security vulnerabilities.
