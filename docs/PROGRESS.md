# Release progress

## Delivered v0.7: guided policies and measurable coverage (2026-10-22)

Release source/docs/GIF pushed at 3042ea2. All six final CI jobs passed:
https://github.com/rahbarahsan/governloom/actions/runs/39720294790.
Python 3.11/3.13: 120 passed, three optional skips each. Eight Chromium workflows
passed (35.6 s), including the deterministic application-selection race regression.
Actual-model examples: ten checks plus quickstart, discovery and policy testbeds.
SDK integration: four checks including an installed Node tarball consumer.
Distribution passed fresh installed 0.7.0 legacy/discovery consumers (35.947 s to
first legacy model incident on this CI host), then non-root/read-only container
creation/restart, access, dashboard, deadline persistence and replay checks.

Shipped five packs/nine trusted source-backed starter controls, per-control
recommendations/selection/deferrals, explicit metrics/denominators, confirmed
permissions/SLA/relevance meanings and immutable runtime control references.
Historical plans and the v1 runtime event contract remain compatible. Source/model
suggestions cannot authorize tools or rewrite the trusted catalogue. Startup
refreshes cannot overwrite a later explicit application selection.

Local full regression: 131 passed before the final corrected-role regression;
31 expanded discovery/guidance checks passed from both source and final installed
wheel. Final wheel SHA-256:
1658d3d8613622a3ab2a63ad0e3b50a451c4e9f13f67e684752364e0a74e6ba4.
Four owned applications completed with zero provider requests. Public aggregate
implementation/corpus hashes and all 59 Markdown local links verified. GIF:
seven actual Chromium frames, 28 seconds, 443777 bytes, 1280x900, zero new requests.

All owned services stopped; final inspection found zero project Python/Node
processes and zero listeners on 8000/5173. Only the original untracked brief
remains outside commits. No registry/image publication, hosted deployment or
external-recipient notifications occurred. No v0.7 implementation work remains.
Recommended v0.8 is in docs/ROADMAP.md; wait for the user's next instruction.
The documentation-only completion checkpoint skips redundant CI; the verified
release code is 3042ea2. The earlier intermediate checkpoints below are history.

### v0.7 implementation checkpoints

User approved implementation of the guided policy/metric plan. Deliver in order:
1. Versioned source-backed catalogue and forecast discovery-to-incident slice.
2. Common, classification, RAG and tool-permission packs; explicit metric
   denominators, missing evidence, owner decisions and immutable rule references.
3. Dashboard selection/review, owned mini-applications, correctness/security,
   browser, installed-package and CI checks; fix failures before delivery.
4. Version/docs/roadmap/GIF, focused commits and push; verify CI and stop services.

Defaults: NIST AI RMF 1.0 plus applicable OWASP LLM Top 10 2025 references;
observation-only proposals, task-specific 10% exploratory calibration settings,
no invented SLAs/permissions, no paid provider dependency. Preserve original
untracked governloom-build-brief.md. No repository/ancestor AGENTS.md found.
v0.6 remains historical evidence; new catalogue versions do not rewrite plans.
Checkpoint: trusted versioned five-pack catalogue, authenticated read API,
per-control recommendations/selection/dismissals and explicit metric results are
implemented. Forecast slice verifies confirmation -> activation -> linked actual
-> incident with frozen catalogue references. Composition supports tool/citation
checks; permissions/SLA/relevance meanings require owner confirmation. Existing
v0.6 records/event contracts remain readable. Python tool observation mapper added.
25 discovery/guidance checks passed (8.24 s), including arithmetic, no labels,
undefined denominators, scopes, group leakage, permissions and catalogue auth.
One test setup initially omitted the viewer's required application grant; fixed.
Dashboard review/selection and source references implemented, including owner
permissions/SLA/relevance decisions, persisted deferrals and unsaved-change guards.
Forecast browser workflow passed; new composite RAG/tools workflow passed (8.2 s).
Initial composite fixture lacked the required operator identity; fixture fixed.
Production dashboard build passed with normal Windows access for esbuild.
All 125 Python checks passed (136.08 s), including actual-model examples and SDK.
Four-app HTTP run data/v07-policy-b completed: actual digits, NOAA, local retrieval
and trained local intent router. Tool attempts flag while independent application
authorization denies deletion. Citation controls are deliberately authored; no new
AI answers or provider calls. Raw runs private under data/, services cleaned up.
Next: compatibility/security refinements, installed distribution/Node consumers,
full browser suite, v0.7 docs/version/GIF and release CI.

Release refinement checkpoint: historical plan activation, adversarial source
instructions, corrected list mappings and large finite residual arithmetic pass.
Per-class reports are bounded to 100 labels; accuracy remains measurable beyond
that bound. All 30 final discovery/guidance checks passed (10.52 s). Seven full
Chromium workflows passed (47.2 s); final dashboard build passed after moving
source links beside threshold explanations. Node SDK build/contract passed; two
real collector checks passed (7.03 s), including an offline fresh tarball consumer.

Final four-app run: data/v07-policy-final (zero provider calls, all services stopped).
Final fresh installed 0.7.0 wheel: data/v07-onboarding-final; setup 91.571 s,
first legacy actual-model incident 103.395 s; additional discovery consumer used
360 held-out cases, no supplied policy, one incident. Wheel SHA-256:
441dc947675eb9d80becc5856ff1fedca5874003f06890b8eeff8e7d6bd7b7fa.
Final full Python regression and source-visible GIF capture are running; docs
and sanitized aggregate evidence prepared. Next: finish these checks, link-check,
focused commits/push, inspect all release CI jobs and final process cleanup.

Final GIF captured/decoded successfully: seven actual Chromium frames, 28 seconds,
443777 bytes at 1280x900; catalogue/NIST reference visible alongside forecast
measurements, zero new model requests. Private capture data/v07-gif-final records
cleanup. All 59 Markdown local-link checks pass; public aggregate evidence has no
credential patterns and its catalogue hash matches the final installed consumer.

Final full Python suite passed: 131 checks in 153.84 s. Review then found a
corrected-field edge case: numeric category values on non-alias paths needed
the same normalization as inferred fields. Fixed by revalidating selected role
projections before evaluation; padded tool permissions are rejected to keep
offline metrics identical to runtime permission checks. Expanded discovery/
guidance suite: 31 passed (13.09 s). Rebuilding final wheel for installed checks;
the no-isolation build attempt lacked setuptools, so use the standard isolated
build already used by distribution CI. No application test failure remains.

