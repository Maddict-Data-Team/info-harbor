# Info-Harbor Campaign Manager

A comprehensive campaign management system designed for location-based marketing and analytics. Info-Harbor automates the processing of location-based campaigns across multiple platforms including Placelift, Comparative Analysis, OOH (Out-of-Home), and Retail Intelligence.

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

### Actions
- `POST /campaign/<code>/run/segments` - Run segment processing
- `POST /campaign/<code>/run/tracker` - Run campaign tracking
- `POST /automation` - Run full automation pipeline

## 🔍 Monitoring & Logging

The system provides comprehensive monitoring:

- **Real-time Dashboard**: Live campaign status and metrics
- **Error Logging**: Detailed error tracking and reporting
- **Performance Metrics**: Processing times and success rates
- **Data Validation**: Automated validation checks and alerts

## 🐛 Troubleshooting

### Common Issues

1. **Campaign not loading**
   - Check BigQuery Campaign_Tracker table for data availability
   - Verify connection settings and credentials

2. **Automation fails**
   - Verify API credentials and permissions
   - Check error logs for specific issues
   - Ensure all dependencies are installed

3. **Data validation errors**
   - Review campaign configuration files
   - Ensure all required fields are properly set
   - Check data format and schema compliance

### Support
For additional support and troubleshooting:
- Check the documentation page in the web interface
- Review error logs and system messages
- Contact the development team

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Team

- **Development Team**: Maddict
- **Project**: Info-Harbor Campaign Manager
- **Version**: 2025.1

## 📞 Contact

For questions, support, or collaboration:
- **Project**: Info-Harbor Campaign Manager
- **Team**: Maddict
- **Year**: 2025

---

**Note**: This system is designed for enterprise-level campaign management and requires proper setup and configuration. Please ensure you have the necessary permissions and credentials before deployment.