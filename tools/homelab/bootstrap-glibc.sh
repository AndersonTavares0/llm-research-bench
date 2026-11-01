#!/usr/bin/env bash
# Populate <study>/workspace/glibc with the container host's C library so the
# sandbox (Debian 12, glibc 2.36) can run current llama.cpp builds (need >= 2.38).
# Run as root on the gpu-lab container host, once per study:
#   bash bootstrap-glibc.sh [study-dir]
set -euo pipefail

STUDY="${1:-/srv/gpu-lab-data/users/ander}"
DEST="$STUDY/workspace/glibc"
LIBS=(
  ld-linux-x86-64.so.2
  libc.so.6 libm.so.6 libpthread.so.0 libdl.so.2 librt.so.1
  libstdc++.so.6 libgcc_s.so.1 libgomp.so.1
  libz.so.1 libzstd.so.1 libssl.so.3 libcrypto.so.3
)

mkdir -p "$DEST"
for lib in "${LIBS[@]}"; do
  src="$(ldconfig -p | awk -v n="$lib" '$1 == n { print $NF; exit }')"
  if [ -z "$src" ]; then
    echo "skipping $lib (not in this libc)" >&2
    continue
  fi
  cp -Lf "$src" "$DEST/$lib"
done
chown 1004:1004 "$DEST"/*
echo "glibc bundle: $(find "$DEST" -maxdepth 1 -type f | wc -l) libs in $DEST"
