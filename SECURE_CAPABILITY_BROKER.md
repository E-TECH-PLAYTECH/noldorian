# Noldorian credential capability broker

## Purpose

Agents need to know which authenticated operations are available without being
able to retrieve, print, transform, copy, or choose an arbitrary process that
receives the credential. Legacy Keyabra env-vaults solve human paste and
shell-history problems, but they are not an agent isolation boundary: an agent
running as the same Unix user can read a `0600` file, and an arbitrary
`keyabra run` command can deliberately encode or transmit its environment.

The capability broker adds that missing boundary.

```text
owner hidden prompt / owner import
                │
                ▼
   root-owned broker + secret custody
                │
     ┌──────────┴──────────┐
     ▼                     ▼
public capability      fixed adapter
metadata               (typed arguments)
     │                     │
     └──────────┬──────────┘
                ▼
      sanitized receipt / MCP result
```

There is intentionally no secret export, clipboard, arbitrary shell, or raw
HTTP operation in the broker or its MCP server.

## Trust boundary

Production installation runs as a root LaunchDaemon. Its application and
state are root-owned under:

`/Library/Application Support/NoldorianKeyBroker`

Secret custody files and the capability catalog are mode `0600` below a mode
`0700` state directory. Authorized desktop agents communicate through
`/var/run/noldorian-key-broker.sock`. The daemon verifies the Unix peer UID;
request-supplied identity is ignored.

Normal authorized UIDs may only:

- check service status;
- list public capability metadata;
- describe one capability; and
- invoke an operation already compiled into an adapter and allowed by the
  owner-controlled catalog.

Only UID 0 may register a capability, enroll a credential, or import one entry
from a legacy Keyabra env-vault. An agent cannot gain owner access without an
operator satisfying the operating system's administrator gate.

The broker cannot protect against a compromised root account or a modified
operating system. Legacy dotenv vaults remain outside this guarantee until
their entries are imported and the plaintext copies are retired by the owner.

## Capability contract

Public metadata contains:

- a stable capability ID;
- provider and human description;
- approved operation names;
- resource scope such as organization/workspace IDs; and
- `available: true|false`.

It never contains credential values or fragments, custody paths, token length,
fingerprints, hashes, or arbitrary executable commands.

The catalog accepts only whitelisted fields and adapters. The initial adapter
is `openai_tunnel_admin`, with these operations:

- `tunnels.list`
- `tunnels.get`
- `tunnels.create`

Arguments are validated and translated to the native `tunnel-client admin
tunnels` command tree without a shell. The key exists only in the child
environment. Results are parsed as JSON and recursively redact sensitive
field names plus direct, URL-encoded, base64, URL-safe-base64, and hexadecimal
secret representations.

## Install on macOS

From the Noldorian checkout:

```bash
sudo keyabra/scripts/install_broker_macos.sh --user "$USER"
```

The installer creates a root-owned zipapp, trusted copy of the provider
client, LaunchDaemon, state directory, and Unix socket. It does not register a
capability or enroll a key unless an owner supplies `--capability SPEC.json`.

## Owner enrollment

To register or update another non-secret policy:

```bash
cp keyabra/examples/openai-tunnel-admin.capability.json /tmp/tunnel-policy.json
# Edit the copied public placeholders, then:
sudo keyabra broker register /tmp/tunnel-policy.json
```

If the credential already exists in a legacy vault, import it by reference;
the agent and client never receive its value:

```bash
sudo keyabra broker import-env \
  openai.tunnel.admin \
  /absolute/path/to/keyabra.env \
  OPENAI_ADMIN_KEY
```

For a new credential, enroll through Keyabra's confirmed hidden prompt:

```bash
sudo keyabra broker enroll openai.tunnel.admin
```

After live provider validation, the owner should retire the legacy plaintext
entry through a separate reviewed migration. Enrollment never silently
deletes the source.

## Agent use

```bash
keyabra broker status
keyabra broker list
keyabra broker describe openai.tunnel.admin
keyabra broker invoke openai.tunnel.admin tunnels.list \
  --arguments-json '{"organization_ids":["org_example"]}'
```

MCP server:

```bash
python3 mcp/noldorian_capabilities_mcp.py
```

The MCP tools are `broker_status`, `list_credential_capabilities`,
`describe_credential_capability`, and `invoke_credential_capability`. No owner
or secret-value tool is exposed over MCP.

## Adding a provider

Provider support is code, not catalog data. A new adapter must define a closed
operation set, validate every argument before resolving the secret, avoid
shells and caller-supplied executables, validate provider identity and scope,
structurally parse provider output, redact sensitive fields and common secret
encodings, and include tests proving credentials never appear in results,
errors, commands, or receipts.
