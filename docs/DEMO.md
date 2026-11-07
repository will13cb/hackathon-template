# Demo, pitch & submission

The demo is often half the score. Freeze features **3 hours** before the deadline.

## Pitch structure (2–3 min)

| Time | Beat | Notes |
|---|---|---|
| 0:00–0:20 | **Problem** | One user, one pain point, one number if you have it. |
| 0:20–1:40 | **Live demo** | Go straight to the wow moment. Show the sponsor product working: the model call, the live URL. |
| 1:40–2:10 | **Architecture** | One slide that names the sponsor services (e.g. "Gemini 3.x on Vertex AI, Cloud Run"). |
| 2:10–2:40 | **Impact + what's next** | Who uses it, what you'd build with another week. |

Script (fill in):

```
Problem:  ___ struggle with ___ because ___.
Demo:     "Watch: I give it ___ and in ___ seconds it ___."
Arch:     "Frontend on ___, the agent runs on ___ and calls ___."
Impact:   "This saves ___ for ___. Next we'd add ___."
```

## Backup plan
- [ ] Record a 2–3 min **backup video** of the full demo (wifi and clouds fail on stage).
- [ ] Warm up the service right before presenting: `curl <url>/health` (cold starts).
- [ ] Have screenshots of the key screens in the slide deck.
- [ ] Rehearse the 2–3 min version **at least twice**, out loud, with a timer.

## Submission README outline
Replace the template README with:

1. **Name + one-line pitch**
2. **Demo:** live URL + video link + 1–2 screenshots/GIF
3. **Problem → Solution** (3–5 sentences)
4. **Sponsor services used:** a bulleted list with what each one does in the app
5. **Architecture:** diagram from `docs/architecture.md`
6. **How to run locally:** `make setup && make dev`
7. **What we built during the event** vs. what came from this template (for transparency)
8. **Team**

## Going public (submission)
- [ ] `make scan`: scan the **whole history** for secrets, not just the current files.
- [ ] **Rotate** any key that was ever committed, even briefly, even while the repo was private.
- [ ] README complete (outline above). No leftover TODOs or template text.
- [ ] LICENSE present (MIT).
- [ ] Check the event's disclosure rules for AI tools, and disclose Claude Code usage if they ask.
- [ ] Flip the repo to public, then submit the link.

## After the event
- [ ] `make teardown-gcp` / `make teardown-aws` (or delete the whole GCP project).
- [ ] Check both billing consoles for anything still running (GPU instances, NAT gateways, endpoints).
- [ ] Pin the best projects on your GitHub profile and link them from your site.
