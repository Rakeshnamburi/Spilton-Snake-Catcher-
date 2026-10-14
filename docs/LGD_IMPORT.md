# Official LGD Location Import

SPILTON stores the Indian administrative hierarchy as:

```text
State/UT → District → Subdistrict/Taluk/Tehsil/Mandal → Village
                      ↘ Urban local body → Ward
```

The application does not ship a fabricated or partial production directory. An administrator must download the current official reports from the Government of India Local Government Directory (LGD):

<https://lgdirectory.gov.in/demo/downloadDirectory.do>

The LGD download screen may require a CAPTCHA. Download the relevant CSV or XLSX reports manually and retain the source date/version shown by LGD. Do not scrape around the CAPTCHA or substitute an unofficial list while describing it as complete.

## Import order

Run the imports from `services/api` after `alembic upgrade head`. Parent records must exist before their children:

```powershell
python -m app.db.import_lgd states C:\imports\states.xlsx --source-version 2026-10-13
python -m app.db.import_lgd districts C:\imports\districts.xlsx --source-version 2026-10-13
python -m app.db.import_lgd subdistricts C:\imports\subdistricts.xlsx --source-version 2026-10-13
python -m app.db.import_lgd villages C:\imports\villages.xlsx --source-version 2026-10-13
python -m app.db.import_lgd urban_local_bodies C:\imports\ulbs.xlsx --source-version 2026-10-13
python -m app.db.import_lgd wards C:\imports\wards.xlsx --source-version 2026-10-13
```

Use the actual LGD export date or release label for `--source-version`. The command accepts CSV and XLSX. Header matching tolerates common LGD report variants such as `State Code`, `State Name (In English)`, and their district/subdistrict/village equivalents.

## Safety and recovery behavior

- Codes are normalized as strings so official leading zeros are preserved where present.
- Duplicate codes in one source file are rejected when their values conflict.
- Child rows are rejected if the referenced parent code is missing.
- Existing codes are updated idempotently; unchanged rows are skipped.
- Each attempt creates a `location_import_jobs` record with entity type, source version/URL, SHA-256 hash, counts, status, timestamp, and sanitized error text.
- Data changes occur inside one transaction. A failed validation rolls back the location changes; the failed job record is retained for diagnosis.
- Imports never reverse-geocode GPS coordinates or assert that a coordinate proves a village address. Customers must confirm or correct directory selections.

## Updating the directory

1. Back up PostgreSQL and record the currently active LGD source versions.
2. Download fresh official reports from LGD.
3. Import in parent-to-child order in a staging environment.
4. Review `/admin/locations` counts, versions, and errors.
5. Exercise cascading selectors and nearby-search coverage for the intended states.
6. Promote the same verified files through the production change process.

The Day 3 repository contains only synthetic hierarchy rows inside automated tests. Until official exports are imported, the public selectors correctly show an empty/import-required state and no claim of complete India coverage is made.
