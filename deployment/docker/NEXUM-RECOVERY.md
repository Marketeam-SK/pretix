# NEXUM Pretix release and recovery

The source of truth is the `Marketeam-SK/pretix` repository. Railway runs a tested image by immutable digest. A GitHub commit alone does not change production. Keep the tested source commit, published image digest and prior successful Railway deployment together in the release record. Keep registry credentials and production configuration in Railway.

## What must survive a rebuild

- The NEXUM organization overview shows paid admissions, configured capacity and the value of paid tickets for standalone events and the three nearest active dates of each series. Rows are ordered by their next active start time, with events without an upcoming start below them. The overview uses the event timezone and checks permission to view orders per event. The value is the sum of individual ticket prices before partial refunds. Pending and test orders, canceled admissions, fees and non-admission products are excluded. Capacity comes from a shared admission quota for the event or date. If the quotas do not identify a single total, the overview displays a dash.
- The Latino reporting rules live in `src/pretix/control/nexum_reporting.py` and the event and date-list views and templates. The standard Latino view omits the original dates whose events now have standalone shops. Its history view and explicit date selection retain access to the original records.
- The `pretix_nexum_summary` plugin lives in `deployment/docker/pretix-nexum-summary`. The Docker build installs it. The restored Pretix database must retain its enabled state on the standalone New Year event. Both the event dashboard and organization overview combine original and standalone New Year sales when the user has order access to both events. For that combined view, the original four reserved seats are added to the standalone quota of 146.
- The main Dockerfile pins the Python base and the Passbook source revision. The Python dependency list comes from the production-equivalent build. Passbook is pulled from `Marketeam-SK/pretix-passbook` at `48d5dfca47976b730dd279504abf9753f23cc1d3`, with its repository tracked independently.

## Verify and release

Install Pretix's development dependencies and the local plugin in an isolated virtual environment. Run the tests against a synthetic database.

```sh
python -m pip install -e '.[dev]' -e deployment/docker/pretix-nexum-summary
cd src
PRETIX_CONFIG_FILE=/dev/null PRETIX_DATABASE_BACKEND=sqlite3 PRETIX_DATABASE_NAME=:memory: \
    PYTHONPATH=../deployment/docker/tests python -m pytest -c setup.cfg --ds=nexum_test_settings \
    tests/control/test_organizer.py ../deployment/docker/tests
```

For an additive release, build on the active image by digest and verify the changed code and templates against the source commit. Compile any updated translation catalogs into the image. For a full rebuild, start at the recorded GitHub commit and run `docker build --platform linux/amd64 -t nexum-pretix:recovery .` at the repository root. The checked-in versions preserve the known Python and plugin dependencies. A full rebuild can still produce a different digest because it also installs system packages. Verify the resulting image before publishing it.

Use a synthetic smoke environment to check the organizer table, the default and historical Latino date lists, the New Year joint summary and the public ticket shop. Publish the checked image to the existing private registry and verify its remote digest. In Railway change the existing Pretix service image to that digest and verify that it becomes the active deployment. Reload the four screens on the production site. Record the verified digest and rollback target after the checks pass.

## Restore or roll back

The fastest restore is the recorded successful image by digest. Use Railway's rollback to the last known good deployment when available. Keep the existing service configuration, private registry access, volumes and database attached. An application rollback does not require restoring order data. If the registry image is unavailable, rebuild from the recorded source commit and repeat the synthetic checks before promoting it. For a database restore, verify the New Year plugin is enabled for the intended event after recovery.

## Verified release on 2026-11-19

- Application change: `8151ee1039d7679de3b824ecf5ce3cf97a223244`. Complete source and full rebuild recipe: `176d873` and successors.
- Active image: `docker.io/maroszitny/nexum-pretix-summary@sha256:1e6ef0c0630f743fa029cc081a0c40ef811aa52cfa1115267535cea3125604f0`. The release preserved all layers of the previous image and updated the organizer view, template and Slovak translation. It did not require a database migration.
- Previous verified image: `docker.io/maroszitny/nexum-pretix-summary@sha256:147712107fb102562ab3ec57d2830f9ab518476de9586628c364d6cd45574f85`.
- Tests: 32 source integration tests, a complete Linux/amd64 rebuild from the tracked Dockerfile, and an isolated HTTP smoke test on the exact release image with PostgreSQL and Redis. Production verification covered the organizer table, the Latino dashboard and date history, the joint New Year sales panel, and the public shops.

## Capacity and value update on 2026-11-19

- Source: `a19af1932d80e5698ffdec0e058eb5138c333610`.
- Active image: `docker.io/maroszitny/nexum-pretix-summary@sha256:bc26a0304802ea19a4368a537ef6416bfa8cf278fca3eedb7b9847de185727a0`.
- Previous image for rollback: `docker.io/maroszitny/nexum-pretix-summary@sha256:1e6ef0c0630f743fa029cc081a0c40ef811aa52cfa1115267535cea3125604f0`.
- The image updates the organizer view, template, Slovak catalog, capacity helper, core plugin signal and the installed New Year plugin's policy and handlers. No database migration is required.
- Verified with 35 source integration tests and isolated HTTP checks with PostgreSQL and Redis. The live organizer result matched the existing New Year combined report, including its historical sales.

## Chronological overview update on 2026-11-19

- Source: `fcec5d78c23e20916926aec07ae70b51429f2ad4`.
- Active image: `docker.io/maroszitny/nexum-pretix-summary@sha256:6c39b05be939a4d0371b9be56ed053e8f6f4a58d3b6bd2ac48f6014114ba17d3`.
- Previous image for rollback: `docker.io/maroszitny/nexum-pretix-summary@sha256:bc26a0304802ea19a4368a537ef6416bfa8cf278fca3eedb7b9847de185727a0`.
- The image updates the organizer view, template and Slovak catalog. The ordering and compact adjacent sales columns passed 35 source tests, isolated Linux/amd64 HTTP checks with PostgreSQL, and a visual check of the live administrator overview.