Final rebuilt wheel installed under data/v07-wheel-final/installed; import location
verified and all 31 discovery/guidance checks passed (11.24 s). Final wheel SHA-256:
1658d3d8613622a3ab2a63ad0e3b50a451c4e9f13f67e684752364e0a74e6ba4.
Supersedes the pre-correction candidate hash above. Final four-app run was repeated
against current documentation under data/v07-policy-release and public aggregates
were refreshed with implementation hashes and the RAG corpus manifest. Retrieval
recall remains 50% on four held-out authored queries. Source and artifact checks
are complete; push the focused release commits and inspect GitHub Actions next.

Release pushed at 1ab40b6; CI run 39719619487 passed examples, SDK, distribution
(including non-root/read-only container/restart) and Python 3.13. Python 3.11
exposed an exact floating-point test assertion (1.9999999999999998 versus 2),
not a metric failure. Use pytest.approx for forecast means/RMSE/bias and push
the test fix, then wait for the full final matrix. Browser job still running
at this checkpoint. All local project Python/Node processes and listeners on
8000/5173 were confirmed zero. No registry/hosted publication occurred.

Floating-point test fix pushed at eeef6e1; all six jobs in run 39719842529 passed.
First-run browser trace independently exposed a real startup race: a delayed
initial /applications response could restore the first application after explicit
selection, causing a policy operation against that selected-back application.
App refresh now rejects responses for superseded selections before setting lists
or scoped state. A deterministic held-response browser regression plus composite
policy workflow passed locally (2 checks, 25.2 s). Push this UI fix and verify
the final eight-workflow browser/full CI run before marking delivery complete.

The new delayed-response fixture needed an explicit array type under strict
TypeScript compilation. Added it; production tsc/Vite build passed (2.99 s).
No backend/wheel or catalogue changes followed the verified final wheel.

## Delivered v0.6: explore, confirm and prepare monitoring (2026-10-21)

Release code/docs/GIF pushed at `4e58313`; all six CI jobs passed:
https://github.com/rahbarahsan/governloom/actions/runs/39559521550.
Python 3.11/3.13 core: 104 passed with two optional skips each. Actual-model
examples: ten checks plus the headless quickstart and the new no-prewritten-policy
digit discovery-to-incident workflow. SDK integration passed; all six Chromium
workflows passed (28.3 s), including persistent owner corrections after reload.
Distribution installed 0.6.0 in a fresh standalone Linux consumer (19.862 s to
actual incident), then built and verified non-root/read-only container creation
and restart, named access, dashboard, deadline persistence and exact replay.

Final local full run: 114 passed; the subsequently expanded discovery suite passed
all 15 checks, including equivalent numeric labels. The final rebuilt installed
wheel also passed all 15 discovery checks (5.70 s). Final wheel SHA-256:
9ac6c9fc6a9e3ab8e7e846ff036a10d9739ecc9f2dcc42062ec09f382086f9a7.
Schema, dependency, compile, Node package and 38-guide link checks passed.
GIF: six verified actual Chromium frames, 24 seconds, 400242 bytes, 1280x900.

Exactly three semantic model requests were made; all replays/captures made zero
additional requests. Forecast and vision proposals yielded actual flags/incidents;
the recorded RAG answer correctly leaves calibration unavailable. No independent
owner study or semantic accuracy guarantee is claimed. All owned services stopped;
final inspection found zero project processes and zero listeners on 8000/5173.

Focused commits: e544820 vertical slice, 72c4564 UI/actual-model mapping, 34a896b
cross-client identity/correction persistence, 08a43a4 packages/CI, c139e89 GIF,
90583e1 numeric-label boundary and 4e58313 docs/evidence. All are pushed. Only the
original untracked brief remains outside commits. No registry/image publication,
hosted deployment or external-recipient notification occurred.

No v0.6 implementation work remains. Recommended v0.7 scope is in docs/ROADMAP.md;
wait for the user's next instruction before starting it. The milestone history
below records development checks and then-pending steps, now completed.

User authorized implementing the discovery-first workflow discussed after v0.5.
The owner reviews an evidence-backed application draft and corrects unresolved
assumptions; they do not start by inventing metrics, datasets or policy JSON.
Scope remains one explicitly connected application, with owned forecast/vision/
RAG mini-applications for verification. Preserve the untracked original brief.
No paid API use, hosted deployment, registry publication or external messages.

Delivery sequence:
1. Local bounded read-only artifact/trace explorer; evidence-backed inference,
   immutable import and owner confirmation; real forecast calibration-to-incident
   vertical slice with versioned dataset/proposal and guarded observation activation.
2. Vision/classification and RAG evidence adapters, explicit unavailable states,
   draft review UI, correction and calibration/activation workflows. Optional
   semantic analysis uses a bounded trusted adapter; no silent provider calls.
3. Actual mini-app verification, discovery/error/owner-correction measurements,
   security/role/concurrency/leakage boundaries, installed package and browser checks.
4. Update docs/roadmap/version/demo evidence, focused commits and authorized push;
   inspect/fix CI, stop owned processes, leave a final resume checkpoint.

Repository/ancestor instructions inspected; no AGENTS.md found. Baseline main is
c64e1f4 with only the original untracked brief. Forecast vertical slice implemented:
bounded local source inspection without execution; exact artifact/semantic quote
checks; immutable discovery/owner corrections; calibration-only dataset/proposal;
transactional idempotent activation with stale-policy conflict and version-bound
flag-only rules. Forecast/discovery/runtime suite: 26 passed, 8.89 s. Import/actor/
scope refinements: 9 passed, 5.87 s. Default Windows pytest temp/cache were denied;
workspace data/ basetemp and no cache provider resolved the environment issue.
Dashboard TypeScript/Vite build passed with normal Windows access for esbuild.
UI review/import/calibration/activation is implemented; next: browser workflow,
actual NOAA/vision/RAG captures, discovery adapter boundaries and release evidence.

Owned actual-model runs completed. Numeric NOAA and real digit traces produced
calibrated policies and incidents with no supplied policy; a single recorded RAG
answer correctly left calibration unavailable. Optional semantic capture completed
exactly three requests through the existing ChatGPT login (cap three, no API key):
21 source-referenced hypotheses and 23 unreviewed scenarios. Source quotes are
validated; this is not independent semantic accuracy or usability evidence.
Private capture: data/v06-discovery-2026-10-21-b. Public-mapper replay is in progress
with frozen bundles and zero new requests. The browser workflow passed (1, 8.7 s)
after correcting two test selectors to the actual navigation/accessibility names.
Observer/privacy/ambiguity suite passed (11, 6.78 s). Next: boundary refinements,
full checks, documentation/version/distribution evidence and CI delivery.

