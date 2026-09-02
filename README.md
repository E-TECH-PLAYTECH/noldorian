# Noldorian

Noldorian lets agents discover and invoke approved credential capabilities
without giving them a secret-value API.

The public `noldorian` package is a zero-dependency client, CLI, and MCP server
for the local root-owned capability broker. The broker exposes public metadata
and a closed set of typed operations; credential values, custody paths,
arbitrary commands, and raw HTTP requests stay outside the agent surface.

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
noldorian describe openai.tunnel.admin
noldorian invoke openai.tunnel.admin tunnels.list \
  --arguments-json '{"organization_ids":["org_example"]}'
```

The client does not provide registration, enrollment, import, export,
clipboard, shell, or secret-retrieval commands.

## MCP

Run the bundled stdio MCP server:

```bash
noldorian-mcp
# equivalent: python3 -m noldorian.mcp
```

It exposes four tools:

- `broker_status`
- `list_credential_capabilities`
- `describe_credential_capability`
- `invoke_credential_capability`

## Broker installation

The root-owned broker and human enrollment ceremony currently live in the
`keyabra` package in this repository. See the
[secure capability broker design](https://github.com/E-TECH-PLAYTECH/noldorian/blob/main/SECURE_CAPABILITY_BROKER.md)
for installation, the trust boundary, and the adapter contract.

Publishing the implementation does not publish or weaken the live broker
state. Credentials, capability grants, account identifiers, and authorized
machine identities are local configuration and must never be committed or
included in distributions.

## Noldorian family

This repository also contains the operator-focused tools that originated the
Noldorian tier:

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
