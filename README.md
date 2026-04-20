# fluffy.toothpaste

Multi-monitor desktop background manager. Set different wallpapers per monitor or stitch one image across all screens.

![Screenshot](screenshot.png)

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)

## Usage

```bash
make          # show available commands
make install  # sync dependencies
make run      # run the app
make test     # run tests
make lint     # check for lint errors
make fix      # auto-fix lint errors
make format   # format source code
make check    # lint + test (CI gate)
make clean    # remove cache artifacts
```

## Building a release bundle

Development dependencies (including PyInstaller) are installed with the default `uv sync`, which pulls in the dev group.

**PyInstaller onedir** (standalone directory under `dist/fluffy-toothpaste/`):

```bash
make install   # or: uv sync --locked
make dist
```

The main executable is `dist/fluffy-toothpaste/fluffy-toothpaste`. You can run it directly from that folder.

**Debian package** (`.deb` for installation on Debian/Ubuntu):

- Requires a Linux host with `dpkg-deb` (install the `dpkg` package if it is missing).

```bash
make deb
```

This runs `packaging/build-deb.sh`: it syncs the lockfile, invokes PyInstaller using `packaging/fluffy.toothpaste.spec`, stages files under the [Filesystem Hierarchy Standard](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html), and builds the package with `dpkg-deb`. The artifact is written to:

`dist/fluffy-toothpaste_<version>_<arch>.deb` (for example `dist/fluffy-toothpaste_0.1.0_amd64.deb`).

Install locally:

```bash
sudo apt install ./dist/fluffy-toothpaste_*_amd64.deb
```

`make clean` removes `build/`, `dist/`, and `.deb-staging/` from local builds.
