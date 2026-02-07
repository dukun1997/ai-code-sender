#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Publish a built JetBrains plugin ZIP to GitHub Release.

Usage:
  release_jetbrains_plugin.sh [options]

Auto defaults:
  --version <value>     Optional. If omitted, infer latest semver and bump patch (+1)
  --zip <path>          Optional. If omitted, pick newest .zip from default directory

Optional:
  --repo <owner/repo>   GitHub repo (default: parsed from git origin)
  --title <text>        Release title (default: tag)
  --notes <text>        Release notes text
  --notes-file <path>   Release notes file path
  -h, --help            Show help
EOF
}

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Command not found: $1"
}

DEFAULT_ZIP_DIR="/Users/dukun/code/tool/ai-code-sender/ide-context/jetbrains-plugin/build/distributions"

normalize_tag() {
  local v="$1"
  if [[ "$v" == v* ]]; then
    echo "$v"
  else
    echo "v$v"
  fi
}

parse_repo_from_origin() {
  local remote
  local owner
  local rest
  local repo
  remote="$(git config --get remote.origin.url || true)"
  [[ -n "$remote" ]] || return 1

  case "$remote" in
    git@github.com:*)
      remote="${remote#git@github.com:}"
      ;;
    https://github.com/*)
      remote="${remote#https://github.com/}"
      ;;
    http://github.com/*)
      remote="${remote#http://github.com/}"
      ;;
    ssh://git@github.com/*)
      remote="${remote#ssh://git@github.com/}"
      ;;
    *)
      return 1
      ;;
  esac

  remote="${remote%.git}"
  remote="${remote#/}"
  remote="${remote%/}"
  [[ "$remote" == */* ]] || return 1

  owner="${remote%%/*}"
  rest="${remote#*/}"
  repo="${rest%%/*}"
  [[ -n "$owner" && -n "$repo" ]] || return 1
  echo "$owner/$repo"
}

strip_v_prefix() {
  local v="$1"
  echo "${v#v}"
}