Full local Python suite passed 111 checks (114.28 s) before the final current-
confirmation/preview/list-bounds refinements. The expanded discovery suite passed
14 checks (5.41 s), covering current-understanding invalidation, preview without
publication, secret-free validation errors and RAG identity/semantic distinction.
All six Chromium workflows passed (45.0 s). The public DiscoveredObserver mapper
preserves actual live versions and rejects missing actuals; it never stamps a
calibration version onto a new model. Frozen zero-request replay completed in
3.568 s with actual digit/forecast flags and one incident each. Held-out budget
violations are surfaced as warnings, not silently retuned. Next: package checks,
actual discovery GIF, public evidence/docs and six-job CI delivery.

Final full Python suite: 114 passed, 159.59 s; existing Starlette/httpx deprecation
only. Core imports from the installed 0.6.0 wheel passed without NumPy/scikit-learn.
Wheel SHA-256: e84a97fa11e3b054732a5affc4c4fb0547d8b141e94371f0436e062ac6e20947.
Node 0.6.0 build, actual HTTP contract and local tarball packaging passed.
Final frozen public-mapper replay completed in 3.951 s with zero new requests;
report: data/v06-discovery-2026-10-21-e. Public whitelist:
docs/experiments/v06-2026-10-21.json. Original semantic request count remains three.

Capture exposed cross-language integral-number representations in dataset hashes;
numeric normalization and a regression check fix that new format. A separate
Windows capture stdin decoding issue was fixed with explicit UTF-8. Actual
browser-to-Python capture now passes. Metrics use readable calibration/held-out
tables; final media capture is in progress. Next: final links/schema/package
checks, focused commits/push, inspect/fix six CI jobs and stop owned processes.

Final discovery GIF captured, decoded and visually reviewed: six frames, 24 s,
400242 bytes at 1280x900. It shows exact evidence, prefilled confirmation, readable
calibration/held-out results, budget warning, observation activation and an actual
NOAA forecast incident. All capture services stopped; zero new model requests.
Current next step: final package/schema/link checks, focused commits and authorized
push, then inspect/fix all six CI jobs and record the verified release checkpoint.

Package verification: all 14 discovery boundary checks passed against the installed
wheel (5.51 s), proving packaged behavior as well as imports. Node 0.6.0 tarball
installed offline into a separate consumer and its exports passed. All local
links across 38 Markdown guides passed; schema drift, compile, dependency and
public credential-pattern checks passed. Final review UI preserves confirmed
description/mappings across reload; history remains inspectable.

Final boundary refinement: integral numeric class labels such as 1/1.0 compare
as the same category rather than manufacturing classification errors. The expanded
15-check discovery suite passed (7.83 s); final wheel rebuilt to include this fix.
Earlier full-suite count remains 114 plus this added regression. Release CI will
collect the final suite. Model-analysis request count remains three.

## Delivered v0.5: outcome coverage and connected-system validation (2026-10-11)

Release code/docs/GIF pushed at `aca7c10`; all six CI jobs passed:
https://github.com/rahbarahsan/governloom/actions/runs/38116779187.
Core Python 3.11/3.13 each passed 89 checks with two optional skips; actual-model
examples passed ten checks plus the headless quickstart, SDK integration passed,
and all five Chromium workflows passed. Distribution independently installed the
0.5.0 wheel in a fresh Linux consumer (29.856 s to actual incident), then built
the container and passed non-root creation/restart, built-dashboard, persisted
deadline, exact replay and actual-resolution checks. CI owned services stopped.

Final local process/listener inspection found zero project-owned processes and
zero listeners on 8000/5173. Only the original untracked brief remains outside
commits. Release versions are 0.5.0; packages/images remain unpublished.
No further v0.5 implementation work remains. Recommended next release is v0.6
as scoped in docs/ROADMAP.md; do not start without the user's next instruction.
Independent users/labels and sustained deployment evidence remain unavailable.
The implementation/capture history below is retained for reproducibility.

User authorized proceeding with the recommended next release. No participating
team is required: use owned standalone consumers and real mini-applications.
Preserve the original untracked brief. No paid API use, external-recipient
messages, registry publication or hosted deployment is part of this scope.
Existing explicitly authorized ChatGPT subscription capture may be used with a
fixed request cap, tool-free prompts and private artifacts; never API-key fallback.

Delivery sequence:
1. Forecast vertical slice: explicit outcome deadlines, persisted missing/late
   evidence, bounded watchdog, incident/webhook delivery and eventual actuals.
2. Chronological non-overlapping block calibration on the frozen NOAA snapshot;
   grouped vision and broader source-backed RAG claims/retrieval gaps/judge errors.
   Freeze engineering labels/splits before inference; do not invent independent
   human review or theoretical guarantees under serial dependence.
3. Signing-key rotation with bounded overlap, full database-plus-secret recovery,
   conservative terminal delivery retention and restart/load/storage failure drills.
4. Standalone installed-package onboarding and a CI-tested container build path,
   release documentation/media as needed, meaningful local/remote checks, focused
   commits/pushes and stopped owned services. External users remain unobserved.

Repository/ancestor instructions inspected; no AGENTS.md found. v0.4 code is
clean apart from the original brief. Research checks: current official Codex
non-interactive/authentication docs, Standard Webhooks multi-signature rotation
and dependent-data conformal research. All four implementation stages and the
release push/remote distribution/browser/core checks are complete.

Vertical slice implemented: explicit numeric deadlines, transactional expectations,
bounded restart/concurrent-safe watchdog, scoped coverage API/UI, frozen-policy
incidents and signed escalation; later actuals resolve coverage without closing
incidents. Existing event replay hashes remain compatible. Twenty outcome/runtime/
retention checks passed (5.16 s); temporal boundary checks passed (2, 0.03 s).
Rotation/incident/outcome boundary suite passed (11, 13.83 s); full bundle recovery/
retention checks passed (4, 1.15 s). Actual SQLite SQLITE_FULL page-cap rollback,
capacity recovery and replay passed with rotation/recovery (4, 1.28 s).

Owned NOAA HTTP drill completed in 18.68 s: deadline flagged, old receiver accepted
dual signatures, lost first receipt retried (2 attempts, 1 notification), receiver
updated, actual received 4.580 s late, incident remained open. Six hundred controlled
observation events accepted in 3.996 s; this is a bounded serial software drill,
not sustained production throughput. Full bundle restored 602 observations,
30 entities and 2 signing keys with integrity/checksum verification; all services
stopped. First preparation run rejected a rate above the existing 10000/minute
policy limit and made zero provider requests; runner corrected.

