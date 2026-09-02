# Contributing

Contributions are welcome through GitHub pull requests.

Before opening a pull request, run the public-package and family tests shown in
`.github/workflows/test.yml`. New credential providers must expose a closed
operation set, validate all arguments before resolving a credential, avoid
shells and caller-selected executables, structurally parse provider output,
and include non-disclosure tests.

Do not include credential values, account-specific policy, custody paths,
machine authorization lists, or customer configuration in issues, fixtures,
commits, or build artifacts. Report vulnerabilities privately as described in
`SECURITY.md`.
