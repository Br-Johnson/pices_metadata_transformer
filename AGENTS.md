# Agent Guidelines for FGDC to Zenodo Migration

## User Interaction

- Before implementing new feaures, always stop and ask me how I want you to implement certain features that are not described thoroughly in our plan before implementing them
- Keep code changes small and focussed
- Avoid creating new files for functionality that exists in existing files. Edit existing files instead

## Core Principles

- **Never modify original FGDC XML files** - they are the source of truth
- **Always validate transformations** before uploading to Zenodo
- **Preserve all metadata** - if uncertain about a field, include it in Zenodo `notes` field rather than exclude it
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

## Common Issues and Solutions

### Date Field Warnings (Normal Behavior)

- **Issue**: Warnings like `date_normalization: complex_date_range. Found: 72-88 thru 87-98`
- **Solution**: These are **NOT errors** - they're informational warnings showing the system is correctly converting complex FGDC date formats to valid ISO dates
- **Action**: None required - this is expected behavior

### Function Signature Errors

- **Issue**: `transform_fgdc_file() takes 1 positional argument but 2 were given`
- **Solution**: Always use `transform_fgdc_file(xml_path)` with only one argument
- **Correct Usage**: `result = transform_fgdc_file("path/to/file.xml")`

### License Field Issues

- **Issue**: Files rejected with invalid license "none"
- **Solution**: The system now correctly defaults to "cc-zero" license
- **Fix**: Regenerate JSON files with `python scripts/batch_transform.py --input FGDC --output output --limit N`

### Command Line Usage

- **Issue**: Incorrect script arguments
- **Solution**: Use `python scripts/batch_transform.py --input FGDC --output output --limit 30`
- **Avoid**: `python scripts/batch_transform.py --limit 30 --output-dir output`

### Environment Setup

- **Issue**: Missing API tokens
- **Solution**: Ensure `.env` file exists with `ZENODO_SANDBOX_TOKEN=your_token`

## Quality Assurance

- **Compare before/after metrics** in progress logs
- **Ensure no regression** in successful transformation rates
- **Generate analysis reports** after significant runs
- **Identify patterns** in errors and warnings for systematic improvements
- **Verify 100% field preservation** using enhanced metrics analysis
- **Check unmapped fields** - should always be 0 for proper data preservation
