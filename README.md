# Card Reconciliation Tool - Automated Rate Analysis System

## Summary

The Card Reconciliation Tool is an enterprise-grade Flask-based web application designed for automated fee rate analysis and reconciliation in the payment card industry. The system provides comprehensive rate calculation capabilities across multiple transaction types and automatically reconciles calculated fees against actual invoice amounts.

The platform features an intelligent automation layer that continuously monitors designated transaction folders, automatically executes rate analysis on complete file sets, and proactively alerts stakeholders when reconciliation metrics fall below configurable thresholds. This eliminates the need for manual monitoring while ensuring critical discrepancies are identified and escalated immediately.

### Core Capabilities

**Rate Analysis Services**
- Dynamic fee calculation based on configurable rate formulas
- Multi-currency support with automatic exchange rate conversion (USD to INR)
- Card issuance data integration and tracking
- Transaction analysis across international, domestic, and dispute categories
- Invoice comparison with calculated fee structures
- Comprehensive reconciliation percentage calculations
- Fuzzy matching between calculated and invoiced line items

**Automation Services**
- Continuous file system monitoring of transaction folders
- Automatic processing upon complete file set detection
- Threshold-based alerting via email and voice calls
- Complete audit trail and historical analysis
- Automated archival of processed transactions
- Configurable processing intervals and alert thresholds

## Workflow

### Manual Operation Workflow

The manual workflow allows users to directly interact with the system through a web interface for on-demand analysis.

**Step 1: User Authentication and Access**

Users navigate to the web application and access the Rates File tab for fee calculation and analysis.

**Step 2: File Upload**

Users upload the required files through the web interface:

Required Files:
- Summary file containing fee rate formulas and calculation rules
- Invoice file with actual VISA invoice amounts for comparison

Optional Files:
- Card Issuance Report for card-based fee calculations
- International Transactions file for international license fees
- Domestic Transactions file for domestic authorization fees
- VROL Dispute Report for dispute-related fees

**Step 3: Processing Execution**

Upon submission, the system performs the following operations:

- Extracts fee types and rate formulas from the Summary file
- Processes card issuance data with period breakdowns
- Analyzes transaction files by category (international, domestic, disputes)
- Calculates fees based on defined formulas supporting multiple patterns (tiered pricing, per-transaction, volume-based, amount-based)
- Extracts actual invoice amounts from the Invoice file
- Performs fuzzy matching between calculated line items and invoiced items
- Computes reconciliation metrics across multiple dimensions

**Step 4: Results Presentation**

The system displays a comprehensive dashboard showing:

Primary Metrics:
- Amount Reconciled percentage (calculated total vs VISA invoice total)
- Fee Reconciled percentage (percentage of invoice items matched)
- Item Reconciled count (matched items vs total VISA items)
- Match percentage (exact amount matches among reconciled items)

Financial Summary:
- Calculated Total in INR
- VISA Invoice Total in INR
- Total Fee Mappings identified

Detailed Breakdown:
- Card issuance data summary
- Transaction overview by category
- Fee detail by sheet with calculation methods
- Line-by-line comparison with percentage differences

**Step 5: User Review and Action**

Users review the results, analyze discrepancies highlighted by percentage differences, identify items requiring attention, and take appropriate action based on findings.

### Automated Monitoring Workflow

The automated workflow operates continuously in the background, eliminating manual intervention for routine processing.

**Continuous Monitoring Phase**

The file system monitor observes designated transaction folders at configurable intervals (default: 5 minutes). The system checks for the presence of all required files and tracks modification timestamps to prevent duplicate processing of the same file set.

**File Detection Phase**

The monitor identifies complete file sets by detecting the following files in transaction folders:

Required Files:
- Card Issuance Report.xlsx
- Domestic transactions.xlsx
- International Transactions.xlsx
- Invoice.xlsx or Invoice - Copy.xlsx
- Summary.xlsx
- VROL Report.xlsx

Optional Files:
- Network Charges Recon.xlsx

**Validation Phase**

The system performs validation checks:
- Verifies that all mandatory files are present in the folder
- Confirms files have been modified since the last processing cycle
- Checks file accessibility and format validity

