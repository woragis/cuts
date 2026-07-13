# Worker rename map (GitHub)

Target names from the treatment pipeline plan. Local/path renames can land before GitHub renames if the PAT cannot see private `cuts-*` repos.

| Current path / remote | Target path | Target GitHub repo |
|----------------------|-------------|--------------------|
| `worker-general` / `cuts-worker-general` | `worker-control` | `cuts-worker-control` |
| `worker-treatment` / `cuts-worker-treatment` | `worker-plan` | `cuts-worker-plan` |
| `worker-render` / `cuts-worker-render` | `worker-ffmpeg` | `cuts-worker-ffmpeg` |
| `worker-notification` / `cuts-worker-notification` | `worker-notify` | `cuts-worker-notify` |
| `worker-visual` / `render-remotion` | `worker-visual` | `cuts-worker-visual` (rename from `render-remotion`) |

Keep: analyze, transcribe, audio, thumbnail, publish.

When `gh` has access to private repos (token must include private repo admin):

```bash
gh auth login -h github.com   # if `gh auth status` says token is invalid
./scripts/rename-worker-repos.sh
```

Until then, local paths already use the new names while remotes stay on the old GitHub URLs (SSH push still works to those).

**Archive unused:** only after confirming nothing still points at a remote. Example:

```bash
gh repo archive woragis/<unused-repo> --yes
```

Do not archive the five rename sources until redirects are confirmed.
