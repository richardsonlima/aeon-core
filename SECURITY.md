# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.5.x | yes |
| earlier | no |

## Reporting a vulnerability

Report privately through GitHub security advisories:
<https://github.com/richardsonlima/aeon-core/security/advisories/new>

Do not open a public issue for a vulnerability. Include the version, a minimal reproduction and the impact you see. I aim to acknowledge a report within 7 days.

## Scope

In scope: the `aeon` package and CLI, the local runtime (`aeon runtime start`), the audit log and its verifier, the published container image build.

Out of scope: vulnerabilities in third-party agents, models or tools that sit behind the gate, and deployments that bind the runtime to a non-loopback address without a token and network controls.

## What Æon does not protect against

Æon gates the actions that go through it. It does not protect against actions that bypass the gate, a compromised host, or an attacker who can write the audit log and its anchor. Read the details before relying on it:

- [docs/security.md](docs/security.md)
- [docs/known-limits.md](docs/known-limits.md)
