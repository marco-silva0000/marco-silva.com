# Translation Run & Resume Reference

_Updated 2026-11-13 after priority batch (`pt`, `ru`, `pl`, `it`, `fi`, `fr`, `sv`, `sw`, `az`, `es`) with `chunk-size=80`._

## Completed / High-Coverage Languages (20 / 64, out of 370 Total Strings)

| Code | Language | Translated | Missing | Coverage | Status |
|---|---|---|---|---|---|
| `en` | 🇬🇧 English | 370 | 0 | **100.0%** | Complete |
| `az` | 🇦🇿 Azerbaijani | 366 | 4 | **98.9%** | Complete |
| `ru` | 🇷🇺 Russian | 366 | 4 | **98.9%** | Complete |
| `fi` | 🇫🇮 Finnish | 362 | 8 | **97.8%** | Complete |
| `sw` | 🏴 Swahili | 362 | 8 | **97.8%** | Complete |
| `pl` | 🇵🇱 Polish | 361 | 9 | **97.6%** | Complete |
| `es` | 🇪🇸 Spanish | 360 | 10 | **97.3%** | Complete |
| `pt` | 🇵🇹 Portuguese | 359 | 11 | **97.0%** | Complete |
| `sv` | 🇸🇪 Swedish | 357 | 13 | **96.5%** | Complete |
| `it` | 🇮🇹 Italian | 356 | 14 | **96.2%** | Complete |
| `fr` | 🇫🇷 French | 351 | 19 | **94.9%** | Complete |
| `ar` | 🇸🇦 Arabic | 330 | 40 | **89.2%** | Near-Complete (1 chunk left) |
| `hi` | 🇮🇳 Hindi | 330 | 40 | **89.2%** | Near-Complete (1 chunk left) |
| `kn` | 🇮🇳 Kannada | 330 | 40 | **89.2%** | Near-Complete (1 chunk left) |
| `fa` | 🇮🇷 Persian | 329 | 41 | **88.9%** | Near-Complete (1 chunk left) |
| `el` | 🇬🇷 Greek | 327 | 43 | **88.4%** | Near-Complete (1 chunk left) |
| `bn` | 🇧🇩 Bengali | 324 | 46 | **87.6%** | Near-Complete (1 chunk left) |
| `eu` | 🏴 Basque | 323 | 47 | **87.3%** | Near-Complete (1 chunk left) |
| `sq` | 🇦🇱 Albanian | 320 | 50 | **86.5%** | Near-Complete (1 chunk left) |
| `af` | 🇿🇦 Afrikaans | 319 | 51 | **86.2%** | Near-Complete (1 chunk left) |
| `be` | 🇧🇾 Belarusian | 135 | 235 | **36.5%** | Partial (3 chunks left) |
| `ur` | 🇵🇰 Urdu | 127 | 243 | **34.3%** | Partial (3 chunks left) |
| Others (42 langs) | `bg`, `ca`, `de`, `ja`, `ko`, `zh-*`, etc. | ~16–23 | ~347–354 | ~4.3%–6.2% | Seeded (~5 chunks each at size 80) |

## How to Run / Resume

```bash
cd ~/projects/marco-silva.com/locale

# Run specific languages (default chunk-size is now 80):
./translate_with_agy.py --lang de ja ko zh-cn zh-tw nl da no uk tr

# Or run all remaining languages automatically:
./translate_with_agy.py

# Check live status anytime:
python3 ../scripts/translations_tool.py status
```