Forecast block threshold frozen from eight 3-month 2019-2020 blocks is 1.496969
ppm. Six of 48 held-out months / 5 of 16 blocks exceed it, versus 15 months under
the original 90th-percentile gate. No missing actuals in this snapshot; revised,
serially dependent data still has no nominal coverage guarantee. Eight document-
disjoint RAG groups (24 authored claims plus retrieval-gap/natural-answer checks)
were frozen before a capped 14-request existing-ChatGPT-login capture. All fourteen
requests completed; four unknowns in each split remain unresolved. A custom-corpus
retrieval defect was fixed and the exact frozen prompts/schemas replayed with zero
new requests. Expected-document retrieval improved from 0/8 to 5/8; three misses
remain, and the natural answer preserves the original legacy-corpus limitation.

Standalone clean-wheel Windows consumer completed: 130.500 s setup, 148.598 s to
one real incident; separate copied application, installed public hook, real owned
classifier, one target call. It captured the development baseline label 0.4.0;
final packages are 0.5.0 and CI repeats fresh installation. It is not independent
user feedback. Public whitelisted reports: docs/experiments/v05-2026-10-11.json;
interpretation and provenance: docs/V05_EVIDENCE.md.

Final local full Python run: 99 passed in 153.19 s; a subsequently added calendar-
gap calibration/holdout boundary check passed separately (1, 3.38 s). Current
suite contains 100 checks. All five Chromium workflows passed in 1.1 min, including
coverage and scoped rotation. A read-only audit request transiently reset after
Windows keepalive idle; maxRetries=2 applies only to that GET, never mutations.
Dashboard and Node SDK builds/HTTP contract passed. Final 0.5.0 Python wheel built.

Twelve-frame actual runtime GIF captured and visually inspected: 29.8 s,
523356 bytes, 1280x900. It adds deliberately overdue NOAA feedback and late actuals
with review still open. All six capture actors stopped; no new LLM requests.
The container is implemented with non-root/read-only runtime and named access;
local Docker daemon is unavailable, so remote distribution CI must establish its
build/restart result. Those final checks and cleanup are now complete, as recorded
in the delivery checkpoint above.

Final packaging checks passed: installed Python 0.5.0 wheel imports the API,
deadline/recovery and integration modules without importing NumPy/scikit-learn;
Node 0.5.0 tarball installed offline into a separate consumer and exports the hook
and deadline contract. Dependency check, schema drift and compile checks passed;
all local links across 36 Markdown guides and public-report credential-pattern
checks passed. npm's default cache was sandbox-restricted; workspace-local cache
resolved packaging without changing user cache permissions. Focused local commits:
9ea1fd1 deadlines, 5e81a4a rotation/recovery, e414df5 domain validation, 6a6281a
calendar gap boundary, 54de8e4 distribution, 986e7c2 runtime GIF and aca7c10 release
docs/evidence. All are pushed; all six remote checks passed at aca7c10. This final
documentation checkpoint records that verified release; it adds no code changes.

## Delivered v0.4 public developer launch (2026-10-10)

User authorized the launch-readiness work: reliable incident delivery, a quickstart
that works without assistance, copyable real-system integrations, measured limits
and community/security documentation. Preserve the untracked original brief.
No deployment, paid API usage or messages to external recipients are authorized.

Delivery sequence:
1. Working vertical slice: real mini-application risk, registered signed webhook,
   persisted retry/restart/deduplication, application action evidence and incident
   review. Add named-role API/UI visibility and failure replay.
2. One-command isolated quickstart with real digit inference, generated private
   credentials, owned local receiver and cleanup; clean-install/container path.
3. Easier Python/TypeScript integration and an explicit versioned event contract.
4. Publish measured onboarding/overhead/failure evidence and detector coverage;
   retain honest engineering-label and forecast dependence limits.
5. Contributor/security/issue guidance, concise README, versioned release notes,
   full local/remote checks, focused commits/pushes and stopped owned servers.

Inspection: v0.3 is clean apart from the original brief. Existing runtime
escalations are transactional; the legacy dispatcher is a local test-only sink.
No repository/ancestor AGENTS.md was found. Standard Webhooks 1.0 and OWASP SSRF
guidance were reviewed against primary sources.

Vertical slice complete: seven signed-delivery/incident checks passed (12.31 s),
including real receiver commit followed by worker os._exit(23), lease recovery,
same-body one-notification replay, concurrent claiming, Retry-After, endpoint/DNS
guards, dead-letter/replay and named-role scope. Dashboard build passed after
esbuild's ancestor-directory scan required normal elevated access. Owned real
digit quickstart completed in 20.335 s; its first incident arrived in 10.104 s.
Fresh setup via scripts/quickstart.py --check --venv data/launch-clean-venv
--directory data/launch-clean-2026-10-10 completed: setup 104.144 s, first incident
119.475 s from setup start; receiver persisted one notification after two attempts.
Application review/outcome and authenticated response-inspection attestation were
recorded. Services stopped; credentials/raw databases remain ignored.

Native async Python and the Node/TypeScript SDK are implemented. Real integration
checks exposed timestamp regeneration on replay; explicit prepare_event/prepareEvent
now freezes the body before retry. Two integration checks passed (4.29 s), including
the compiled Node SDK against the actual collector. Node HTTP contract check passes.
The explicit numeric OpenTelemetry span adapter passes its ingestion/privacy/missing
evidence check (0.15 s); this fixture checks the span interface, not an installed
OpenTelemetry SDK.

All five Chromium workflows passed (44.2 s), including receiver failure/replay,
viewer/reviewer denial, operator connection/disable and one-time secrets absent
from browser storage. The first full Python suite passed 84 checks (146.73 s).
New calibration selects only on calibration labels: 5% budget yields 13/261
calibration false positives; held-out 15 captured errors, 3 misses, 26 false
positives and 316 clear controls. Its 7.60% held-out false-positive rate exceeds
the calibration budget and is published without retuning. Original gate: 17
captured errors, 1 miss, 52 false positives and 290 clear controls.

Updated GIF capture initially expired before the worker retry plus five-second UI
poll; backend had actually delivered. A bounded 25-second wait produced ten
verified frames, 24.6 s and 435,696 bytes. Visual review then exposed a first-event
incident counter/cooldown persistence bug from premature ORM autoflush. New
incident admission is deferred until counters are complete; regression checks
cover the first escalation and cooldown. Terminal/replay transitions now clear
leases and fence stale completion. A race fixture was corrected to dispatch one
claim, since a continuously running worker may legitimately claim a replay anew.
Final boundary checks passed; the regenerated ten-frame GIF is 437,724 bytes,
24.6 seconds and 1280 x 900. Visual review confirms one queued escalation and
signed delivery after two attempts. Owned capture services stopped.

