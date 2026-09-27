# Troubleshooting

Start with the logs: **System → Logs** in the UI, or `docker logs releasarr`, where every line is
tagged `[api]`, `[scheduler]` or `[nginx]`. `docker inspect --format '{{.State.Health.Status}}'
releasarr` shows whether the healthcheck passes.

## The container keeps restarting

- **A migration failed.** The container stops on purpose rather than serve against a
  half-migrated database. The error is near the top of `docker logs releasarr`.
- **`Permission denied` under `/config`.** Everything there belongs to `PUID`:`PGID`. If you
  changed them, or copied files in as root, `chown -R <PUID>:<PGID>` the host directory.
- **`RELEASARR_MODE must be one of all, web, worker`.** A typo in the mode.

## Signing in does not stick

Signing in works, but the next page load is back at the login screen:

- **Plain HTTP with `RELEASARR_AUTH_COOKIE_SECURE=true`.** The browser drops a `Secure` cookie
  on `http://`, so the session is never kept. Unset it, or put TLS in front.
- **A reverse proxy on a path without a URL base.** The session cookie is scoped to
  `<url base>/api/v1/auth`. Serving Releasarr at `/releasarr/` needs **Settings → General → URL
  base** (or `RELEASARR_URL_BASE`) set to `/releasarr` and a container restart, and the proxy
  must pass the path through unchanged rather than strip it.

## The setup screen appears again

The database is gone, which almost always means `/config` is not mounted: every recreate starts
from an empty instance. Check the volume in your compose file.

## Account locked

Ten failed sign-ins lock an account for fifteen minutes
(`RELEASARR_AUTH_MAX_FAILED_LOGINS`, `RELEASARR_AUTH_LOCKOUT_SECONDS`). Wait it out; the next
successful sign-in clears the counter.

## Searching or grabbing says the integration is not configured

Fill it in under **Settings → External services**. Each URL is the address the app's own UI
opens on, URL base included — `http://sonarr:8989`, or `https://example.com/sonarr` behind a
proxy — and Releasarr adds the API path itself. The connection test
next to each one checks it without saving. A field marked *Set by environment* comes from a
`RELEASARR_*` variable and can only be changed there.

`localhost` inside the container is the container itself, not the machine it runs on. Use the
host name or IP where each service listens: `http://192.168.1.10:8989`.

## A finished download never imports

The release is marked completed but Sonarr or Radarr reports that the path does not exist.
Releasarr hands over the path qBittorrent reports, unchanged, so it has to exist at that same
path wherever Sonarr and Radarr run. If qBittorrent saves to `/downloads/…` but Sonarr
sees the same directory as `/data/downloads/…`, the import fails. Make the download directory
appear at the same path to qBittorrent and to the \*arr apps — the same mount point, or a
matching path on each host.

**System → Tasks** shows each `export` run with its own logs. A release that fails to import
five times in a row is marked failed rather than retried forever.

## Reverse proxy

Anything that forwards a whole host name to port 8050 works. With Caddy:

```
releasarr.example.com {
    reverse_proxy your-host:8050
}
```

Set `RELEASARR_AUTH_COOKIE_SECURE=true` once it is served over HTTPS. The installable app
needs HTTPS too.
