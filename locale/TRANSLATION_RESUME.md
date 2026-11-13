# Translation Run & Resume Reference

_Updated 2026-11-13 (v142). Stopped cleanly at ~80% Argon credit usage._

## Current Coverage (337 Total Strings)

| Code | Language | Translated | Missing | Coverage | Status |
|---|---|---|---|---|---|
| `en` | 🇬🇧 English | 337 | 0 | **100.0%** | Complete |
| `ar` | 🇸🇦 Arabic | 336 | 1 | **99.7%** | Complete |
| `hi` | 🇮🇳 Hindi | 336 | 1 | **99.7%** | Complete |
| `kn` | 🇮🇳 Kannada | 336 | 1 | **99.7%** | Complete |
| `fa` | 🇮🇷 Persian | 335 | 2 | **99.4%** | Complete |
| `el` | 🇬🇷 Greek | 333 | 4 | **98.8%** | Complete |
| `bn` | 🇧🇩 Bengali | 330 | 7 | **97.9%** | Complete |
| `az` | 🇦🇿 Azerbaijani | 329 | 8 | **97.6%** | Complete |
| `eu` | 🏴 Basque | 329 | 8 | **97.6%** | Complete |
| `es` | 🇪🇸 Spanish | 326 | 11 | **96.7%** | Complete |
| `af` | 🇿🇦 Afrikaans | 325 | 12 | **96.4%** | Complete |
| `sq` | 🇦🇱 Albanian | 325 | 12 | **96.4%** | Complete |
| `it` | 🇮🇹 Italian | 322 | 15 | **95.5%** | Complete |
| `fr` | 🇫🇷 French | 316 | 21 | **93.8%** | Complete |
| `ru` | 🇷🇺 Russian | 264 | 73 | **78.3%** | Partial (4 chunks left) |
| `pt` | 🇵🇹 Portuguese | 259 | 78 | **76.9%** | Partial (4 chunks left) |
| `be` | 🇧🇾 Belarusian | 134 | 203 | **39.8%** | Partial (in progress when stopped) |
| `ur` | 🇵🇰 Urdu | 130 | 207 | **38.6%** | Partial (11 chunks left) |
| Others (46 langs) | `bg`, `ca`, `de`, `ja`, `ko`, `zh-*`, etc. | ~15–22 | ~315–322 | ~4.5%–6.5% | Seeded; ready for batch |

## How to Resume Later

The script automatically skips all translated strings and picks up right at `pt`, `ru`, `ur`, and `be` (in `translations_master.csv`):

```bash
cd ~/projects/marco-silva.com/locale

# Resume everything (finishes pt, ru, ur CSVs first, then continues translations_master.csv from Belarusian 'be'):
./translate_with_agy.py

# Or translate specific languages only:
./translate_with_agy.py --lang pt ru ur de ja ko zh-cn zh-tw

# Check live status anytime:
python3 ../scripts/translations_tool.py status
```