Quickstart/docs/SDK packaging/community files and expanded CI are implemented.
Reviewed launch evidence records two captures, source hashes, overhead and gate
trade-offs; no keys/raw databases or new provider requests are published.
Final local checks: 88 Python tests passed (138.61 s); all five Chromium workflows
passed (44.2 s); dashboard production build, dependency check, schema drift check,
compilation and whitespace checks passed. One existing Starlette/httpx deprecation
warning remains. The 0.4.0 wheel installed into a fresh target and core/SDK/API
imports passed without importing NumPy/scikit-learn. The TypeScript tarball built,
installed into a fresh consumer and exported its runtime hook/event preparation.
No registry publication occurred.

Committed-code quickstart capture at 20656e1 completed in 23.655 s; first incident
12.776 s, two sender attempts and one receiver notification. Its code snapshot
hash and separate measurements are published alongside the earlier fresh-install
capture. A separate interactive public-wrapper drill used the same stop-file
protocol as Ctrl+C and proved parent exit plus owned-service cleanup. Early Ctrl+C
cannot race the owner's exclusive directory admission. Legacy browser screenshot
side effects were discarded. No Docker daemon was running; use the tested native
fresh-install path, with no container/deployment claim.

Focused commits cover signed delivery (94a8028), first-escalation/lease fencing
(d3c508a), native SDKs (f93ae46), calibration (ffa4108), quickstart (20656e1),
actual GIF (f9d87a3) and launch documentation/CI (864e2d3). All are pushed to
origin/main. All five release CI jobs passed at 864e2d3: Python 3.11/3.13 core,
actual-model examples/headless quickstart, native SDK integration and Chromium.
Verified run: https://github.com/rahbarahsan/governloom/actions/runs/38094170488.
Local link checking passed across 28 guides. Process/listener inspection found
zero owned Python/Node servers and no listeners on 8000/5173. Original brief
remains untouched and untracked. No required v0.4 implementation remains.

This documentation-only checkpoint follows the verified release; the run above
identifies the exact tested code. Recommended next scope is v0.5 in ROADMAP.md:
independent fresh-checkout onboarding evidence, stronger task-specific grouped
RAG/forecast calibration and longer recovery/storage drills. Registry publication,
deployment, customer pilots and announcements have not occurred.

## Delivered v0.3 follow-through (2026-10-08)

User approved all four next steps: replace the GIF with actual runtime capture,
restart-safe metadata delivery, named authenticated operator roles, and stronger
grounding/drift checks with measured misses and false positives. All four are
implemented and locally verified on the v0.2 foundation. Raw text/credentials
must never enter the durable outbox. Engineering calibration is not independent
human review.
Research: OWASP password/session guidance and the DKW–Massart concentration bound
were checked against primary sources. No customer participation is required.

Final release verification: 76 Python tests passed (101.02 s), all five Chromium
workflows passed (31.2 s), dashboard production build, dependency check and Python
compilation passed. One existing Starlette/httpx deprecation warning remains.
Detector profiles now bind event phase as well as deployment versions; the test
proves an input event cannot enter an output calibration window. The actual digit
HTTP test covers same-origin browser controls, rejected cross-origin writes,
durable counters and application review persistence across service restart.

The replacement GIF has ten verified frames, 24.6 seconds, 426,587 bytes and a
1280 x 900 poster. It shows real digit inference/withholding, named incident
ownership, application label resolution, response-inspection attestation,
durable heartbeat and explicitly labeled recorded real RAG evidence. The capture
made zero new subscription requests. A case-sensitive disposition selector was
fixed, then visual review found a hidden identity banner; its layout was corrected
and the final capture regenerated. Private captures are under ignored
data/runtime-gif-2026-10-08-d/; owned capture services stopped. Automated browser
test side effects on the three legacy screenshots were discarded.

Release version is 0.3.0. The wheel built successfully with isolated build
dependencies; an initial no-isolation attempt lacked local setuptools and was
replaced by the declared build workflow. Reviewed public media is docs/media/.
Installed-wheel 0.3.0 SDK/outbox/auth/detector/API imports passed from the fresh
target directory without importing NumPy or scikit-learn. Whitespace checks pass.
Process/listener inspection found no owned Python/Node servers or listeners on
8000/5173. The final release is pushed to origin/main as 8606bd5, with focused
commits eac945f (phase scope) and a326546 (actual runtime GIF). All four release CI
jobs passed: core Python 3.11/3.13, actual mini-application software integration,
and Chromium workflows. Run:
https://github.com/rahbarahsan/governloom/actions/runs/37841991399.
The original untracked governloom-build-brief.md remains untouched. No pending
release implementation work remains; v0.4 is a recommendation for the next session.
The next recommended scope is v0.4 in docs/ROADMAP.md: durable signed incident
delivery, broader domain validation, async/TypeScript integrations and operational
hardening. This recommendation does not authorize starting another release.

### Implementation checkpoints

First slice complete: `governloom.outbox.DurableObservationHook` freezes metadata
in SQLite, resumes pending deliveries, persists counters/deadlines/attempts, fences
leases, bounds pending bodies/terminal IDs, and rejects text/known sensitive metadata.
Three outbox checks pass (9.83 s), including hard producer death after real HTTP
collector commit, replay with one alert, concurrent admission, expiry and auth failure.
Logical bounds do not constitute a disk quota. Next: server-side named identities.

Named access is implemented: private bootstrap, salted password hashes, revocable
eight-hour sessions, scoped viewer/reviewer/operator/admin roles, server-bound
actors, list/export/object-route scope checks, login throttling and password change.
Existing-account databases cannot fall back to local mode. Four auth/API checks
pass (14.13 s), the outbox/auth/API combination passes seven checks (31.13 s), and
the new Chromium role workflow passes (13.3 s). Dashboard production build passes.
An audit-action test label and a collapsed-details browser selector were corrected;
the role checks themselves held. Next: immutable detector profiles and calibration.

Evidence slice implemented: immutable source/reference profiles, separate checksum
approval, exact deployment scope, transient quote/source/answer validation, explicit
claim coverage gaps, and non-overlapping ECDF windows with conservative DKW bounds
and persistent alpha spending. Known dependent forecasting replay explicitly lacks
a nominal probability guarantee. Sixteen detector/monitoring checks pass (3.00 s);
twelve detector/auth/actual-example checks pass (60.56 s). Actual validation completed
in data/detectors-2026-10-08-b/: vision six perturbed windows flagged/three normal
clear; forecast two offset windows flagged/two normal clear; held-out RAG two risks
flagged/two supported claims clear. One calibration claim unavailable. Ten bounded
subscription requests completed, including a new actual RAG answer whose overbroad
enforcement statement was flagged. First calibration-accessor attempt failed before
inference and was fixed. All owned validation services stopped. Reviewed report:
docs/DETECTOR_VALIDATION.md and docs/experiments/detectors-2026-10-08.json. Capture
was during working-tree development; the Git revision alone is insufficient.
Remote CI succeeded for 3fb782a (run 37833724599). Next: final runtime GIF and checks.

