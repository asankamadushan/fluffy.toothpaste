#!/usr/bin/env bash
# Assemble a .deb from the PyInstaller onedir bundle (FHS layout).
# Requires: uv, dpkg-deb (package dpkg on Debian/Ubuntu).
# PyInstaller 6.15+ supports Python 3.14; this project uses 3.14+.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

uv sync --locked --all-groups
uv run pyinstaller packaging/fluffy.toothpaste.spec --noconfirm

VERSION="$(uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")"

if command -v dpkg-architecture >/dev/null 2>&1; then
  ARCH="$(dpkg-architecture -qDEB_BUILD_ARCH)"
else
  case "$(uname -m)" in
    x86_64) ARCH=amd64 ;;
    aarch64) ARCH=arm64 ;;
    *) ARCH="$(uname -m)" ;;
  esac
fi

STAGING="${ROOT}/.deb-staging"
rm -rf "$STAGING"
mkdir -p "${STAGING}/DEBIAN"
mkdir -p "${STAGING}/usr/lib/fluffy-toothpaste"
mkdir -p "${STAGING}/usr/bin"
mkdir -p "${STAGING}/usr/share/applications"
mkdir -p "${STAGING}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${STAGING}/usr/share/doc/fluffy-toothpaste"

cp -a "${ROOT}/dist/fluffy-toothpaste/." "${STAGING}/usr/lib/fluffy-toothpaste/"

cat > "${STAGING}/usr/bin/fluffy-toothpaste" << 'EOF'
#!/bin/sh
exec /usr/lib/fluffy-toothpaste/fluffy-toothpaste "$@"
EOF
chmod 0755 "${STAGING}/usr/bin/fluffy-toothpaste"

cp "${ROOT}/packaging/desktop/fluffy-toothpaste.desktop" "${STAGING}/usr/share/applications/"
cp "${ROOT}/icon.png" "${STAGING}/usr/share/icons/hicolor/256x256/apps/fluffy-toothpaste.png"
cp "${ROOT}/packaging/copyright" "${STAGING}/usr/share/doc/fluffy-toothpaste/copyright"

INSTALLED_SIZE="$(du -sk "${STAGING}/usr" | cut -f1)"

MAINTAINER="${DEBFULLNAME:-fluffy.toothpaste maintainers} <${DEBEMAIL:-maintainers@local}>"

{
  echo "Package: fluffy-toothpaste"
  echo "Version: ${VERSION}"
  echo "Section: graphics"
  echo "Priority: optional"
  echo "Architecture: ${ARCH}"
  echo "Installed-Size: ${INSTALLED_SIZE}"
  echo "Maintainer: ${MAINTAINER}"
  echo "Depends: libc6 (>= 2.31)"
  echo "Description: Multi-monitor desktop background manager"
  echo " Set different wallpapers per monitor or stitch one image across all screens."
} > "${STAGING}/DEBIAN/control"

mkdir -p "${ROOT}/dist"
OUT="${ROOT}/dist/fluffy-toothpaste_${VERSION}_${ARCH}.deb"
dpkg-deb --root-owner-group --build "$STAGING" "$OUT"
echo "Built: ${OUT}"
