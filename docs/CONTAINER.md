# Build and run the private collector container

The image builds the dashboard in Node 22 and installs the Python 3.13 collector
from a wheel. It runs as UID/GID 10001, with named access enabled and persistent
SQLite/signing secrets beneath `/data`. Model dependencies and provider credentials
are not included. Built assets use `GOVERNLOOM_WEB_DIST`; installed collectors can
set this host path explicitly too.

```sh
docker build -t governloom-local .
docker run -d --name governloom-local --read-only --tmpfs /tmp:rw,noexec,nosuid --cap-drop ALL --security-opt no-new-privileges -p 127.0.0.1:8000:8000 -v governloom-data:/data governloom-local
docker exec -it governloom-local python -m governloom.cli bootstrap-admin alice
```

Bootstrap prompts for a private password; there is no default account. Open
`http://127.0.0.1:8000`, sign in, configure an application/policy and create its
ingestion key. Bootstrap refuses existing accounts. Only loopback is published
in this command. For private remote access configure TLS, allowed hosts/origins
and network controls explicitly; this image is not a hosted deployment.

Start the optional outcome watchdog in a separate terminal:

```sh
docker exec governloom-local python -m governloom.cli monitor-worker
```

For webhooks configure the host allowlist at container creation, provision the
receiver and its secret, then run `webhook-worker`. A production worker should
have its own managed process using the same persistent database/secrets/config;
`docker exec` demonstrates the command and does not provide a supervisor.
HTTPS webhook receivers must resolve exclusively to public addresses; a container
service name/private network address is not a bypass of that restriction.

Stop/remove the application container with `docker stop governloom-local` and
`docker rm governloom-local`; the named data volume persists. Existing bind-mounted
directories must grant UID 10001 access. Back up database plus signing secrets as
described in [recovery](RECOVERY.md). Do not delete the named volume to upgrade.

The distribution CI job builds the image and tests named access, dashboard serving,
deadline persistence, exact event replay and eventual actuals across container
restart. It uses an ephemeral test account/volume, no provider calls and deletes
only its owned CI container/volume. The [v0.6 distribution job](https://github.com/rahbarahsan/governloom/actions/runs/39559521550)
passed both creation and restart checks at `4e58313`, running as UID 10001 with
the built dashboard. Local Windows has no running Docker daemon; execution was
verified in Linux CI. No image is published
to a registry. See [release evidence](V05_EVIDENCE.md) for verified results.

Design references: [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
and [runtime flags](https://docs.docker.com/reference/cli/docker/container/run/).
