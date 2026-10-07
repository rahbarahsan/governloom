# Attribution

Application code, fictional Northstar policies and fixtures are original
repository material under the existing root Apache-2.0 license. No external
corpus, benchmark, third-party imagery or validation labels were copied.

Dependencies are installed by package managers, not vendored as source. Their
upstream LICENSE/NOTICE files remain in installed Python distributions and
`web/node_modules`. Preserve those files if distributing a dependency bundle.
The Python wheel includes this project's license and corpus; Vite retains
dependency license comments in the built dashboard.

| Dependency | Role | Upstream project |
| --- | --- | --- |
| FastAPI / Starlette | API | fastapi/fastapi; Kludex/starlette |
| Pydantic | Validation | pydantic/pydantic |
| SQLAlchemy | Persistence | sqlalchemy/sqlalchemy |
| Uvicorn | ASGI server | Kludex/uvicorn |
| React | Dashboard | facebook/react |
| Vite | Build/development | vitejs/vite |
| TypeScript | Static checks | microsoft/TypeScript |
| pytest / httpx | Backend tests | pytest-dev/pytest; encode/httpx |
| Playwright | Browser tests | microsoft/playwright |
| Prettier | Formatting | prettier/prettier |
| Pillow | Optional documentation GIF encoding | python-pillow/Pillow |

`requirements.lock` and `web/package-lock.json` record verified versions. Consult
each distribution's own license for its exact terms. No upstream endorsement
is implied. A public dataset would require a separate redistribution review;
none is shipped here.

The README GIF and still preview are original captures of this application's
fictional no-key demo. Pillow is pinned separately in
`scripts/requirements-media.txt`; its installed license remains intact.
