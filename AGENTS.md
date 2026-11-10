# Agent Guidelines & Development Rules for marco-silva.com

This repository contains Marco Silva's personal production website and web applications (portfolio, Wagtail CMS blog, Emojinary, and Lupus / Werewolf party game engine).

## 1. Mandatory Versioning & Changelog Protocol
Whenever implementing changes, bugfixes, or features in this repository:
1. **Bump Version Counter**:
   - Increment `VERSION_COUNTER` in `website/version.py`.
   - Update `VERSION` file in the repo root (e.g. `v114-<short-hash>` or `v114`).
2. **Update CHANGELOG.md**:
   - Document every user-facing change, fix, and new feature under the current version header in `CHANGELOG.md`.
3. **Run Automated Tests & Linting**:
   - Execute `USE_SQLITE=1 uv run pytest lupus/tests.py gamerooms/tests.py`.
   - Run `uv run ruff check lupus/ gamerooms/ templates/ website/ --ignore E501`.
   - All tests must pass with 0 errors before deployment.
4. **Deploy & Rollout Restart**:
   - Commit locally to `main`, merge to `dev`.
   - Rsync files to VM 115 (`root@192.168.1.115:/root/marco-silva.com/`), commit on VM 115, merge to `dev`.
   - Rollout restart pods on VM 115: `kubectl rollout restart deploy/django deploy/celery-worker -n marco-silva`.
5. **Record in Homelab Action Log**:
   - Immediately append an audit entry in `~/vault/40 Operations/Action Log.md` under the current date.
