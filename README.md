# Info-Harbor

## Overview
The Info-Harbor project is one of the largest undertakings at Maddict, designed to manage the entire campaign workflow efficiently. It is built around a modular architecture with three core components: Campaign Tracker, Segment Selection, and Automation. Each component plays a distinct role and integrates seamlessly with Google Cloud services, with BigQuery serving as the primary tool for data storage and querying.

### Components
- **Campaign Tracker**: Handles the addition of metadata.
- **Segment Selection**: Identifies and retrieves the most suitable segments.
- **Automation**: Oversees the execution of the campaigns.

## Table of Contents
- [Overview](#overview)
  - [Components](#components)
- [Technologies](#technologies)
- [Setup Instructions](#setup-instructions)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Google Cloud SDK Setup](#google-cloud-sdk-setup)
- [License](#license)

## Technologies
This project is built using the following technologies:
- **Google Cloud Platform (GCP)** for infrastructure and services.
- **Python** for scripting and data manipulation.
- **SQL** for querying BigQuery.
- **GitHub** for securely storing the code and version control.

## Setup Instructions

### Prerequisites
- GCP account with access to BigQuery and some other services (depends on your role).
- Python 3.8 or higher.
- Access to required datasets in BigQuery.

### Installation
Follow these steps for setting up the project locally.

```bash
# Clone the repository
git clone https://github.com/Maddict-Data-Team/info-harbor.git

# Navigate to the project directory
cd info-harbor

# Install dependencies
pip install -r requirements.txt

```

### Google Cloud SDK Setup
Follow these steps for logging in to GCP.

```bash
# Install Google Cloud SDK (if not already installed)
# For detailed instructions, visit: https://cloud.google.com/sdk/docs/install

# After installing the SDK, authenticate to GCP
gcloud auth login

# (Optional) Set the project ID if it's not already set
gcloud config set project maddict-project-id

# Verify that you're logged in and can access the project
gcloud config list

```
# License

MIT License

Copyright (c) 2024 Maddict Data Team