# Manual Release UI Fallback

Use this when `gh` CLI is unavailable.

## Steps

1. Ensure tag exists on remote:
```bash
git tag -a v0.1.2 -m "Release v0.1.2"
git push origin v0.1.2
```

2. Open:
`https://github.com/<owner>/<repo>/releases/new?tag=v0.1.2`

3. Fill:
- Release title: `v0.1.2`
- Release notes: short summary + install steps

4. Upload plugin ZIP from:
`ide-context/jetbrains-plugin/build/distributions/`

5. Click `Publish release`.
