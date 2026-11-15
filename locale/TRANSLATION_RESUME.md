# Translation Run & Resume Reference

_Updated 2026-11-15 with credit-optimized `agy` settings (`gemini-3.8-flash-low`, `--effort low`, 6-language batching, local prefill, and cognate tracking) across 578 total discovered strings._

## Recommended Model & Credit-Saving Configuration

- **Best Primary Model**: `gemini-3.8-flash-low` (`--effort low`) — short-window rolling Flash quota, zero wasted reasoning tokens, ideal for JSON UI translation.
- **Secondary Fallback**: `gemini-4-hydrogen-low` (`--effort low`) — shares short-window rolling quota; fallback chain stops at `gemini-4-argon-low` (never escalates to `claude-*`, `gpt-oss-120b-medium`, or `argon-high`).
- **Zero-Credit Local Prefill**: Run `python3 ../scripts/translations_tool.py prefill` (also automatic in `translate_with_agy.py`) before spending credits.
- **Multi-Language Batching**: Default `--langs-per-call 6` translates 6 languages in a single prompt; default `--tier priority` targets the 22 primary languages (use `--tier core` for the 12 main site/game languages, or `--tier all` for all 63).

## Language Coverage Snapshot (578 Total Strings)

| Code | Language | Translated | Missing | Coverage | Status |
|---|---|---|---|---|---|
| `en` | 🇬🇧 English | 578 | 0 | **100.0%** | Source |
| `es` | 🇪🇸 Spanish | 376 | 202 | **65.1%** | Batch 1 + New Strings Left |
| `fr` | 🇫🇷 French | 376 | 202 | **65.1%** | Batch 1 + New Strings Left |
| `it` | 🇮🇹 Italian | 376 | 202 | **65.1%** | Batch 1 + New Strings Left |
| `ru` | 🇷🇺 Russian | 376 | 202 | **65.1%** | Batch 1 + New Strings Left |
| `pt` | 🇵🇹 Portuguese | 375 | 203 | **64.9%** | Batch 1 + New Strings Left |
| `az` | 🇦🇿 Azerbaijani | 372 | 206 | **64.4%** | Batch 1 + New Strings Left |
| `fi` | 🇫🇮 Finnish | 372 | 206 | **64.4%** | Batch 1 + New Strings Left |
| `pl` | 🇵🇱 Polish | 372 | 206 | **64.4%** | Batch 1 + New Strings Left |
| `sv` | 🇸🇪 Swedish | 372 | 206 | **64.4%** | Batch 1 + New Strings Left |
| `sw` | 🏴 Swahili | 372 | 206 | **64.4%** | Batch 1 + New Strings Left |
| `el` | 🇬🇷 Greek | 341 | 237 | **59.0%** | Near-Complete |
| `hi` | 🇮🇳 Hindi | 341 | 237 | **59.0%** | Near-Complete |
| `kn` | 🇮🇳 Kannada | 341 | 237 | **59.0%** | Near-Complete |
| `ar` | 🇸🇦 Arabic | 340 | 238 | **58.8%** | Near-Complete |
| `fa` | 🇮🇷 Persian | 339 | 239 | **58.7%** | Near-Complete |
| `sq` | 🇦🇱 Albanian | 331 | 247 | **57.3%** | Near-Complete |
| `bn` | 🇧🇩 Bengali | 330 | 248 | **57.1%** | Near-Complete |
| `eu` | 🏴 Basque | 330 | 248 | **57.1%** | Near-Complete |
| `af` | 🇿🇦 Afrikaans | 327 | 251 | **56.6%** | Near-Complete |
| `be` | 🇧🇾 Belarusian | 149 | 429 | **25.8%** | Partial |
| `ur` | 🇵🇰 Urdu | 143 | 435 | **24.7%** | Partial |
| Others (42 langs) | `de`, `nl`, `ja`, `ko`, `zh-*`, etc. | 22–38 | 540–556 | 3.8%–6.6% | Cleaned + Prefilled |

## How to Run / Resume (Credit-Optimized)

```bash
cd ~/projects/marco-silva.com/locale

# 1. Inspect dry-run plan first (0 credits):
./translate_with_agy.py --dry-run

# 2. Top up core 12 site/game languages (batched 6-at-a-time on gemini-3.8-flash-low):
./translate_with_agy.py --tier core

# 3. Top up all 22 priority languages (default):
./translate_with_agy.py

# 4. Run explicit subset:
./translate_with_agy.py --lang de nl ja ko zh-cn zh-tw

# 5. Pre-fill local variants/cognates with 0 LLM credits & check status anytime:
python3 ../scripts/translations_tool.py prefill
python3 ../scripts/translations_tool.py status
```
