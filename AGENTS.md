# ThermalShift AI — Codex Project Instructions

## Mission

Build ThermalShift AI for the FortyGuard Hackathon'26.

ThermalShift is a thermal-aware workload orchestration system for distributed
AI infrastructure. It uses real FortyGuard hyperlocal ambient-temperature data
as an operational signal when deciding where and when flexible GPU workloads
should run.

The project must be practical, measurable, deployable, and suitable for a
hackathon judging demo.

## Core research question

Given the same workloads, compute capacity, eligibility constraints, release
times, runtimes, and deadlines, can a scheduler using FortyGuard-derived
ambient thermal conditions reduce modeled thermal exposure compared with
temperature-unaware baseline schedulers without degrading workload completion
or deadline satisfaction?

## Primary hackathon tracks

- Industrial & Enterprise
- Model Designing

Do not turn the project into a generic climate dashboard or chatbot.

## Winning product story

FortyGuard temperature data
-> thermal assessment
-> workload/site constraints
-> scheduling optimization
-> measurable comparison against baselines
-> clear operational recommendation

FortyGuard must remain central to the project.

## Scientific boundaries

Use careful terminology.

Allowed:
- ambient temperature
- modeled thermal stress
- modeled thermal exposure
- thermal-aware scheduling
- thermal stress-hours
- relative comparison between schedulers

Do NOT claim that outdoor ambient temperature directly measures or proves:
- GPU temperature
- server inlet temperature
- cooling energy consumption
- PUE
- water consumption
- chiller efficiency
- electricity savings
- actual facility energy savings

Those would require facility telemetry that this project does not have.

Preferred result wording:

"ThermalShift reduced modeled ambient thermal exposure by X% versus the
baseline while preserving Y% deadline satisfaction."

Only report X and Y when produced by real experiments. Never fabricate results.

## FortyGuard constraints

- API key must only come from environment variables.
- Never print, log, commit, or hard-code API keys.
- `.env` must be ignored by Git.
- Commit `.env.example` with empty values only.
- Base URL: https://api.fortyguard.com
- Main endpoint initially: POST /v1/heatmap
- Status endpoint: GET /v1/status/{activity_id}
- Treat the API as asynchronous.
- Use bounded polling with backoff.
- Cache successful results to avoid duplicate credit usage.
- Use U.S. locations only.
- For hackathon experiments, use dates from 2021-01-01 onward.
- Heatmap forecast use must not exceed the hackathon-supported future window.
- Use actual request granularity in documentation rather than claiming a finer
  output resolution than was requested.

## Initial simulated AI-compute sites

Use four U.S. locations for the main benchmark unless evidence requires a
change:

1. Northern Virginia / Ashburn, Virginia
2. Phoenix, Arizona
3. San Antonio, Texas
4. Atlanta, Georgia

Locations represent modeled AI-compute sites. Do not imply that any named
real-world data center supplied private operational telemetry.

## Core domain entities

### Site

Fields should include:
- site_id
- name
- latitude
- longitude
- timezone
- total_gpu_capacity

### Workload

Fields should include:
- workload_id
- name
- gpu_demand
- duration_hours
- release_time
- deadline
- priority
- eligible_site_ids

### Temperature observation / assessment

Preserve raw FortyGuard observations separately from derived thermal metrics.

### Schedule decision

Capture:
- workload_id
- site_id
- start_time
- end_time
- thermal_exposure
- deadline_satisfied
- capacity_satisfied
- scheduler_name
- decision_reason where appropriate

## Thermal exposure

Use an interpretable modeled metric.

Conceptually:

thermal_exposure =
sum(ThermalStress(site, time) * duration_interval)

Call its aggregate unit "thermal stress-hours" or another explicitly modeled
decision metric.

It is not a physical energy unit.

The exact ThermalStress formulation must be documented and testable. Prefer
simple, explainable models over unjustified complexity.

## Scheduling

Implement baseline schedulers before judging ThermalShift.

Minimum baselines:
- First Available
- Capacity Only

Optional if useful:
- Random with fixed deterministic seed

ThermalShift should use constraint-aware optimization.