If validation fails, the system logs the status and waits for the next monitoring cycle. If validation succeeds, processing is initiated.

**Automatic Processing Phase**

Upon successful validation:
- Creates a temporary processing directory
- Copies files to the temporary location for isolated processing
- Maps files to the expected format for the rate analysis engine
- Invokes the rate analysis engine with mapped file paths
- Receives comprehensive results with all calculated metrics

**Threshold Evaluation Phase**

The system extracts the Amount Reconciled percentage and compares it against the configured threshold (default: 95%):

- Below 95%: Triggers critical alert (email and phone call)
- 95% to 98%: Generates warning alert (email only)
- Above 98%: Results in informational logging (no alert)

**Alert Dispatch Phase**

When thresholds are breached, the system executes the following:

Email Alert:
- Generates detailed alert message with all reconciliation metrics
- Includes calculated vs VISA amounts with difference
- Lists all processed files
- Sends to configured recipient list via SMTP

Voice Call Alert:
- Constructs text-to-speech script with key metrics
- Initiates automated voice call via Twilio
- Delivers concise alert information to designated phone numbers
- Directs recipients to check email for details

Logging:
- Records alert in database with timestamp and severity
- Logs notification attempts and delivery status
- Maintains audit trail for compliance

**Cleanup and Archival Phase**

After processing completion:
- Moves processed files to date-stamped archive folders
- Stores complete analysis results in the database
- Updates processing timestamps to prevent reprocessing
- Removes temporary files and cleans up working directory
- Logs completion status with summary metrics

## Architecture

### System Architecture Overview

The Card Reconciliation Tool employs a multi-layered architecture designed for scalability, maintainability, and reliability.

**Presentation Layer**

The web application layer provides a user interface through the Rates File tab for manual fee analysis and invoice reconciliation. The interface allows file uploads, displays processing status, and presents comprehensive results in a dashboard format. The presentation layer communicates with the backend through RESTful API endpoints for processing requests and status queries.

**Automation Layer**

The automation layer operates independently from the web application as a background service:

- File System Monitor: Uses the Watchdog library to observe transaction folders for file changes. Implements event-driven detection of new or modified files. Validates complete file sets before triggering processing.

- Auto Processor: Orchestrates the complete analysis workflow from file detection through result storage. Maps detected files to the expected format. Executes analysis through the integration layer. Evaluates results against configurable thresholds. Coordinates with the alert manager for notifications.

- Alert Manager: Handles multi-channel notifications through email (SMTP) and voice calls (Twilio). Constructs detailed alert messages with comprehensive metric information. Implements severity-based formatting. Maintains retry logic for failed notification attempts.

- Scheduler: Manages timing of monitoring cycles. Prevents duplicate processing through timestamp tracking. Coordinates concurrent processing requests.

**Business Logic Layer**

The processing layer contains the core rate analysis algorithms and business rules:

- Configuration Module: Defines fee type patterns, rate formula templates, column mapping rules, and validation criteria. Provides file structure detection patterns.

- Rate Calculator: Performs dynamic fee calculations based on configurable formulas. Supports multiple formula types including tiered pricing structures, per-transaction fees, per-dispute fees, volume-based calculations, and transaction amount-based fees. Handles multi-currency conversions.

- Data Extractors: Analyzes Excel structure to identify fee types and rate formulas. Extracts card issuance data with automatic period detection. Processes transaction files by category with intelligent type detection. Extracts invoice line items for comparison.

- Reconciliation Engine: Performs fuzzy matching between calculated and invoice line items. Computes reconciliation percentages across multiple dimensions. Identifies discrepancies and calculates percentage differences. Generates comprehensive metric summaries.

**Data Access Layer**

The data layer manages all file operations and persistence:

- File Handlers: Support multiple encodings (UTF-8, Latin1, CP1252) for text files. Handle Excel formats (.xlsx, .xls) with automatic header detection. Implement error recovery for malformed files.

- Database Layer: Stores processing history with complete metadata. Maintains alert records for audit compliance. Persists analysis results for historical reporting. Uses SQLAlchemy ORM with SQLite for development and PostgreSQL option for production.

