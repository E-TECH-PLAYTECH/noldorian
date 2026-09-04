# Security policy

Noldorian is designed so agent-facing clients can discover how to run
owner-gated credential use without retrieving credential values.

Report suspected vulnerabilities privately to the maintainers. Do not open a
public issue that contains credentials, custody paths, authentication headers,
private account identifiers, or exploit details for an unpatched vulnerability.

Same-user dotenv vaults are an operator paste-once surface, not isolation
against a process running as the same Unix user. An optional Gondolin
extension may add a privilege-separated broker; it is not required to install
or use Noldorian.
