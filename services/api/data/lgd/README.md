# Bundled LGD location data

These CSV files are a small, openly-licensed extract of the **India Local
Government Directory (LGD)** so the app's State → District → Mandal → Village
selectors and the location search work out of the box.

| File | Contents |
| --- | --- |
| `states.csv` | All 36 States / Union Territories |
| `districts.csv` | All 763 districts |
| `subdistricts.csv` | All 6,921 sub-districts (mandal / taluk / tehsil / circle) |
| `villages-south-india.csv` | 95,457 villages in Andhra Pradesh, Telangana, Karnataka, Tamil Nadu and Kerala |

**Source:** <https://github.com/planemad/india-local-government-directory>, a
mirror of the official <https://lgdirectory.gov.in> export.
**Licence:** Government Open Data License – India.

## Loading

```bash
cd services/api
python -m app.db.load_lgd
```

The loader uses the same import pipeline as
`python -m app.db.import_lgd <entity> <file>`, so it validates the hierarchy and
records an import audit job. It is safe to re-run — rows are upserted by LGD code.

## Getting the full national village set (optional)

This bundle ships villages for the five southern states only, to keep the
download small. For all ~640,000 Indian villages, download the current export
from <https://lgdirectory.gov.in/downloadDirectory.do> and import it:

```bash
python -m app.db.import_lgd villages path/to/villages.xlsx --source-version 2026-01-01
```

`source_version` should be the real export date, not the example above.