## Delivered runtime checkpoint (2026-10-08 UTC)

Latest steering: the user approved implementation of the plan. No participating
team is available; build independent mini projects to test GovernLoom instead.
The detailed plan is docs/PILOT_PLAN.md: real digit classification, historical
NOAA forecasting and model-backed RAG over actual project documentation. These
projects and the six-stage local sequence are implemented. Vision/forecasting/RAG
have actual-model evidence; launcher, bounded background delivery/heartbeats,
grouped incidents/actions, local escalation, backup/restore and conservative
retention have working checks. Final validation and focused commits are pushed.
A customer pilot is later, not an input blocking development.

Primary data sources, attribution and official local subscription execution docs
were checked. Optional scikit-learn 1.9.1/NumPy 2.5.3 and dependencies were installed
locally for feasibility preparation; core dependency files were not changed.
No new model inference, dataset download or service was started during planning.
That was a planning-only checkpoint; runtime code has since advanced below.

Implementation checkpoint: the vision mini service now trains a real 64-tree
digit classifier and connects through HTTP. Its 360 held-out cases produce
342 correct predictions, 18 errors, 69 review flags, 17 captured errors and one
confident error missed, at a calibration-selected confidence threshold 0.59375.
Two actual-model tests pass (12.86 seconds), including result withholding,
persisted review resolution, label feedback and actual service restart.
Forecasting now serves predictions and linked outcomes through the same HTTP
boundary, records investigations and supports an explicitly configured fallback.
Four example tests pass (20.21 seconds); CI uses a labeled synthetic forecast
fixture and never fetches remote data. The separate actual NOAA snapshot has SHA-256
c9a91a170d09d16afaaad56c4f383ed4fcb7fa0da967998694842d5c8168bcf3.
Direct model evaluation on its 48 observed 2021-2024 outcomes measures MAE
0.75654 ppm and RMSE 0.95067 ppm, versus seasonal-naive MAE 2.59771 ppm.
The frozen 2019-2020 calibration tolerance is 0.97433 ppm; 15 held-out errors
exceed it. These are revised-snapshot historical results, not live forecasting
or a historical data-vintage simulation. Raw snapshot and provenance stay in
ignored data/miniapps/. The RAG service now retrieves actual documentation and
uses the bounded opt-in subscription generator, with explicit post-generation
faults and tool denial before a write. Five example tests pass (24.79 seconds),
including an explicitly fake CI generator with real collector HTTP. A sandbox
temporary-directory permission failure was resolved by using a fresh ignored
workspace basetemp; it was not an application failure. The later launcher run
below records actual RAG generation. Software tests do not establish model quality.

Working continuation: the isolated launcher completed all 360 vision cases and
48 NOAA forecast/outcome pairs in data/testbed-2026-10-08-b/. Exactly 15 natural
forecast outcomes were flagged; deliberate offset and fallback passed. RAG
stopped before inference because the sandboxed CLI could not find its home/login
configuration. All owned services stopped; failed-run reports are retained.
A fresh authorized elevated run completed in data/testbed-2026-10-08-c/ with
exactly three completed local subscription requests. All 1,246 events were
accepted (vision 1,138; forecasting 99; RAG 9) and all owned services stopped.
Natural RAG responses: one answer about tool enforcement, one cautious partial
abstention about text retention, and one refusal to invent a medical approval.
Both post-generation faults were withheld; the unauthorized write was denied
before its marker file existed. Citation membership passed natural answers, but
does not establish claim support. The partial abstention exposes retrieval
coverage limits. An earlier launcher attribute mismatch was
fixed after vision completed; that capture is data/testbed-2026-10-08/.
Three focused application commits 007c99f, e6e6347, cc8fc12 are pushed. All GitHub
Actions jobs passed for cc8fc12 at
https://github.com/rahbarahsan/governloom/actions/runs/37714232976.
Background observation is implemented: bounded RAM queue,
exact-body retry, separate synchronous enforcement, loss counters and scoped
heartbeats. Six delivery tests pass (5.28 seconds), including a real collector
outage/restart, receipt loss without duplicate alerts and quiet batch cadence.
Launcher and reviewed actual-model evidence are committed in a3f669c. Six example
tests include a bounded launcher with no subscription calls/downloads and clean
shutdown. Delivery/incident docs, dashboard coverage and backup/retention/capacity
checks are complete. Incident
grouping, action acknowledgment/operator verification and local test-sink retry
checks pass; two initially incorrect audit-kind assertions were corrected to
the existing review_event audit store. No messages to real recipients were sent.

Final local validation: **67 tests pass (86.34 seconds)**, four browser workflows
pass (26.9 seconds), TypeScript/production bundle, compilation and pip check pass.
Browser checks cover visible cadence counters, incident ownership, app action
acknowledgment and reload. A sandbox Vite resolution failure was rerun with
required access; its own leftover collector was verified/stopped. A selector
matching both a paragraph and hidden option was corrected before successful rerun.
Steady local delivery: 100/100 accepted at 100 attempts/second, enqueue p95 0.449 ms.
Burst: 16 accepted/984 explicitly dropped, max queue 16 and 7,936 serialized bytes;
all 116 accepted events present, one grouped incident/cooldown escalation.
Live-WAL backup tests pass; actual testbed restore preserved 1,246 events and 130
entities, integrity ok. Retention preview on that DB found zero eligible old
observations and applied no deletion. Tests execute pruning only in disposable DBs.
Full reports: docs/TESTBED_EVIDENCE.md, docs/experiments/testbed-2026-10-08.json,
docs/experiments/capacity-2026-10-08.json; integration docs: RUNTIME_DELIVERY.md;
operations: PILOT_OPERATIONS.md. Raw captures/backups remain ignored in data/.
The updated 0.2 wheel builds (57,297 bytes), and its installed SDK, operations
and API import from an isolated target directory without model dependencies.
An initial non-isolated build lacked setuptools; normal isolated build succeeded.
Packaging smoke is now part of Python 3.11/3.13 CI. Next work after delivery:
metadata-only durable outbox with explicit text coverage gaps, authenticated
operator roles, domain-calibrated detectors, then a real customer pilot if one
becomes available. No deployment, paid API calls or external recipients.

