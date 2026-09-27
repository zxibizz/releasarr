# Security Policy

## Supported versions

Releasarr is pre-1.0. Only the latest released tag receives fixes.

| Version | Supported |
| --- | --- |
| latest release | yes |
| anything older | no |

## Reporting a vulnerability

Please report privately via GitHub's
[private vulnerability reporting](https://github.com/zxibizz/releasarr/security/advisories/new)
rather than opening a public issue.

Include what you did, what happened, and the version from `GET /api/v1/system/status`. A
proof of concept helps but is not required. Expect an acknowledgement within a
week.

## Threat model

Releasarr is designed to run on a private network next to Sonarr, Radarr,
Prowlarr and qBittorrent, and holds the API keys and password for all four. Its
security properties are sized for that:

- **Do not port-forward it.** Accounts, roles, per-user request scopes and a
  login lockout are there to keep household members out of each other's way,
  not to stand up to the open internet. For remote access, put it behind a VPN
  or a TLS reverse proxy — which is also what the installable app needs.
- **A fresh instance's setup page is open** until the first admin account is
  created. Create it before the port is reachable by anyone else.
- **The service key is an admin credential.** Anything holding it can queue
  tasks on the instance's behalf. Treat it like the \*arr API keys it sits next
  to, and regenerate it from **Users** if it leaks.
- **`RELEASARR_AUTH_SECRET` signs every access token.** Anyone who has it can
  mint a token for any user. The container generates one into
  `/config/auth-secret` when none is set; keep that file out of backups you
  share.
- **The refresh cookie is not `Secure` by default**, because most instances are
  reached over plain HTTP on a LAN and a `Secure` cookie would never be sent
  back. Behind TLS, set `RELEASARR_AUTH_COOKIE_SECURE=true`.

Things that are in scope and that we do want to hear about:

- Bypassing authentication, a role or a permission check, or reading or
  changing a request outside the caller's request scope.
- Leaking a stored integration credential, the service key, a token or a
  password hash via an endpoint, a log line or an error message.
- Refresh-token replay that survives rotation, or cross-site request forgery
  against the UI.
- Anything that lets an unauthenticated caller queue work for the scheduler.

Out of scope:

- Exposing Releasarr to the internet without a proxy, and being reached.
- Denial of service from an authenticated caller.
- Vulnerabilities in Sonarr, Radarr, Prowlarr, qBittorrent or the indexers
  themselves.
