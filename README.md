# PICES FGDC to Zenodo Metadata Migration

This project transforms 4,206 FGDC XML metadata records to Zenodo JSON format and uploads them to the Zenodo sandbox for the PICES (North Pacific Marine Science Organization) metadata migration project.

## 🏗️ Project Structure

```
pices_md_2/
├── scripts/                    # All Python scripts
│   ├── fgdc_to_zenodo.py      # Core transformation logic
│   ├── validate_zenodo.py     # Validation script
│   ├── batch_transform.py     # Batch transformation processor
│   ├── zenodo_api.py          # Zenodo API client
│   ├── upload_to_zenodo.py    # Legacy upload script
│   ├── batch_upload.py        # New batched upload system
│   ├── test_batch_upload.py   # Test script for batch uploads
│   ├── upload_audit.py        # Audit and verification system
│   ├── verify_uploads.py      # Post-upload verification
│   ├── resume_upload.py       # Resume interrupted uploads
│   ├── generate_exclusion_lists.py # Generate exclusion lists
│   └── logger.py              # Logging infrastructure
├── docs/                      # Documentation and reference files
│   ├── rfq.txt               # Request for Quote document
│   ├── fgdc_to_zenodo_crosswalk_exhaustive.csv # Field mappings
│   ├── tips_gotchas.txt      # Transformation tips and edge cases
│   ├── zenodo_api_docs.txt   # Zenodo API documentation
│   └── FDGC-STD-001-1998v2.txt # FGDC standard reference
├── FGDC/                     # Source FGDC XML files (4,206 files)
├── logs/                     # Log files and analysis reports
├── output/                   # Generated output files
├── transformed/              # Transformed JSON files and copies
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd pices_md_2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your Zenodo API tokens
```

### 2. Transform Metadata

```bash
# Test with small sample
python scripts/batch_transform.py FGDC output --limit 10

# Transform all files
python scripts/batch_transform.py FGDC output
```

### 3. Upload to Zenodo

```bash
# Test batch upload (5 files)
python scripts/test_batch_upload.py

# Upload in batches of 100 (recommended)
python scripts/batch_upload.py --sandbox --batch-size 100

# Upload all files in batches of 1000
python scripts/batch_upload.py --sandbox --batch-size 1000
```

### 4. Check for Duplicates

```bash
# Check for duplicates across all sources
python scripts/deduplicate_check.py --sandbox

# Check specific files
python scripts/deduplicate_check.py --sandbox --check-files FGDC-1,FGDC-2

# Generate report only (no deletions)
python scripts/deduplicate_check.py --sandbox --report-only
```

### 5. Audit Results

```bash
# Generate comprehensive audit report
python scripts/upload_audit.py --output-dir output
```

## 📋 Detailed Usage

### Transformation Process

The transformation process converts FGDC XML metadata to Zenodo JSON format following the comprehensive crosswalk mapping in `docs/fgdc_to_zenodo_crosswalk_exhaustive.csv`.

**Key Features:**

- Handles all 60+ FGDC elements
- Comprehensive edge case handling
- Detailed logging and error tracking
- Data integrity validation
- Character count analysis

**Command Options:**

```bash
python scripts/batch_transform.py --input FGDC --output output [options]

Options:
  --limit N        Process only N files (for testing)
  --input DIR      Input directory containing FGDC XML files (required)
  --output DIR     Output directory for transformed files (required)
  --verbose        Enable verbose logging
```

### Upload Process

The new batched upload system provides:

- **Rate limiting**: Stays within Zenodo limits (90 req/min, 4500 req/hour)
- **Resource management**: Proper cleanup with context managers
- **Error recovery**: Continues processing even if individual files fail
- **Progress tracking**: Can resume from any point
- **Audit trail**: Comprehensive logging and reporting
- **Duplicate prevention**: Centralized registry and API-based duplicate detection

**Command Options:**

```bash
python scripts/batch_upload.py [options]

Options:
  --sandbox        Use Zenodo sandbox (default: True)
  --production     Use Zenodo production (overrides --sandbox)
  --batch-size N   Number of files per batch (default: 1000)
  --limit N        Limit number of files to process (for testing)
  --interactive    Interactive mode: stop between batches for review (recommended for production)
  --output-dir DIR Output directory for logs (default: output)
```

### Interactive Mode (Recommended for Production)

For production uploads, use interactive mode to review each batch before proceeding:

```bash
# Production upload with interactive review
python scripts/batch_upload.py --production --interactive --batch-size 50

# Sandbox testing with interactive review
python scripts/batch_upload.py --sandbox --interactive --batch-size 10
```

Interactive mode provides:

- **Batch-by-batch review**: Stop after each batch to review results
- **Built-in tools**: Run duplicate checks and audits directly from the interface
- **Quality control**: Ensure each batch is successful before proceeding
- **Manual validation**: Review logs, reports, and individual records
- **Safe stopping**: Exit cleanly at any point with progress saved

### Duplicate Detection

The duplicate detection system provides:

- **Multi-source checking**: Compares local logs, centralized registry, and Zenodo API
- **Title-based detection**: Finds records with identical titles
- **Registry validation**: Ensures local tracking matches Zenodo state
- **Comprehensive reporting**: Detailed analysis of potential duplicates
- **Safe operation**: Report-only mode by default

### Audit and Verification

The audit system provides comprehensive reporting on:

- Upload success rates
- Error analysis and categorization
- Data integrity checks
- Performance metrics
- Recommendations for improvements

**Command Options:**

```bash
python scripts/upload_audit.py [options]

Options:
  --output-dir DIR Directory containing upload logs
  --report-file FILE Save human-readable report to file
```

**Duplicate Detection Options:**

```bash
python scripts/deduplicate_check.py [options]

Options:
  --sandbox        Check sandbox Zenodo (default: True)
  --production     Check production Zenodo (overrides --sandbox)
  --output-dir DIR Output directory for reports (default: output)
  --check-files    Comma-separated list of specific files to check
  --report-only    Generate report only, do not delete duplicates (default: True)
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with your Zenodo API tokens:

```bash
ZENODO_SANDBOX_TOKEN=your_sandbox_token_here
ZENODO_PRODUCTION_TOKEN=your_production_token_here
```

### Rate Limiting

The system automatically handles Zenodo's rate limits:

- **Minute limit**: 90 requests/minute (safely under 100/min limit)
- **Hour limit**: 4500 requests/hour (safely under 5000/hour limit)
- **Request interval**: 0.7 seconds between requests

### Batch Sizes

Recommended batch sizes:

- **Testing**: 5-10 files
- **Development**: 100 files
- **Production**: 1000 files

## 📊 Monitoring and Logging

### Log Files

The system generates comprehensive logs:

- `logs/transform_*.log` - Transformation progress and issues
- `logs/warnings.json` - Structured warnings with context
- `logs/errors.json` - Errors requiring attention
- `logs/progress.csv` - Cumulative progress tracking
- `output/batch_upload_log_*.json` - Upload progress and results
- `output/upload_audit_*.json` - Comprehensive audit data

### Progress Tracking

Monitor progress with:

```bash
# Check transformation progress
tail -f logs/transform_*.log

# Check upload progress
tail -f output/batch_upload_log_*.json

# Generate audit report
python scripts/upload_audit.py
```

## 🔍 Record Review and Analysis

### Individual Record Review

Use the comprehensive record review helper to analyze specific transformations:

```bash
# Review a specific record
python scripts/record_review.py FGDC-1234

# Review with Zenodo verification
python scripts/record_review.py FGDC-1234 --check-zenodo

# Review in production environment
python scripts/record_review.py FGDC-1234 --production
```

### Review Output

The record review provides:

- **Overall Status**: Excellent/Good/Fair/Poor with quality score
- **File Status**: Which files exist (original FGDC, transformed JSON)
- **Original FGDC Analysis**: File size, XML structure, key field presence
- **Transformed JSON Analysis**: Field coverage, data preservation ratios
- **Upload Analysis**: Upload status, deposition ID, DOI, timestamp
- **Issue Analysis**: Warnings, errors, validation issues
- **Zenodo Verification**: Live check against Zenodo API (optional)

### Enhanced Metrics

The system now provides comprehensive metrics:

#### Data Preservation Metrics

- **Content Preservation Ratio**: Percentage of meaningful content preserved
- **Field Preservation Ratio**: Percentage of FGDC fields successfully mapped
- **Semantic Preservation Score**: Quality of meaning preservation
- **Data Loss/Gain Indicators**: Specific issues identified

#### Field Coverage Analysis

- **Critical Fields**: Title, creators, publication date, description (weighted 70%)
- **Important Fields**: Keywords, license, access rights, communities (weighted 20%)
- **Optional Fields**: Notes, references, contributors (weighted 10%)
- **Weighted Coverage Score**: Overall field completeness

#### Data Quality Assessment

- **Title Quality**: Length, formatting, capitalization
- **Creator Quality**: Name format, completeness
- **Description Quality**: Length, sentence structure
- **Keyword Quality**: Count, length, relevance
- **Date Quality**: Format validation, reasonableness
- **License Quality**: Valid license identification

#### Transformation Effectiveness

- **Mapping Completeness**: How well FGDC fields were mapped
- **Data Enrichment**: Additional value added during transformation
- **Format Compliance**: Zenodo schema compliance
- **Semantic Accuracy**: Meaning preservation quality

#### Compliance Metrics

- **Zenodo Required Fields**: 100% required for upload
- **Zenodo Recommended Fields**: Best practices compliance
- **PICES Community**: Community membership verification
- **Open Access**: Access rights compliance
- **License Compliance**: Valid license usage

### Quality Scoring

Records are scored on a 0-100 scale with letter grades:

- **A (90-100)**: Excellent quality, all requirements met
- **B (80-89)**: Good quality, minor issues
- **C (70-79)**: Fair quality, some concerns
- **D (60-69)**: Poor quality, significant issues
- **F (0-59)**: Failed quality, major problems

### Example Review Output

```
🟢 OVERALL STATUS: EXCELLENT
📊 Data Quality Score: 95.0%
🔄 Transformation: ✅
⬆️  Upload: ✅