OR-Tools is preferred if it provides a clear implementation.

Constraints should include:
- eligible site
- GPU capacity
- release time
- runtime
- deadline

Primary optimizer objective:
minimize modeled thermal exposure while satisfying operational constraints.

Do not sacrifice deadline feasibility merely to reduce thermal exposure.

## Evaluation

Use exactly the same workload scenarios and capacities across scheduler
comparisons.

Track at least:
- completed workloads
- deadline satisfaction rate
- mean modeled thermal exposure
- total modeled thermal exposure
- peak/maximum exposure where meaningful
- scheduler runtime
- infeasible workloads

Prefer historical replay across multiple dates/windows instead of choosing one
favorable temperature example.

Make experiments deterministic and reproducible.

## Architecture

Prefer a small modular Python codebase.

Suggested modules:

thermalshift/
    config.py
    models/
    fortyguard/
        client.py
        models.py
        poller.py
        service.py
        cache.py
    thermal/
        model.py
    scheduler/
        base.py
        first_available.py
        capacity.py
        optimizer.py
    benchmark/
        runner.py
        metrics.py
    api/
        app.py

tests/
examples/
docs/

Do not create modules merely to match this layout if they provide no value.

## Technology direction

Target Python 3.12.

Preferred dependencies:
- FastAPI
- HTTPX
- Pydantic / pydantic-settings
- OR-Tools
- pytest
- pytest-asyncio
- Ruff

Add dependencies only when required.

Avoid heavy agent frameworks and unnecessary infrastructure.

## Code quality

- Type public interfaces.
- Keep functions focused.
- Write docstrings for public classes/functions where useful.
- Use Pydantic for externally sourced structured data where validation helps.
- Handle API failures explicitly.
- Never silently swallow exceptions.
- Avoid broad `except Exception` unless re-raising with justified context.
- Prefer deterministic behavior in tests and benchmarks.
- Keep secrets out of output.
- Run Ruff and pytest before considering a task complete.

## Testing

Unit tests must not contact FortyGuard.

Use `httpx.MockTransport` or equivalent dependency injection for HTTP tests.

Test:
- authentication headers without exposing secrets
- successful submissions
- status parsing
- HTTP failures
- malformed responses
- polling completion
- polling failure
- polling timeout
- thermal model boundaries
- scheduling feasibility
- optimizer correctness
- benchmark reproducibility

Real FortyGuard requests belong only in explicit smoke/integration scripts and
must never run automatically during pytest.

## Security

`.gitignore` must exclude:
- .env
- virtual environments
- caches
- Python build metadata
- locally cached FortyGuard API responses if they contain anything unsuitable
  for publication

Never expose credentials in source, tests, examples, logs, screenshots, or
documentation.

## Hackathon scope

Prioritize, in this order:

1. Correct FortyGuard integration
2. Reproducible temperature dataset/cache
3. Thermal stress model
4. Workload/site models
5. Baseline schedulers
6. ThermalShift optimizer
7. Benchmark evidence
8. Live API/demo
9. README and methodology
10. Deployment and demo video

Do not spend core build time on:
- LLM chatbot
- Kubernetes integration
- live GPU cluster integration
- BMS/SCADA integration
- user authentication
- billing
- mobile app
- elaborate microservices
- an Agentic AI feature unless the core submission is already complete

## Submission quality

The final repository should support:
- a working live demo
- reproducible local setup
- public/judge-accessible GitHub repository
- clear README
- architecture/methodology explanation
- benchmark results
- approximately 3-minute demo video
- <=500-word submission summary

Tell the story as:

problem
-> user
-> FortyGuard usage
-> decision model
-> measured result

## Working style for Codex

Before making substantial changes:
1. inspect the repository
2. state the smallest coherent implementation plan
3. implement only that scope
4. run relevant tests and Ruff
5. summarize changed files and test results

Do not rewrite unrelated files.

Do not create speculative features.

Do not fabricate API response schemas. When an undocumented FortyGuard field is
needed, stop and request a real sample or current documentation.

Do not commit or push unless explicitly instructed.

The goal is a strong, simple, tested hackathon product rather than maximum
feature count.