Delivered checkpoints: a3f669c (launcher/actual-model evidence), ba2ec7d
(bounded delivery/incident integration), 70c5404 (operations/capacity/release docs).
All are pushed to origin/main. GitHub Actions for code head
70c54049ec68851f972bc8c153599521b3fa94d5 completed successfully: Python 3.11,
Python 3.13, optional actual-model integration and Chromium jobs, including
wheel build/install/import smoke. Run:
https://github.com/rahbarahsan/governloom/actions/runs/37717404315.
Process and listener checks confirm no project servers and no listeners on
8000/5173. The only untracked file remains the user's original
governloom-build-brief.md; it was not modified or committed. This documentation
checkpoint records delivery without changing the validated code.

This section supersedes the earlier claim-evaluation roadmap below. The user
clarified the product: a developer connects an existing AI system through a hook;
GovernLoom monitors production signals, flags risks and supports mitigation.
There is no organization-wide inventory requirement. Vision, RAG, forecasting,
classification and custom systems must share a provider-independent contract.

Implemented: authenticated HTTP event ingestion, Python callable/tool hooks,
immutable configurable runtime policies, transient text scanning, scoped revocable
keys, delayed forecast outcome linkage, rolling numeric signals, durable alerts,
operator ownership/disposition audit, and a live dashboard. The legacy evaluation
workbench remains available. No model provider is needed to monitor a customer's
own running model, and no synthetic target is used in the monitoring product flow.

Earlier foundation checks: 49 backend tests pass (20.08 seconds), including 15 runtime checks
and a real TCP collector process. Coverage includes
vision output withholding, tool blocking before execution, delayed forecast
error, idempotent concurrent replays, privacy, auth, rate limits, and collector
redirect rejection. All four real-browser workflows pass (26.3 seconds), including
policy/key setup, live vision risk evidence, operator mitigation, reload and key
revocation. Earlier navigation assumptions and a missing operator after reload
were fixed in the browser tests. TypeScript/production bundle, compilation and
dependency check pass. The v0.2 wheel builds and public hook/schema/version
imports pass from its installation in the separate clean environment. Research,
runtime integration docs and roadmap now reflect the user's actual product scope.
Checkpoint `4f9fd5a` contains the runtime engine/hook; `cd70907` contains the
dashboard/browser integration; `59351be` contains product research, integration
docs and the revised roadmap. All three are pushed to origin/main. Local
validation and packaging review are complete. Process/listener checks confirm
zero project servers and no listeners on ports 8000/5173. The original brief is
the only untracked file. Remote Python 3.11/3.13 and Chromium checks all passed
for `59351beaf984ce96f820e5d13ad366139b9531e9` in
https://github.com/rahbarahsan/governloom/actions/runs/37629734622.
The v0.2 runtime foundation is delivered. A final documentation checkpoint records
the successful remote result without changing runtime code. Next executable
work: the real-system pilot/reliability milestone in docs/ROADMAP.md; choose
metrics with a consenting team and measure latency, coverage and useful alerts.
Do not claim production scale, risk-detection accuracy, comprehensive PII detection
or compliance certification. Once shipped, follow docs/ROADMAP.md: connect a real
customer system and improve reliable telemetry/incident operations.

Original untracked `governloom-build-brief.md` remains untouched. No deployment
or paid inference is authorized. No manual server should remain after delivery.

## Specification and state

The supplied specification is `governloom-build-brief.md` (no BUILD_BRIEF.md exists).
No repository or ancestor AGENTS.md was found. The README is expanded; the existing
Apache-2.0 license and untracked brief are preserved. Local ChatGPT-subscription
inference is now explicitly authorized; no deployment or paid API calls are authorized.

## Completed

- Repository and toolchain inspected: Python 3.13.1, Node 22.14.0, npm 11.6.2.
- Core schemas, immutable versioned source import, validated JSONL case/trace import,
  audited optimistic review, frozen datasets, metric prerequisites and scoring implemented.
- Original 16-document fictional policy corpus and 40 scenario fixtures implemented;
  20 calibration and 20 held-out cases grouped by topic. No independent human review claimed.
- CLI vertical slice completed; all five fault modes exercised with clean baseline.
- Persistent atomic worker with cancellation, leases, owner fencing and unique result
  finalization implemented. API added for the full workflow, evidence and JSONL export.
- Git checkpoint `f3a5b2c`: core, API and worker milestone committed; supplied
  untracked brief left untouched.
- Git checkpoint `8477c71`: review/recovery hardening, fixed fixtures and provider tests.
- Git checkpoint `0806e5a`: dashboard implementation.
- Git checkpoint `0257121`: real browser workflows and screenshots.
- Git checkpoint `d08086e`: Python and browser CI definitions.
- Git checkpoint `ab79300`: release documentation and measured delivery evidence.
- React/TypeScript dashboard implemented: applications/imports, review/edit/audit,
  publication, bounded jobs, per-dimension coverage, evidence and comparison.
- Fixed 40-case JSONL suite shipped separately from runtime generation.
- Paid provider routes/adapters remain unavailable. Budgeted interfaces tested with
  a deterministic no-network fake, including evidence validation and failures.
- Actual worker kill/restart and stale-owner fencing checks pass.
- Locked setup, Python wheel, CI definitions, README, schema/measurement docs,
  attribution, screenshots and machine-readable release evidence completed.

## Validation

- `git status --short`: initial state contained only the untracked build brief.
- `python --version; node --version; npm --version`: passed.
- `python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e '.[dev]'`: passed.
- `.\.venv\Scripts\python.exe -m pytest -q`: **15 passed** (core milestone).
- API milestone: **17 passed**, with one upstream Starlette/httpx deprecation warning.
- `npm install` in `web`: passed, 0 vulnerabilities reported.
- `npm run build` in `web`: TypeScript and production bundle passed; removed an
  empty CSS import that caused a warning on the initial build.
- `npx playwright install chromium`: passed.
- Final `.\.venv\Scripts\python.exe -m pytest -q`: **27 passed** in 17.03 seconds;
  one upstream Starlette/httpx deprecation warning remains.
- Final `npm run test:e2e` in `web`: **3 passed** in 22.4 seconds. Real API and
  separate worker: manual imports/telemetry/download, demo review/run/comparison/
  persistence, UTF-8 import and mobile empty states. Failures found earlier were fixed.
- Final `npm run build`: passed. API static index/JavaScript asset/health all returned 200.
- `.\.venv\Scripts\python.exe -m pip check`: passed, also in the fresh install.
- `python -m venv data\clean-env`, install `requirements.lock`, install editable
  package with `--no-deps`, CLI demo against `data/clean-setup.db`: all passed.
