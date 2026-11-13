# Translation Run & Resume Reference

_Updated 2026-11-13 (v141)._

## Quick Commands

```bash
cd ~/projects/marco-silva.com/locale

# 1. Run / resume all CSV catalogs (defaults to gemini-4-argon-medium with auto-fallback across models)
./translate_with_agy.py

# 2. Run / resume all PO catalogs across all 64 languages
./translate_with_agy.py --type po

# 3. Check live coverage across all 64 languages
python3 ../scripts/translations_tool.py status
```

## Features in `translate_with_agy.py`
- **Default model**: `gemini-4-argon-medium`
- **Automatic quota fallback**: Rotates through `gemini-4-argon-medium` → `gemini-4-argon-low` → `gemini-4-argon-high` → `gemini-4-hydrogen-medium` → `gemini-4-hydrogen-low` → `gemini-4-hydrogen-high` → `claude-sonnet-5-5-medium` → `claude-sonnet-5-5-low` → `gpt-oss-120b-medium` if any single model reaches its quota.
- **Immediate persistence**: Saves every 20-string chunk to CSV, `.po`, and `.mo` immediately.
