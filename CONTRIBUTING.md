# Contributing

Run the public-package tests:

```bash
python3 -m unittest discover -s tests -v
```

Factory publish is not GitHub. Build locally, store the wheel and sdist on
Google Drive, then `twine upload` to PyPI. GitHub Releases must not upload.

Do not include credential values, account-specific policy, custody paths,
machine authorization lists, or customer configuration in issues, fixtures,
commits, or build artifacts. Report vulnerabilities privately as described in
`SECURITY.md`.