- `.\.venv\Scripts\python.exe -m pip wheel --no-deps . --wheel-dir data\dist`:
  passed. Wheel contains core, 16 policies, 40 fixtures and the root license.
- Installed the built wheel into `data/clean-env` and ran six more complete
  demo runs against `data/wheel-demo.db`; comparison matched 20 cases.
- `.\.venv\Scripts\python.exe scripts\verify_demo.py`: six runs passed;
  per-fault results and denominators saved in `docs/release-evidence.json`.
- `.\.venv\Scripts\python.exe -m compileall -q src scripts` and `git diff --check`: passed.
- Post-release GIF capture: `node web/scripts/capture-demo.mjs` passed against an
  isolated real API/worker/browser. Eleven states encoded into a looping 1280 × 900
  GIF: 23.2 seconds, 489,817 bytes. Source review, approvals, publication, both runs,
  comparison and highlighted evidence assertions passed; no browser errors.
- Optional media setup `pip install -r scripts/requirements-media.txt`,
  `node --check web/scripts/capture-demo.mjs`, encoder compilation, decoded-frame/
  timing/size validation and `git diff --check` passed. Media dependency is separate
  from runtime requirements. Review/evidence capture frames inspected visually.
- First GitHub Actions run **passed** on Ubuntu: Python 3.11 core, Python 3.13
  core, Chromium browser workflow and artifact upload. Verified commit `ab79300`;
  run https://github.com/rahbarahsan/governloom/actions/runs/37562245561.
- Six focused delivery commits pushed to `origin/main`, followed by a documentation
  checkpoint for the passing remote CI and README badge. No history rewritten.
- `.\.venv\Scripts\python.exe -m governloom.cli --db sqlite:///data/vertical-slice.db demo`:
  six completed runs, 20 cases each. Findings: clean 0, irrelevant retrieval 20,
  outdated source 20, unsupported statement 0 (documented blind spot), invalid
  citation 10, timeout 20. Compatible comparison on 20 matched cases passed.

## Next executable step

2026-10-07: after the user challenged the synthetic demo's realism, they authorized
using their existing OpenAI subscription instead of sharing an API key. The
installed Codex CLI reports ChatGPT authentication. Added an opt-in local
subscription transport and `scripts/run_subscription_eval.py`: four natural
questions using two existing policies, observed trace import/worker evaluation,
two explicitly synthetic unsupported additions, and four separate claim judgments.
The answer prompt excludes reference answers and expected labels. Captures keep
model selector, CLI version, prompt/rubric versions, source/dataset hashes,
exact responses, evidence and usage. No auth token file is read/copied/published.

The first attempt rejected unsupported built-in provider retry configuration
before inference. Removed that configuration and preserved the failed capture
in ignored `data/subscription-2026-10-07/`. A fresh invocation completed all
eight real turns in `data/subscription-2026-10-07-b/`; the isolated database is
`workbench.db`. Published the non-secret report in
`docs/experiments/subscription-2026-10-07.json`. Reproduce with:

`.\.venv\Scripts\python.exe scripts/run_subscription_eval.py --allow-subscription --model gpt-6.1-sol --max-requests 8 --timeout-seconds 180 --output data/new-subscription-capture`

Results: 4/4 response behaviors match authored fixtures; both paraphrased answers
fail literal agreement while citation checks pass. Separate real judge turns
mark both original factual claims supported and both appended claims unsupported,
with exact source passage validation. Existing deterministic checks do not
distinguish the additions. Comparison is compatible on four matched cases.
Human calibration, immutable backend model snapshot and subscription monetary
cost remain unavailable. Fictional corpus and four exploratory cases do not
establish real-world evaluation reliability. Dashboard semantic metric stays
unavailable; estimates remain in the report. See `docs/SUBSCRIPTION_EVAL.md`.

New tests cover API-key rejection/removal, request limits, durable errors,
deadline termination, attempted tool use, forged judge quotes, and real-workflow
trace import with a no-network fake. **34 backend tests pass** (23.19 seconds);
web production build, compilation, pip check and diff check pass. **3 browser
workflows pass** (29.3 seconds). Script starts no servers; normal API/worker/tests make no
subscription calls. Transport reservations count CLI invocations, not internal
HTTP retries; the CLI can retry transport within the fixed deadline.

Checkpoint `67ae6b9` commits capture transport, experiment script and tests.
The recorded report was independently re-read to verify eight completed turns,
both completed four-case runs, frozen dataset checksum and exact judge evidence.
Test-created screenshot changes were discarded. Process and listener checks
confirm no remaining capture, API, worker or dashboard server. Documentation
and the non-secret recorded experiment form a separate delivery checkpoint.

Next work: blinded independent label export/import and adjudication, then
dashboard claim-evidence integration with explicit uncalibrated states and
a larger second application. Do not treat model estimates as human labels.

Post-release presentation: a real 23.2-second demo GIF (11 frames, 489,817 bytes)
is added to the README with a still preview and reproducible capture scripts.
Capture verifies the review/publish/clean/faulty/compare/evidence workflow and
decoded animation frames. It uses an isolated database and no paid provider.

The recommended v0.2 scope is now recorded in `docs/ROADMAP.md`: claim-level
grounding, independently reviewed calibration, a second application/corpus,
and a local launcher/finding filters. The subscription experiment above is
the first implemented slice; the remaining scope is proposed. Continue with
blinded label export/import and a calibration report; no real-model quality
claim without actual independent labels.

First-release delivery is complete. Follow README setup to run it. If changing
code, run the backend suite, web build, and browser suite before updating evidence:
`.\.venv\Scripts\python.exe -m pytest -q`, `npm --prefix web run build`,
`npm --prefix web run test:e2e`. `docs/VALIDATION.md` records exact release results.

The next optional expansion is independent review/calibration and a second
application/corpus. It requires new evidence and, for paid providers, explicit
configuration and spending authorization. No automatic restart is configured.

The user authorized pushing the focused delivery commits to `origin/main`.
Use `git status -sb` to inspect remote synchronization if resuming. No force-push,
deployment, or paid API provider work is authorized. Local subscription inference
is authorized as described above. The supplied brief remains an
untracked user file and is deliberately excluded from delivery commits.

## Current blockers and scope limits

None for the completed local three-application delivery sequence. No participating
team is required to reproduce it. Persistent event delivery, authenticated roles,
customer-specific retention and domain calibration remain future work; the
current checkpoint establishes measured integration behavior, not a production
SLA or regulatory certification. Independent human calibration is unavailable.
The legacy citation-membership/extra-claim blind spot is still explicit. No
paid API usage, external recipients or deployment occurred.