- Archive Management: Moves processed files to date-stamped folders. Implements configurable retention policies. Maintains file integrity for compliance requirements.

**Integration Layer**

The integration layer connects external services and APIs:

- Email Integration: Supports standard SMTP for cross-platform compatibility. Implements Outlook integration via win32com for Windows environments. Handles template-based message generation. Manages attachment and inline content.

- Twilio Integration: Enables voice call alerts with text-to-speech capabilities. Supports multiple recipient phone numbers. Implements call status tracking and retry logic.

- REST API: Exposes endpoints for automation status monitoring, processing history retrieval, manual trigger capabilities, and configuration management.

**Deployment Components**

Web Application Service:
- Flask application with Gunicorn WSGI server
- Handles HTTP requests for manual processing
- Serves user interface and API endpoints
- Manages session state and file uploads

Automation Service:
- Independent Python process for background monitoring
- Runs continuously with configurable check intervals
- Isolated from web application for reliability
- Restart-safe with state persistence

Shared Resources:
- Transaction folders accessible to both services
- Database for coordinated state management
- Log files for unified audit trail
- Configuration files for consistent behavior

**Data Flow Architecture**

Input Data Flow:
- Transaction files arrive in monitored folders
- File monitor detects and validates completeness
- Files are copied to temporary processing directory
- Rate analysis engine parses each file by type
- Extracted data is normalized and validated

Processing Data Flow:
- Configuration provides mapping rules and formula patterns
- Rate calculator applies formulas to transaction and card data
- Invoice data is extracted and matched against calculated values
- Reconciliation percentages are computed
- Results are packaged into comprehensive report structure

Output Data Flow:
- Processing results are stored in database with metadata
- Alert messages are constructed based on threshold evaluation
- Notifications are dispatched through configured channels
- Processed files are moved to archive folders
- API endpoints expose results for external integration
- Audit logs are written for compliance

**Security Architecture**

Authentication and Authorization:
- API endpoints require token-based authentication
- Environment variables isolate credentials from source code
- Session management secures web application access

Data Protection:
- File system permissions restrict access to transaction folders
- Database encryption protects stored reconciliation results
- HTTPS/TLS encrypts all web traffic
- Sensitive data is masked in log files

Audit and Compliance:
- Complete audit trails track all processing activities
- Alert logs maintain notification history
- Processing timestamps enable forensic analysis
- File archives preserve original transaction data
- Database records support regulatory compliance requirements

## Deployment

### Quick Deploy to Render (Free Tier)

This application is ready for cloud deployment on Render's free tier.

**Prerequisites:**
- OpenAI API key for root cause analysis
- GitHub repository

**Deploy Steps:**
1. See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions
2. Set required environment variables: `OPENAI_API_KEY` and `SECRET_KEY`
3. Deploy with build command: `pip install -r requirements.txt`
4. Start with: `gunicorn app:app --bind 0.0.0.0:$PORT`

**Deployment URL:** After deployment, access your app at `https://your-app-name.onrender.com`

**Cost:** Free tier available, or $7/month for Starter tier (no sleep, better performance)

### Environment Variables Required

See `.env.example` for complete list:
- `OPENAI_API_KEY` - Required for AI-powered root cause analysis
- `SECRET_KEY` - Required for Flask session security
- `SMTP_*` - Optional (email alerts already configured in code)

### Features Available on Free Tier
✅ All reconciliation features
✅ ZIP upload batch processing
✅ OpenAI root cause analysis
✅ Email alerts
✅ Excel/PDF report generation
✅ Real-time processing
✅ HTTPS security

**Note:** Free tier sleeps after 15 minutes of inactivity. First request takes ~30 seconds to wake up.

## Technology Stack

- **Backend:** Python 3.11, Flask
- **AI/ML:** OpenAI GPT-3.5-Turbo for root cause analysis
- **Data Processing:** pandas, openpyxl
- **Reports:** ReportLab (PDF), Excel export
- **Email:** Mailjet SMTP
- **Deployment:** Gunicorn WSGI server
- **Cloud:** Render (free tier compatible)
