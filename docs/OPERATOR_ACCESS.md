# Named operator access

Bootstrap once on the collector host, with a private password prompt:

```powershell
.venv\Scripts\python.exe -m governloom.cli bootstrap-admin alice
$env:GOVERNLOOM_AUTH_MODE = "operators"
.venv\Scripts\python.exe -m uvicorn governloom.api:app --host 127.0.0.1 --port 8000
```

Pass `--db sqlite:///path/to/collector.db` before the command for another database.
`--password-stdin` supports automation without a password in command arguments.
There is no default password. Bootstrap refuses an existing account database.
Once accounts exist the collector defaults to operator mode and refuses explicit
unauthenticated local mode. The legacy shared admin token cannot bypass this mode.
Databases without accounts retain the explicitly local development workflow.

Sign in on the dashboard. Administrators use **Operator accounts** to create users,
assign applications and revoke access. Everyone can change their own password;
this invalidates all their sessions. Tokens stay in page memory: reloading signs
out. API clients use `POST /api/auth/login` and the returned Bearer token.

| Role | Access |
| --- | --- |
| Viewer | Read/export assigned applications and evidence |
| Reviewer | Viewer access plus case/incident/alert review and action verification |
| Operator | Reviewer access plus policies, ingestion keys, imports and evaluations for assigned applications |
| Admin | All applications, application creation, account management and local escalation dispatch |

The API enforces permissions and filters application/run lists. Object routes,
comparisons and exports check scope too. The server substitutes the authenticated
username into actor fields and records successful administrative POSTs. Older
fixture/import provenance fields may still identify a scripted producer; the
operator request audit identifies who authorized that operation. A user-entered
owner remains an assignment, not proof that the named person acted.

Passwords require 15–1,024 characters, have unique 128-bit salts and use
PBKDF2-HMAC-SHA256 with 600,000 iterations. This dependency-free implementation
uses the OWASP-documented PBKDF2 work factor; it makes no FIPS certification claim.
Sessions have 256-bit random secrets, stored only as SHA-256 digests, an eight-hour
absolute expiry and at most 20 live sessions per account. Revocation/password
change takes effect on the next request. Failed and successful logins share a
persisted limit of ten attempts/minute per direct client IP; do not trust forwarded
headers. Use edge rate limits when exposing the private collector through a proxy.
Audit/session backups contain hashes and account identifiers: restrict OS access.

Use the existing TLS hosting guide for remote access; never send passwords or
session tokens over public HTTP. This release has local named accounts, not SSO,
MFA or a self-service password recovery service. Keep a second administrator for
recovery; the last active administrator cannot be revoked.

References checked 2026-10-08: [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
and [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
