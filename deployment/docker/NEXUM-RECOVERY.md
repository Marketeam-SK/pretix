# NEXUM Pretix release and recovery

The source of truth is the `Marketeam-SK/pretix` repository. Railway runs a tested image by immutable digest. A GitHub commit alone does not change production. Keep the tested source commit, published image digest and prior successful Railway deployment together in the release record. Keep registry credentials and production configuration in Railway.

## What must survive a rebuild

- The organization overview shows paid admissions on standalone events and the three nearest active series dates. It uses the event timezone and checks permission to view orders per event. Pending and test orders, canceled admissions and non-admission products are excluded.
- The Latino reporting rules live in `src/pretix/control/nexum_reporting.py` and the event and date-list views and templates. The standard Latino view omits the original dates whose events now have standalone shops. Its history view and explicit date selection retain access to the original records.
- The `pretix_nexum_summary` plugin lives in `deployment/docker/pretix-nexum-summary`. The Docker build installs it. The restored Pretix database must retain its enabled state on the standalone New Year event. The plugin combines original and standalone New Year sales when the user has order access to both events. The organization overview shows the standalone event's own sales.
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
