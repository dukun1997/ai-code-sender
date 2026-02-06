#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Publish a built JetBrains plugin ZIP to GitHub Release.

Usage:
  release_jetbrains_plugin.sh --version <version_or_tag> --zip <artifact.zip> [options]

Required:
  --version <value>     Version or tag (example: 0.1.2 or v0.1.2)
  --zip <path>          Path to built plugin ZIP

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
  remote="$(git config --get remote.origin.url || true)"
  [[ -n "$remote" ]] || return 1

  if [[ "$remote" =~ ^git@github\.com:([^/]+)/([^/]+?)(\.git)?$ ]]; then
    echo "${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
    return 0
  fi
  if [[ "$remote" =~ ^https://github\.com/([^/]+)/([^/]+?)(\.git)?$ ]]; then
    echo "${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
    return 0
  fi
  return 1
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

[[ -n "$VERSION" ]] || die "--version is required"
[[ -n "$ZIP_PATH" ]] || die "--zip is required"
[[ -f "$ZIP_PATH" ]] || die "ZIP file not found: $ZIP_PATH"
[[ -z "$NOTES" || -z "$NOTES_FILE" ]] || die "Use either --notes or --notes-file, not both"
[[ -z "$NOTES_FILE" || -f "$NOTES_FILE" ]] || die "Notes file not found: $NOTES_FILE"

require_cmd git
require_cmd gh

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Must run inside a git repository"
gh auth status >/dev/null 2>&1 || die "GitHub CLI not authenticated. Run: gh auth login"

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
