# Agent Guidelines for FGDC to Zenodo Migration

## Core Principles

- **Never modify original FGDC XML files** - they are the source of truth
- **Always validate transformations** before uploading to Zenodo
- **Preserve all metadata** - if uncertain about a field, include it rather than exclude it
- **Work in small batches** - test with `--limit 10` before processing large sets
- **Check for duplicates** - verify no duplicate records are uploaded to Zenodo after each batch

## Critical Files (Never Delete)

- `FGDC/` - Original source files (4,206 XML files)
- `secrets.txt` - API tokens (keep secure) and never commit
- `logs/progress.csv` - Cumulative progress tracking
- `output/` - All generated content

## Workflow Guidelines

### Before Making Changes

- **Read existing logs** to understand current issues
- **Test with small samples** using `--limit 10`
- **Review transformation results** in `output/zenodo_json/`
- **Check validation reports** in `output/validation_report.json`

### During Processing

- **Log everything** - every issue, warning, and success should be documented
- **Handle edge cases gracefully** - log warnings rather than failing
- **Use sandbox tokens** for testing (never production without explicit instruction)
- **Respect rate limits** - Zenodo has strict limits: 5000 per hour and 100 per minute

### After Each Upload Batch

- **Check for duplicates** - run `python scripts/deduplicate_check.py --sandbox` to verify no duplicate records exist
- **Review duplicate report** - examine `output/duplicate_check_report_*.txt` for any issues
- **Review new log entries** for any issues introduced
- **Update progress metrics** in `logs/progress.csv`
- **Clean up temporary files** after operations

## Code Modification Rules

- **Test changes incrementally** - use `--limit 10` to test modifications
- **Preserve existing mappings** - only modify if you have a clear improvement
- **Add new validation rules** when you discover new issues
- **Comment complex transformations** with reasoning
- **Update README.md** if you change command-line options

## Quality Assurance

- **Compare before/after metrics** in progress logs
- **Ensure no regression** in successful transformation rates
- **Generate analysis reports** after significant runs
- **Identify patterns** in errors and warnings for systematic improvements
