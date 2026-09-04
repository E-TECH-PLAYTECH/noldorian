# Optional Gondolin extension (capability broker client)

Public Noldorian ships a **client** for an optional local Unix-socket
extension. The server, privileged custody, native helper, and installer are
**not** part of this package.

Everyday use is the 0600 vault (`xabra run --env-file`). Missing the socket is
not a failure (`noldorian doctor` reports `extension.status = absent`).

## Socket

Default path: `/var/run/noldorian-key-broker.sock`

Override: environment variable `NOLDORIAN_BROKER_SOCKET`.

## Public actions only

The client (`noldorian.client.BrokerClient`) sends JSON lines and accepts only:

- `status`
- `list`
- `list_enrollment_templates`
- `describe`
- `invoke`
- `request_enrollment`
- `enrollment_status`

It refuses `enroll`, `register`, `import_env`, `get_secret`, `shell`, and
`owner_prompt`. `request_enrollment` accepts policy metadata (template,
purpose, operations, resources) and never a credential value.

## Schemas

- `noldorian.key-capabilities/v1`
- `noldorian.enrollment-request/v1`
- `noldorian.enrollment-templates/v1`

A later Noldorian release may add fields. It must not invalidate
`xabra run --env-file` / paste-once child env.