📁 FILES:
   Original FGDC: ✅
   Transformed JSON: ✅

📄 ORIGINAL FGDC ANALYSIS:
   File size: 4.39 KB
   XML elements: 90
   Title: ✅
   Creators: ✅
   Abstract: ✅
   Keywords: ✅
   Spatial bounds: ✅

🔄 TRANSFORMED JSON ANALYSIS:
   Fields present: 13/13
   Required fields: 4/4
   Data preservation: 95.2%
   Quality grade: A

⬆️  UPLOAD ANALYSIS:
   Status: success
   Deposition ID: 348189
   DOI: 10.5281/zenodo.348189
```

### Bulk Metrics Analysis

Analyze enhanced metrics across all transformed records:

```bash
# Analyze all records and print summary
python scripts/metrics_analysis.py

# Analyze and save detailed report
python scripts/metrics_analysis.py --save-report

# Analyze with custom output directory
python scripts/metrics_analysis.py --output-dir custom_output --save-report
```

The metrics analysis provides:

- **Overall Score Distribution**: Average, median, min/max scores across all records
- **Quality Grade Distribution**: Count and percentage of A/B/C/D/F grades
- **Field Coverage Analysis**: Average coverage for critical/important/optional fields
- **Compliance Analysis**: Zenodo compliance rates and PICES community membership
- **Transformation Effectiveness**: Mapping completeness and data enrichment scores
- **Actionable Recommendations**: Specific improvements based on analysis patterns

### Metrics Assessment

#### Character Count Analysis

Focuses on **meaningful content preservation**:

- Extracts only text content from key FGDC elements
- Calculates semantic preservation scores
- Identifies specific data loss/gain patterns
- Provides actionable insights for transformation improvements

#### Field Coverage Analysis

- **Critical fields** (70% weight): title, creators, publication_date, description
- **Important fields** (20% weight): keywords, license, access_right, communities
- **Optional fields** (10% weight): notes, references, contributors
- **Weighted coverage score** provides meaningful completeness metric

#### Data Integrity Metrics

- **Quality grades** (A-F) with clear thresholds (90+, 80+, 70+, 60+, <60)
- **Percentage-based scoring** for all coverage metrics
- **Clear definitions** for each metric category
- **Actionable recommendations** based on analysis patterns

## 🛠️ Troubleshooting

### Common Issues

1. **Rate Limiting Errors**

   - The system automatically handles rate limits
   - If you see rate limit errors, the system will wait and retry

2. **Resource Leaks**

   - The new system uses context managers for proper cleanup
   - If you see semaphore warnings, restart the process

3. **Upload Failures**

   - Check the audit report for error patterns
   - Use smaller batch sizes for problematic files
   - The system can resume from where it left off

4. **Memory Issues**

   - Use smaller batch sizes
   - The system processes files one at a time to minimize memory usage

5. **Duplicate Records**
   - Run duplicate check: `python scripts/deduplicate_check.py --sandbox`
   - Review the report for title duplicates and registry mismatches
   - Use `--check-files` to verify specific files
   - The system now prevents duplicates automatically during upload

### Recovery

If an upload is interrupted:

```bash
# The system automatically resumes from where it left off
python scripts/batch_upload.py --sandbox --batch-size 100
```

## 📈 Performance Metrics

### Expected Performance

- **Transformation**: ~0.1 seconds per file
- **Upload**: ~3-4 seconds per file (including rate limiting)
- **Total time**: ~2-3 hours for all 4,206 files

### Success Rates

- **Transformation**: >99% success rate
- **Upload**: >95% success rate
- **Data integrity**: >98% pass validation

## 🔍 Quality Assurance

### Validation

All transformed records are validated against:

- Zenodo schema requirements
- Required field presence
- Data format validation
- URL validation
- Date format validation

### Data Integrity

The system tracks:

- Character count preservation
- Field coverage analysis
- Missing data identification
- Transformation accuracy

## 📚 Documentation

- `docs/rfq.txt` - Project requirements and scope
- `docs/fgdc_to_zenodo_crosswalk_exhaustive.csv` - Complete field mappings
- `docs/tips_gotchas.txt` - Edge cases and transformation tips
- `docs/zenodo_api_docs.txt` - Zenodo API reference

## 🤝 Contributing

1. Follow the existing code structure
2. Add comprehensive logging for any new features
3. Update documentation for any changes
4. Test with small batches before full runs
5. Ensure proper error handling and resource cleanup

## 📄 License

This project is part of the PICES metadata migration initiative.

## 🆘 Support

For issues or questions:

1. Check the logs for detailed error information
2. Review the audit reports for patterns
3. Use the test scripts to isolate issues
4. Consult the documentation in the `docs/` directory
