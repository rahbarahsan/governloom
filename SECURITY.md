# Security reporting

Use the repository's **Security → Report a vulnerability** private channel when
available. Otherwise open a public issue containing only a request for a private
security contact; wait for a private channel before disclosing details. Never
publish exploit details, passwords, ingestion/signing keys, subscription auth
files, private prompts or customer records.

Private reports should describe affected version, reproduction, prerequisites,
impact and a sanitized proof. Maintainers assess reports and coordinate fixes;
there is no guaranteed response-time SLA. Fixes target current 0.6.x; older
installations should upgrade and have no promised backport SLA.

GovernLoom supports controlled self-hosted integrations. It has named application
roles, but no tenant isolation, SSO/MFA or compliance certification. Remote use
needs TLS, named accounts, host/origin restrictions and OS access controls; see
[access](docs/OPERATOR_ACCESS.md) and [operations](docs/PILOT_OPERATIONS.md).

Protect SQLite and the separate signing-secret directory. Unix secret creation
uses owner-only mode; Windows requires explicit NTFS permissions. Full restore
requires both database and signing secrets; [recovery bundles](docs/RECOVERY.md)
contain credentials and must remain private. [Signing rotation](docs/WEBHOOKS.md)
supports bounded overlap or immediate revocation for future dispatches.
Webhook URLs are host-allowlisted;
validated HTTPS addresses and disabled redirects complement network egress rules.

Collector text/grounding passages are transient; selected metadata and evidence
hashes persist. Application logs/upstream model captures have separate retention
rules. Detectors may miss risks or flag benign cases; a clear check cannot establish
that a system/output is safe.

Discovery evidence differs from runtime text: selected source files and bounded
scalar/ID telemetry columns are retained for review. Review private bundles before
import; best-effort credential filters cannot establish absence of sensitive data.
Optional semantic analysis transmits selected source excerpts only when explicitly
enabled locally. The explorer does not execute target code or fetch remote files.
See [discovery access and bounds](docs/DISCOVERY.md).
