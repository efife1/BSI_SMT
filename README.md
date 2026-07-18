# BSI SMT GitHub release script

Place `release.sh` in the root of the BSI SMT repository, beside `VERSION`, `Dockerfile`, and `docker-compose.yml`.

Make it executable:

```bash
chmod +x release.sh
```

Publish the current version:

```bash
./release.sh
```

Publish and create a version tag:

```bash
./release.sh --tag
```

The script reads the release number from `VERSION`, validates the project, checks shell and Python syntax, stages and commits changes, pushes `main`, and optionally creates a matching Git tag.