is_semver() {
  [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

semver_gt() {
  local a="$1"
  local b="$2"
  local a1 a2 a3 b1 b2 b3

  IFS='.' read -r a1 a2 a3 <<< "$a"
  IFS='.' read -r b1 b2 b3 <<< "$b"

  if (( a1 > b1 )); then
    return 0
  fi
  if (( a1 < b1 )); then
    return 1
  fi
  if (( a2 > b2 )); then
    return 0
  fi
  if (( a2 < b2 )); then
    return 1
  fi
  (( a3 > b3 ))
}

bump_patch() {
  local version="$1"
  local major minor patch
  IFS='.' read -r major minor patch <<< "$version"
  echo "$major.$minor.$((patch + 1))"
}

infer_latest_zip() {
  local candidates=()
  local latest=""
  local latest_mtime=0
  local file
  local mtime

  shopt -s nullglob
  candidates=("$DEFAULT_ZIP_DIR"/*.zip)
  shopt -u nullglob

  [[ ${#candidates[@]} -gt 0 ]] || return 1

  for file in "${candidates[@]}"; do
    mtime="$(stat -f '%m' "$file" 2>/dev/null || stat -c '%Y' "$file" 2>/dev/null || echo 0)"
    if [[ "$mtime" -gt "$latest_mtime" ]]; then
      latest_mtime="$mtime"
      latest="$file"
    fi
  done

  [[ -n "$latest" ]] || return 1
  echo "$latest"
}

infer_next_version() {
  local best=""
  local tag
  local ref
  local remote_tags
  local version
  local zip_file
  local zip_files=()

  while IFS= read -r tag; do
    version="$(strip_v_prefix "$tag")"
    if is_semver "$version"; then
      if [[ -z "$best" ]] || semver_gt "$version" "$best"; then
        best="$version"
      fi
    fi
  done < <(git tag --list)

  remote_tags="$(git ls-remote --tags origin 2>/dev/null || true)"
  while read -r _ ref; do
    [[ -n "${ref:-}" ]] || continue
    tag="${ref#refs/tags/}"
    tag="${tag%\^\{\}}"
    version="$(strip_v_prefix "$tag")"
    if is_semver "$version"; then
      if [[ -z "$best" ]] || semver_gt "$version" "$best"; then
        best="$version"
      fi
    fi
  done <<< "$remote_tags"

  shopt -s nullglob
  zip_files=("$DEFAULT_ZIP_DIR"/*.zip)
  shopt -u nullglob

  for zip_file in "${zip_files[@]}"; do
    if [[ "$(basename "$zip_file")" =~ ([0-9]+\.[0-9]+\.[0-9]+)\.zip$ ]]; then
      version="${BASH_REMATCH[1]}"
      if [[ -z "$best" ]] || semver_gt "$version" "$best"; then
        best="$version"
      fi
    fi
  done

  [[ -n "$best" ]] || return 1
  bump_patch "$best"
}

VERSION=""
ZIP_PATH=""
REPO=""
TITLE=""
NOTES=""
NOTES_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="${2:-}"; shift 2 ;;
    --zip)
      ZIP_PATH="${2:-}"; shift 2 ;;
    --repo)
      REPO="${2:-}"; shift 2 ;;
    --title)
      TITLE="${2:-}"; shift 2 ;;
    --notes)
      NOTES="${2:-}"; shift 2 ;;
    --notes-file)
      NOTES_FILE="${2:-}"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      die "Unknown argument: $1" ;;
  esac
done

[[ -z "$NOTES" || -z "$NOTES_FILE" ]] || die "Use either --notes or --notes-file, not both"
[[ -z "$NOTES_FILE" || -f "$NOTES_FILE" ]] || die "Notes file not found: $NOTES_FILE"

require_cmd git
require_cmd gh

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Must run inside a git repository"
gh auth status >/dev/null 2>&1 || die "GitHub CLI not authenticated. Run: gh auth login"

if [[ -z "$ZIP_PATH" ]]; then
  ZIP_PATH="$(infer_latest_zip || true)"
  [[ -n "$ZIP_PATH" ]] || die "--zip not provided and no .zip found in $DEFAULT_ZIP_DIR"
  echo "[INFO] Auto-selected ZIP: $ZIP_PATH"
fi
[[ -f "$ZIP_PATH" ]] || die "ZIP file not found: $ZIP_PATH"

if [[ -z "$VERSION" ]]; then
  VERSION="$(infer_next_version || true)"
  [[ -n "$VERSION" ]] || die "--version not provided and unable to infer next version from tags/zip files"
  echo "[INFO] Auto-inferred version: $VERSION"
fi

TAG="$(normalize_tag "$VERSION")"

if [[ -z "$REPO" ]]; then
  REPO="$(parse_repo_from_origin || true)"
fi
[[ -n "$REPO" ]] || die "Unable to infer --repo from origin. Please pass --repo owner/repo"

if ! git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1; then
  git tag -a "$TAG" -m "Release $TAG"
  echo "[INFO] Created local tag $TAG"
else
  echo "[INFO] Local tag already exists: $TAG"
fi

if ! git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1; then
  git push origin "$TAG"
  echo "[INFO] Pushed tag to origin: $TAG"
else
  echo "[INFO] Remote tag already exists on origin: $TAG"
fi

if [[ -z "$TITLE" ]]; then
  TITLE="$TAG"
fi

if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  echo "[INFO] Release already exists. Uploading/replacing asset..."
  gh release upload "$TAG" "$ZIP_PATH" --repo "$REPO" --clobber
else
  echo "[INFO] Creating release $TAG in $REPO..."
  if [[ -n "$NOTES_FILE" ]]; then
    gh release create "$TAG" "$ZIP_PATH" --repo "$REPO" --title "$TITLE" --notes-file "$NOTES_FILE"
  elif [[ -n "$NOTES" ]]; then
    gh release create "$TAG" "$ZIP_PATH" --repo "$REPO" --title "$TITLE" --notes "$NOTES"
  else
    gh release create "$TAG" "$ZIP_PATH" --repo "$REPO" --title "$TITLE" --notes "Plugin release $TAG"
  fi
fi

echo "[OK] Release ready: https://github.com/$REPO/releases/tag/$TAG"
