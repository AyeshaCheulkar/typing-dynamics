# Repository Guidelines

## Project Structure & Module Organization

Keep production code, tests, documentation, and static resources in clearly named top-level directories when they are introduced (for example, `src/`, `tests/`, `docs/`, and `assets/`). Keep each feature's implementation and supporting files close together. Avoid placing generated files, local environments, or editor metadata in version control. Update this guide when the project adopts a concrete framework or directory convention.

## Build, Test, and Development Commands

This repository does not currently expose a committed build script, package manifest, or test runner. Before adding one, document the required setup and canonical commands in the project README. Prefer a small, repeatable command set, such as:

```powershell
# Install dependencies
npm install
# Run the automated checks
npm test
# Start local development
npm run dev
```

Use only commands backed by committed configuration; do not require contributors to rely on untracked local setup.

## Coding Style & Naming Conventions

Follow the conventions established by the files you edit. Use consistent indentation within each language (two spaces for JSON, unless its surrounding file differs), meaningful names, and one responsibility per module. Name directories and non-class files in lowercase kebab-case (for example, `data-cleaning/` and `survey-form.md`); use the language's standard class/type casing where applicable. Add an automated formatter or linter with its configuration before enforcing style mechanically.

## Testing Guidelines

Add tests with every behavior change once a test framework is selected. Place tests in `tests/` or next to the code according to the chosen tool's convention, and use descriptive names such as `calculates_total_for_empty_cart`. Cover normal behavior, boundary cases, and bug fixes. Run the project's documented test command before opening a review.

## Commit & Pull Request Guidelines

No Git history is available in the current checkout, so no repository-specific commit convention can be inferred yet. Use short, imperative commit subjects, such as `Add survey validation`, and keep commits focused. Pull requests should explain the change, identify testing performed, link related issues when available, and include screenshots or sample output for user-facing changes. Do not commit credentials, personal data, or machine-specific configuration.
