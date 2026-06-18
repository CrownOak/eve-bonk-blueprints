# BONK Blueprint Profitability Scanner (v2, SDE-driven)

Ranks the most profitable **Tech I** items to manufacture, by **ISK per hour**, from
EVE's SDE + live Jita prices. Use the top few to decide what to train toward and mine for.
Runs monthly.

- Working dir: `C:\Users\sales\blueprint-scout`
- Repo: https://github.com/CrownOak/eve-bonk-blueprints
- **Live page: https://crownoak.github.io/eve-bonk-blueprints/** (password-protected)

## What it does
1. Builds a blueprint index from the SDE CSV dumps (manufacturing activity only) for
   Ships / Modules / Ammo / Drones, **Tech I only** (via `invMetaTypes`), cached locally.
2. Pulls live Jita prices for every product + input material (Fuzzwork market aggregates).
3. `profit = product_sell * output_qty - ME-adjusted material cost - ~5% job fee`;
   `ISK/hour = profit / build_hours`; ranks best-first.
4. Drops collector/data artifacts with an implausible margin cap (`--max-margin`, default 1000%).

> v1 was broken (its per-item endpoints had changed and returned nothing) and mis-valued
> multi-unit runs. v2 fixes both and is far faster (bulk SDE, no per-item calls).

## Files
| File | What |
|---|---|
| `bonk_blueprint_scanner.py` | the tool |
| `blueprint_page.py` | shared HTML renderer (fail-closed lock) |
| `page_lock.py` | client-side AES page encryption |
| `index.html` | generated Top-N page (committed + served by Pages) |
| `run.bat` / `run.ps1` | monthly runner: scan, then `publish.bat` |
| `publish.bat` | commit + push the page (fail-closed: refuses unlocked) |
| `sde_index.json` | cached blueprint index (gitignored; auto-rebuilds when stale) |
| `.venv\` | Python venv (openpyxl + cryptography) |

Only the page + source are committed; the SDE cache, CSV/XLSX, and logs are gitignored.

## The monthly job
A Windows Task Scheduler task **"BONK Blueprint Scanner"** runs `run.bat` monthly. The
SDE index auto-refreshes when older than `--max-cache-days` (25), so a monthly (or
bi-monthly) run always uses fresh data. The page is client-side encrypted with the shared
`EVE_PAGE_PASSWORD` (same password as the other EVE tools).

```powershell
schtasks /Query  /TN "BONK Blueprint Scanner" /V /FO LIST
schtasks /Run    /TN "BONK Blueprint Scanner"
schtasks /Change /TN "BONK Blueprint Scanner" /MO 2   # make it bi-monthly
```

## On-demand
```bat
cd C:\Users\sales\blueprint-scout
.venv\Scripts\python.exe bonk_blueprint_scanner.py --me 10 --top 5
.venv\Scripts\python.exe bonk_blueprint_scanner.py --categories ships,modules --refresh
.venv\Scripts\python.exe bonk_blueprint_scanner.py --demo      REM offline self-test
```

## Flags
| Flag | Default | Meaning |
|---|---|---|
| `--me` | `10` | assumed Material Efficiency (0-10) |
| `--top` | `5` | how many builds to keep |
| `--categories` | `all` | `ships,modules,ammo,drones` subset |
| `--max-margin` | `1000` | drop builds above this % margin (artifacts) |
| `--min-volume` | `0` | drop products below this sell volume |
| `--refresh` | off | force SDE index rebuild |
| `--allow-unlocked` | off | permit an UNLOCKED page (local only) |
| `--demo` | off | offline self-test |

## Notes
- "Profit" assumes Jita fills at listed prices; margins move when manufacturers flood a
  market. Treat as a STRONG directional guide, not a guarantee.
- Tech I filter + margin cap exist because faction/officer/special-edition items have SDE
  blueprints but trade as rare collectibles (fake margins). Adjust `--max-margin` to taste.
