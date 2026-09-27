# Upgrading

Pin a version tag rather than `latest`, so a restart never changes the version underneath you:

```yaml
image: ghcr.io/zxibizz/releasarr:0.11.0
```

The published tags are:

| Tag | Moves to | Use it if |
| --- | --- | --- |
| `X.Y.Z` | nothing, ever | You want restarts to be boring. Recommended |
| `X.Y` | the newest `X.Y.z` | You want patch fixes without thinking about it |
| `X` | the newest `X.y.z`, from 1.0 on | You want features too, but not a breaking release |
| `latest` | the newest stable release | You do not mind a breaking upgrade arriving on a restart |
| `beta` | the newest prerelease | You are testing a release candidate |

`beta` and `latest` never point at the same image: a prerelease is only ever published as
`beta` and its exact version, and never moves `latest`, `X.Y` or `X`.

Then:

1. Read the [changelog](../CHANGELOG.md) for the versions you are crossing.
2. Back up the database — see below.
3. Pull the new tag and recreate the container. Migrations run automatically on every start,
   before the API or scheduler come up; a failed one stops the container instead of serving
   against a half-migrated schema.

Downgrading across a migration is not supported: bring the old database back from your backup
instead.

## Backups

Everything Releasarr keeps is in `/config`, or in Postgres if you pointed it there:

- **SQLite**: stop the container and copy `/config/releasarr.db`. Copying it while the
  container runs can catch a write half-done.
- **Postgres**: `docker exec releasarr-postgres pg_dump -U releasarr releasarr > releasarr.sql`.
- **`/config/auth-secret`**: signs access tokens. Losing it costs nothing — sessions live in the
  database and refresh onto a new secret on their own — but anyone who has it can forge a
  session, so keep it out of backups you share.

## Moving to Postgres or a split deployment

Pointing `RELEASARR_DATABASE_URL` at Postgres starts from an empty database: requests,
releases, accounts and the Settings page overrides in `/config/releasarr.db` are not copied
over. Note down any settings you changed in the UI first. The next Sonarr and Radarr sync
recreates the requests; release history and file mappings do not come back.

If you build the image yourself: `Dockerfile.all-in-one` is now `Dockerfile`.

## From 0.11 to 0.12

The API and its paths now follow the \*arr apps. Nothing needs migrating by hand, but anything
outside Releasarr that talked to it does:

| | 0.11 | Now |
| --- | --- | --- |
| API prefix | `/api/` | `/api/v1/` |
| Instance info | `GET /api/system` | `GET /api/v1/system/status` |
| Health probe | `GET /api/healthz`, `/api/readyz` | `GET /ping` |
| Service key | `X-API-Key` header | `X-Api-Key` header (case never mattered) or `?apikey=` |
| Sonarr URL | `http://sonarr:8989/api/v3` | `http://sonarr:8989` |

Old \*arr and qBittorrent URLs with the API suffix keep working, so stored settings and
`RELEASARR_*_URL` variables can be cleaned up at leisure. `RELEASARR_AUTH_COOKIE_PATH` is ignored
now; remove it. Everyone is signed out once, because the refresh cookie moved with the API.

## From before 0.10.0

Releasarr used to be built from a checkout and run with the database and logs mounted into
`/app`, nginx on port 80, and every setting in an `--env-file`. 0.10.0 is the first published
image, and moves all of that:

| | Before | Now |
| --- | --- | --- |
| Image | built locally from `Dockerfile.all-in-one` | `ghcr.io/zxibizz/releasarr:0.11.0` |
| Port inside the container | `80` | `8050` |
| Database | `/app/releasarr.db` | `/config/releasarr.db` |
| Logs | `/app/.logs/` | `/config/logs/` |
| Runs as | root | `PUID`:`PGID`, default `1000:1000` |
| `RELEASARR_AUTH_SECRET` | required | generated into `/config/auth-secret` when unset |
| `RELEASARR_AUTH_COOKIE_SECURE` | `true` | `false` |
| `RELEASARR_METADATA_LANGUAGES` | `("eng", "rus")` | `("eng",)` |

To carry an existing SQLite install over:

```bash
docker stop releasarr && docker rm releasarr

mkdir -p releasarr-config/logs
cp services/backend/releasarr.db releasarr-config/releasarr.db
cp services/backend/.logs/* releasarr-config/logs/ 2>/dev/null || true
sudo chown -R 1000:1000 releasarr-config   # your PUID:PGID
```

Then start it from [`compose.example.yaml`](../compose.example.yaml) with `./releasarr-config`
as the `/config` volume, and:

- **Publish `8050:8050`**, not `8050:80`. A qBittorrent *Run external program on torrent
  finished* hook pointed at Releasarr is no longer needed and can be removed: the release sync
  picks up finished torrents on its own.
- **Keep your `RELEASARR_AUTH_SECRET`** in the environment, or drop it and let one be generated;
  open sessions refresh onto the new one without anyone signing in again.
- **Behind a TLS reverse proxy, set `RELEASARR_AUTH_COOKIE_SECURE=true`**; that used to be the
  default.
- **Relied on Russian titles?** Set `RELEASARR_METADATA_LANGUAGES=["eng", "rus"]`, or add `rus`
  under **Settings → Metadata providers**, before the next sync runs.
- **Your `.env` still works**: pass it with `env_file:` and every value in it stays pinned, as
  before. Or leave it out and move the settings into the Settings page.

On Postgres there is nothing to copy: keep `RELEASARR_DATABASE_URL` pointing at the same
database and apply the rest of the list.
