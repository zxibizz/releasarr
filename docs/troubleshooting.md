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
- **A reverse proxy rewriting the path.** The session cookie is scoped to `/api/auth`. Serve
  Releasarr at the root of its own host name; a sub-path such as `/releasarr/` is not supported.

## The setup screen appears again

The database is gone, which almost always means `/config` is not mounted: every recreate starts
from an empty instance. Check the volume in your compose file.

## Account locked

Ten failed sign-ins lock an account for fifteen minutes
(`RELEASARR_AUTH_MAX_FAILED_LOGINS`, `RELEASARR_AUTH_LOCKOUT_SECONDS`). Wait it out; the next
successful sign-in clears the counter.

## Searching or grabbing says the integration is not configured

Fill it in under **Settings → External services**. Each base URL must include the API path:
Sonarr and Radarr `…/api/v3`, Prowlarr `…/api/v1`, qBittorrent `…/api/v2`. The connection test
next to each one checks it without saving. A field marked *Set by environment* comes from a
`RELEASARR_*` variable and can only be changed there.

From inside the container, other containers are reachable by name only on a shared Docker
network — `http://sonarr:8989/api/v3`, not `http://localhost:8989/api/v3`.

## A finished download never imports

The release is marked completed but Sonarr or Radarr reports that the path does not exist.
Releasarr hands over the path qBittorrent reports, unchanged, so it has to exist at that same
path inside the Sonarr and Radarr containers. If qBittorrent saves to `/downloads/…` but Sonarr
sees the same directory as `/data/downloads/…`, the import fails. Mount the download directory
at the same path in the qBittorrent and \*arr containers.

**System → Tasks** shows each `export` run with its own logs. A release that fails to import
five times in a row is marked failed rather than retried forever.

## Reverse proxy

Anything that forwards a whole host name to port 8050 works. With Caddy:

```
releasarr.example.com {
    reverse_proxy releasarr:8050
}
```

Set `RELEASARR_AUTH_COOKIE_SECURE=true` once it is served over HTTPS. The installable app
needs HTTPS too.
