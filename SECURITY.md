# Security policy

Noldorian is designed so agent-facing clients can discover and invoke approved
credential capabilities without retrieving credential values.

Please report suspected vulnerabilities privately through GitHub's **Report a
vulnerability** flow for `E-TECH-PLAYTECH/noldorian`. Do not open a public issue
that contains credentials, custody paths, authentication headers, private
account identifiers, or exploit details for an unpatched vulnerability.

The broker does not defend against a compromised root account or modified
operating system. Legacy same-user dotenv vaults and arbitrary command runners
are operator compatibility surfaces, not agent isolation boundaries.
