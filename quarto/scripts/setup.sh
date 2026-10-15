#!/usr/bin/env bash
# One-time setup for the Quarto deck toolchain (all user-level, inside quarto/):
#   - Quarto (bundles pandoc) from its GitHub release into quarto/.dist/,
#     checked against the release's published SHA-256
#   - MathJax 3 single-file SVG bundle and the Inter / JetBrains Mono web fonts
#     into quarto/vendor/ (offline math and fonts, embed-resources exports stay
#     self-contained), checked against quarto/vendor.sha256
set -euo pipefail
Q="$(cd "$(dirname "$0")/.." && pwd)"
sha256check() { if command -v sha256sum >/dev/null; then sha256sum -c "$@"; else shasum -a 256 -c "$@"; fi >/dev/null; }  # macOS: shasum
tmps=(); trap 'rm -rf ${tmps[@]+"${tmps[@]}"}' EXIT   # (bash 3.2: empty array under set -u)
QV=1.10.18   # sums from https://github.com/quarto-dev/quarto-cli/releases/download/v1.10.18/quarto-1.10.18-checksums.txt
case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)  QA=linux-amd64 QS=afad071b5bd22c02f2d300695743189d3650e0537a53073e654b630cff2b0c73 ;;
    Linux-aarch64) QA=linux-arm64 QS=f6a07df68e25330b5df34f65d3df66bca605acce3b830c593a58e91884d4cf6c ;;
    Darwin-*)      QA=macos       QS=ddd6a71a9e0448ab15fb655bc589e11cb6589a248ec35ccd7f7f44137531688e ;;
    *) echo "ERROR: no Quarto $QV build for $(uname -sm)" >&2; exit 1 ;;
esac
if [ "$(cat "$Q/.dist/version" 2>/dev/null)" != "$QV-$QA" ]; then
    tmp="$(mktemp -d)"; tmps+=("$tmp"); tgz="$tmp/quarto.tar.gz"
    curl -fsSL -o "$tgz" "https://github.com/quarto-dev/quarto-cli/releases/download/v$QV/quarto-$QV-$QA.tar.gz"
    echo "$QS  $tgz" | sha256check -   # the published bytes, or fail
    new="$tmp/dist"; mkdir -p "$new/quarto"   # extract aside; swap in only once it worked
    case "$QA" in linux-*) tar -xzf "$tgz" -C "$new/quarto" --strip-components=1 ;; *) tar -xzf "$tgz" -C "$new/quarto" ;; esac
    [ -x "$new/quarto/bin/quarto" ] || { echo "ERROR: unexpected Quarto archive layout" >&2; exit 1; }
    echo "$QV-$QA" > "$new/version"
    [ ! -e "$Q/.dist" ] || mv "$Q/.dist" "$tmp/old-dist"
    mv "$new" "$Q/.dist"
fi
if ! (cd "$Q/vendor" 2>/dev/null && sha256check "$Q/vendor.sha256" 2>/dev/null); then
    tmp="$(mktemp -d)"; tmps+=("$tmp")
    npm --prefix "$tmp" install --silent --ignore-scripts mathjax-full@3.2.2 @fontsource-variable/inter@5.2.8 \
        @fontsource-variable/jetbrains-mono@5.2.8
    nm="$tmp/node_modules"; fs="$nm/@fontsource-variable"
    mkdir -p "$Q/vendor/mathjax" "$Q/vendor/fonts"
    cp "$nm/mathjax-full/es5/tex-svg.js" "$nm/mathjax-full/LICENSE" "$Q/vendor/mathjax/"
    cp "$fs"/inter/files/*-wght-normal.woff2 "$fs"/jetbrains-mono/files/*-wght-normal.woff2 "$Q/vendor/fonts/"
    cp "$fs/inter/LICENSE" "$Q/vendor/fonts/LICENSE-Inter.txt"
    cp "$fs/jetbrains-mono/LICENSE" "$Q/vendor/fonts/LICENSE-JetBrainsMono.txt"
    (cd "$Q/vendor" && sha256check "$Q/vendor.sha256")   # pinned bytes, or fail
fi
python3 "$Q/scripts/gen_client.py"   # deck browser layers (quarto/shim/_client.html)
"$Q/bin/quarto" --version
