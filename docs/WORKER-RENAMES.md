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

When `gh` has access to private repos:

```bash
gh repo rename cuts-worker-control --repo woragis/cuts-worker-general
# then update .gitmodules urls and git remote set-url
```

Until then, paths may already use new names while remotes stay on old URLs.
