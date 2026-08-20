# Info-Harbor Campaign Manager

A comprehensive campaign management system designed for location-based marketing and analytics. Info-Harbor automates the processing of location-based campaigns across multiple platforms including Placelift, Comparative Analysis, OOH (Out-of-Home), and Retail Intelligence.

## Modernization Status

> **Control-group rule for small campaigns (decision recorded 2026-08-20):**
> The standard configuration selects 50,000 control DIDs from a 100,000-DID
> candidate pool. When fewer than 100,000 eligible DIDs are available, the
> control group is reduced proportionally to 50% of the available pool
> (rounded to the nearest whole DID, with at least one control DID for a
> non-empty pool), rather than stopping the campaign or assigning every DID
> to control. For pools of 100,000 or more, the 50,000-DID cap is unchanged.
> This business rule should be reviewed with the placelift methodology owner.

> **Required environment variables for `ui/app.py` (decision recorded
> 2026-08-20, IH-025/IH-027):**
> - `INFO_HARBOR_API_TOKEN` — a shared bearer token every state-changing
>   route (`/campaign/<code>/run/<action>`, `/api/campaign/<code>/run/<action>`,
>   `/api/run-all-trackers`, `/api/campaigns/add`, `/automation`) requires
>   as `Authorization: Bearer <token>`. If unset or empty, every one of
>   those routes rejects every request with 401 — the app never falls
>   back to "no auth required." Read-only routes are unaffected.
> - `INFO_HARBOR_FLASK_SECRET_KEY` — the Flask session-signing key. If
>   unset or empty, the app refuses to start rather than using a
>   hardcoded value or a value regenerated on every process start.
>
> Both must be supplied securely at process-start time by whoever deploys
> or runs this app (a secret manager, an orchestrator's secret-injection
> mechanism, or an operator's own shell environment) — **never** committed
> to this repository, hardcoded in source, placed in a URL, written to a
> log, or embedded in any HTML/JavaScript served to the browser. Setting
> these in the actual deployment/runtime environment is a human deployment
> step, out of scope for this repository's code and CI configuration —
> `.github/workflows/deploy.yml` was not modified as part of this change.
>
> This bearer-token check is an **interim internal-control mechanism**,
> not a replacement for a real identity provider: it uses one shared
> secret with no per-user identity, no token rotation, and no CSRF
> protection. Treat it as closing the "wide open, no auth at all" gap
> (`docs/code-audit.md` IH-025), not as the final security posture for
> this UI.

**Why this work is happening:** An independent audit found that Info-Harbor's
reporting pipeline can silently produce zero output for certain campaign
types, can run reports under the wrong campaign's identity, and has no
automated tests to catch either problem before it reaches production. This
effort is fixing those problems in small, reviewed, test-backed steps rather
than through a single large rewrite, so that every change can be proven not
to break a working report before it ships.

**Current phase:** Phase 1 — Safety & Test Baseline (`feature/safety-test-baseline`).
Establishing an offline test suite and a complete issue register before any
pipeline behavior is changed. Awaiting review and approval before further work.

**What has been completed:**

- A full, evidence-based audit of the pipeline: 41 tracked findings, each
with exact file/line evidence and a safe way to reproduce it (see
`docs/code-audit.md`).
- An offline, credential-free automated test suite (50 tests) that proves
several of the most serious findings using the real production code —
without ever touching BigQuery, Google Drive, or any real credentials.
- A repository misconfiguration that would have silently discarded any test
suite ever committed has been fixed.
- A non-deploying validation check added for pull requests (the existing
production deployment process was left untouched).

**Most important confirmed risks** (full detail in `docs/code-audit.md`):

- A specific, common campaign configuration produces **zero reports and no
error**, silently, on every scheduled run.
- The audience "control group" — the baseline a campaign is measured
against — is not being kept separate from the group that saw the
campaign, undermining the statistical basis for reporting results.
- Segment processing can be run for one campaign but silently record data
under a *different* campaign's identity.
- The web dashboard can trigger production data writes, including for every
campaign at once, with no login required.

**Currently being worked on:** Nothing beyond this baseline — the project is
paused for review of Phase 1 before any pipeline code changes begin.

**What comes next (pending approval):** Unifying scattered configuration,
then fixing the confirmed issues above one at a time, each with its own
tests and sign-off, starting with the highest-severity findings.

**Safety statement:** No production data or cloud services (BigQuery,
Google Drive, Secret Manager) were written to, modified, or deleted during
this audit or while building the test suite. No real credentials were
created, read, or used. All 50 tests run entirely offline.

**Last updated:** 2026-08-19

**Further reading:**

- `[docs/code-audit.md](docs/code-audit.md)` — the full, detailed issue register
- `[docs/modernization-log.md](docs/modernization-log.md)` — chronological record of every change
- `[docs/modernization-spec.md](docs/modernization-spec.md)` — target architecture and technical plan



## 🚀 Features

- **Automated Campaign Processing**: End-to-end automation pipeline for segment processing and data validation
- **Multi-Country Support**: Manage campaigns across multiple countries and regions
- **Real-time Monitoring**: Live dashboard with campaign status and performance metrics
- **Data Validation**: Comprehensive validation system ensuring data quality and configuration accuracy
- **Cloud Integration**: Seamless integration with Google Cloud services (BigQuery, Cloud Storage, Drive)
- **Web Interface**: Modern, responsive web UI built with Flask and Bootstrap
- **API Access**: RESTful API endpoints for programmatic access



## 🏗️ Architecture

```
info-harbor/
├── shared/                 # Shared utilities and models
│   ├── config/            # Configuration management
│   │   ├── campaigns/     # Campaign configurations
│   │   ├── paths.py       # Path configurations
│   │   └── schemas.py     # Data schemas
│   ├── models/            # Data models
│   └── utils/             # Utility functions
├── projects/              # Core project modules
│   ├── automation/        # Main automation pipeline
│   ├── campaign-tracker/  # Campaign tracking system
│   └── segments/          # Segment processing
├── ui/                    # Web interface
│   ├── templates/         # HTML templates
│   ├── static/           # Static assets
│   └── app.py            # Flask application
└── keys/                  # API keys and credentials
```



## 🎯 Campaign Types



### Placelift

Location-based advertising campaigns targeting specific geographic areas and points of interest.

### Comparative Analysis

Market research campaigns comparing performance across different regions or competitors.

### OOH (Out-of-Home)

Digital signage and outdoor advertising campaigns for physical locations.

### Retail Intelligence

Store performance analysis and customer behavior tracking for retail locations.

## 🛠️ Technology Stack

- **Backend**: Python 3.x, Flask
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Database**: Google BigQuery
- **Cloud**: Google Cloud Platform
- **APIs**: Google Ads, Facebook, and other marketing platforms



## 📋 Prerequisites

- Python 3.8 or higher
- Google Cloud Platform account
- BigQuery access
- Required API credentials



## 🚀 Installation

1. **Clone the repository**
  ```bash
   git clone https://github.com/your-username/info-harbor.git
   cd info-harbor
  ```
2. **Install dependencies**
  ```bash
   pip install -r requirements.txt
  ```
3. **Configure credentials**
  - Place your API keys in the `keys/` directory
  - Configure Google Cloud credentials
  - Set up BigQuery access
4. **Run the application**
  ```bash
   cd ui
   python app.py
  ```
5. **Access the web interface**
  - Open your browser and navigate to `http://localhost:5000`
  - Use the dashboard to manage campaigns



## 📖 Usage



### Dashboard

- View all active campaigns and their current status
- Monitor real-time performance metrics
- Access quick actions for campaign management



### Campaign Management

- Click on any campaign to view detailed information
- Run segments processing for target audiences
- Execute campaign tracking and analytics
- Validate campaign configurations



### Automation

- Use the "Run Automation" button to execute the complete pipeline
- Monitor automation progress and results
- Check for any errors or warnings



### Documentation

- Access comprehensive documentation via the "Documentation" link
- Learn about system architecture and features
- Find troubleshooting guides and support information



## 🔧 Configuration



### Campaign Configuration

Each campaign requires the following configuration:

```python
{
    "campaign_code": "unique_identifier",
    "countries": ["US", "CA", "UK"],
    "type": "Placelift",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "segments": ["demographic_1", "geographic_1"],
    "excluded_segments": ["exclude_1"],
    "parameters": {
        "radius": 5000,
        "time_interval": "daily"
    }
}
```



### Environment Variables

Set the following environment variables:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export BIGQUERY_DATASET="campaign_data"
export API_KEYS_PATH="./keys/"
```



## 📊 API Endpoints



### Campaigns

- `GET /api/campaigns` - Get all campaigns
- `GET /api/campaign/<code>` - Get specific campaign details
- `POST /api/refresh` - Refresh campaign data

