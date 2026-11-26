#!/bin/sh
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# Downloads one tool of a release of another project and stops unless its SHA-256 is the pinned one. Used by the workflows (only actions of GitHub itself are allowed, so no third-party action installs them).
#   sh tools/fetch_pinned.sh cosign|osv-scanner|scorecard DIRECTORY
set -eu
tool="$1"
dest="$2"
mkdir -p "$dest"
case "$tool" in
  cosign)
    url="https://github.com/sigstore/cosign/releases/download/v3.1.6/cosign-linux-amd64"
    sha="318a99ade4156a0c4113aa983b46c0a0830fa7896a096c63121ee47b610a94c6"
    ;;
  osv-scanner)
    url="https://github.com/google/osv-scanner/releases/download/v2.7.1/osv-scanner_linux_amd64"
    sha="fb7dab19a8bd9bbe5c3189f09d4b7ee1820c9553a23bac202648a56efd2f6ee8"
    ;;
  scorecard)
    url="https://github.com/ossf/scorecard/releases/download/v5.7.0/scorecard_5.7.0_linux_amd64.tar.gz"
    sha="3b08ec0a8681806c3e744ec9210742a502c7d66f06f25523b70f7128738235d3"
    ;;
  *)
    echo "unknown tool: $tool" >&2
    exit 2
    ;;
esac
file="$dest/download"
curl -fsSL --retry 3 -o "$file" "$url"
echo "$sha  $file" | sha256sum -c -
case "$url" in
  *.tar.gz) tar -xzf "$file" -C "$dest" "$tool" && rm -f "$file" ;;
  *) mv "$file" "$dest/$tool" ;;
esac
chmod +x "$dest/$tool"
