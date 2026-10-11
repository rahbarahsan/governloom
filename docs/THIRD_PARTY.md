# Attribution

Application code, fictional Northstar policies and fixtures are original
repository material under the existing root Apache-2.0 license. RAG source-support
labels are engineering-authored. The runtime mini-applications also use the public
datasets credited below; they are separate from the legacy fictional workbench.

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
| NumPy / scikit-learn | Optional actual mini-application models | numpy/numpy; scikit-learn/scikit-learn |

`requirements.lock` and `web/package-lock.json` record verified versions. Consult
each distribution's own license for its exact terms. No upstream endorsement
is implied. Container builds use the official Node 22 and Python 3.13 Debian
Bookworm images; preserve upstream software licenses when distributing an image.
No project image or package has been published to a registry.

The README GIF and still preview are original captures of actual owned runtime
applications and labeled replay of recorded real model evidence. Pillow is pinned in
`scripts/requirements-media.txt`; its installed license remains intact.

## Data and transformations

The vision and standalone classifier use scikit-learn's bundled digit subset:
Alpaydin, E. and Kaynak, C. (1998), Optical Recognition of Handwritten Digits,
DOI 10.24432/C50P49. [UCI's dataset page](https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits)
licenses it under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Our internal train/calibration/holdout splits and declared occlusion/noise
transformations differ from the original benchmark protocol; original labels
under corruption have not received independent recognizability review.

The forecaster explicitly downloads and retains the complete
[NOAA GML monthly CO2 source header](https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt),
crediting NOAA Global Monitoring Laboratory, its data providers and the Scripps
Institution of Oceanography contributors. Downloads and raw snapshots stay in
ignored `data/`; public evidence records hashes and derived metrics. Site changes,
interpolated observations and revised snapshots constrain interpretation; this
is not a real-time-vintage climate study. See [forecasting](../examples/forecasting/README.md).
