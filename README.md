# Noldorian

Noldorian lets agents request human-approved credential access, discover the
resulting named capabilities, and invoke approved operations without giving
them a secret-value API.

The public `noldorian` package is a zero-dependency client, unified CLI, and MCP
server for the local root-owned capability broker. It also bundles the
operator family (`keyabra`, `xadabra`, `xabra`, `binabra`, and `xalakazam`) so
there is one install and one source of truth. The broker exposes public
metadata and a closed set of typed operations; credential values, custody
paths, arbitrary commands, and raw HTTP requests stay outside the agent
surface.

## Install

```bash
python3 -m pip install noldorian
# or
uv tool install noldorian
```

## Query capabilities

```bash
noldorian status
noldorian list
noldorian templates
noldorian describe openai.tunnel.admin
noldorian request-enrollment openai.tunnel.admin \
  --purpose "OpenAI Secure MCP Tunnel administration for Studio Bridge"
noldorian invoke openai.tunnel.admin tunnels.list \
  --arguments-json '{"organization_ids":["org_example"]}'
```

`request-enrollment` is the agent-safe enrollment boundary. It submits only a
reviewed template plus human-readable purpose and scope. The broker opens the
owner-only hidden prompt, stores the credential in root custody, and returns a
request ID/status. The agent can poll `enrollment-status`; it never receives
the entered value. Direct catalog registration, legacy import, export,
clipboard, shell, and secret-retrieval commands remain owner-only or absent
from the agent surface.

## MCP

Run the bundled stdio MCP server:

```bash
noldorian-mcp
# equivalent: python3 -m noldorian.mcp
```

It exposes seven tools:

- `broker_status`
- `list_credential_capabilities`
- `list_credential_enrollment_templates`
- `describe_credential_capability`
- `invoke_credential_capability`
- `request_credential_enrollment`
- `get_credential_enrollment_status`

## Broker installation

The root-owned broker and human enrollment ceremony are bundled into the
unified distribution (the `keyabra` namespace remains a compatibility surface).
See the
[secure capability broker design](https://github.com/E-TECH-PLAYTECH/noldorian/blob/main/SECURE_CAPABILITY_BROKER.md)
for installation, the trust boundary, and the adapter contract.

Publishing the implementation does not publish or weaken the live broker
state. Credentials, capability grants, account identifiers, and authorized
machine identities are local configuration and must never be committed or
included in distributions.

## Noldorian family

The same `noldorian` distribution installs the operator-focused tools that
originated the Noldorian tier:

| Package | CLI | Purpose |
|---|---|---|
| `keyabra` | `keyabra` | Human secret enrollment and root broker service |
| `xadabra` | `xadabra` | Interactive placeholder runner |
| `binabra` | `abra` | Portable bin-directory anchor |
| `xabra` | `xabra` | Verified direct-distribution app installer |
| `xalakazam` | `xalakazam` | Operator orientation and checkpoints |

## Security and license

Please use GitHub's private vulnerability-reporting flow; see the
[security policy](https://github.com/E-TECH-PLAYTECH/noldorian/blob/main/SECURITY.md).
Noldorian is licensed under the
[Apache License 2.0](https://github.com/E-TECH-PLAYTECH/noldorian/blob/main/LICENSE).
