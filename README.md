# Invoice Receiver Service

A webhook-based service that automatically processes invoices from emails using Microsoft Graph API and QR code detection.

## Overview

This service monitors an email inbox for new invoices, extracts relevant data using QR code detection, validates the information, and sends it to the Navision ERP system. It utilizes the Microsoft Graph API for email monitoring and webhook notifications.

## Features

* Email monitoring via Microsoft Graph API
* Automatic QR code detection from PDF attachments
* Invoice data validation and error handling
* Integration with Navision ERP
* Automatic retry mechanism for failed operations
* Secure token management for API authentication
* Detailed logging for monitoring and debugging

## Prerequisites

To run this service, ensure that the following dependencies are installed:

* Python 3.10+
* SQL Server
* Microsoft Azure Account with Graph API access
* Navision ERP system
* ODBC Driver for SQL Server
* ngrok (for local development)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/invoice-receiver-service.git
cd invoice-receiver-service
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install ngrok:
   * Download from ngrok.com
   * Extract and add it to your system PATH
   * Sign up and obtain your authentication token
   * Run:
```bash
ngrok authtoken your_auth_token
```

5. Configure environment settings:
   * Set up the SQL Server connection in `src/ProcessingData/DB/conection.py`
   * Configure Microsoft Graph API credentials in `src/info/config.py`

## Usage

1. Start ngrok to expose your local webhook:
```bash
ngrok http 5048
```

2. Copy the ngrok HTTPS URL (e.g., https://1234-your-tunnel.ngrok.io) and update:
   * Azure webhook subscription URL
   * `WEBHOOK_URL` in `src/info/config.py`

3. Start the webhook server:
```bash
python src/main.py
```

4. Once started, the service will:
   * Listen for webhook notifications on port 5048
   * Process incoming emails automatically
   * Extract QR codes from PDF attachments
   * Validate extracted data and send it to Navision ERP

5. Monitor logs in `logs/app.log` for debugging and issue tracking

## Webhook Configuration

### Local Development with ngrok
* ngrok creates a secure tunnel to your local machine
* Provides a public HTTPS URL for the webhook
* Allows Microsoft Graph API to send notifications to the local server
* Includes a web interface at http://localhost:4040 for inspecting webhook traffic

### Production Setup
* Replace the ngrok URL with the production server URL
* Update the webhook subscription in Azure
* Ensure port 5048 is accessible for webhook communication

### Managing Webhook Subscriptions
* The service automatically creates new subscriptions
* To cancel all existing subscriptions, run:
```bash
python cancelAllSubscriptions.py
```

## Configuration Files

* `src/info/config.py` – API credentials and webhook endpoints
* `src/ProcessingData/DB/conection.py` – Database connection settings
* `src/Hook/webhook.py` – Webhook server configuration

## Testing

To run the test suite:
```bash
pytest tests/
```

## Project Structure

```
InvoiceReceiver/
├── src/
│   ├── Hook/                 # Webhook handling
│   ├── ProcessingData/       # Data processing logic
│   │   ├── API/             # External API integrations
│   │   ├── DB/              # Database operations
│   │   └── transformations/ # Data transformations
│   ├── info/                # Configuration files
│   └── main.py             # Application entry point
├── tests/                   # Test suite
└── logs/                    # Application logs
```

## Error Handling

The service includes mechanisms to handle errors efficiently:

* Automatic retry for failed operations
* Detailed error logging for debugging
* Email notifications for processing failures
* Duplicate email detection to prevent redundant processing

## Monitoring

You can monitor the service using:

* Application logs in `logs/app.log`
* ngrok web interface at http://localhost:4040
* Email notifications for processing failures
* SQL Server transaction logs for database monitoring

## Troubleshooting

### Webhook not receiving notifications:
* Check ngrok status and URL
* Verify webhook subscription in Azure
* Ensure port 5048 is not blocked by a firewall

### Connection errors:
* Verify SQL Server connectivity
* Check Microsoft Graph API credentials
* Ensure ODBC drivers are correctly installed

### Processing errors:
* Ensure the PDF attachment format is valid
* Verify QR code readability
* Check the data validation rules in the service

## Security

* Secure token management for API authentication
* Webhook validation to prevent unauthorized requests
* Encrypted database connections for secure data storage
* Strict handling of sensitive information
* ngrok provides a secure HTTPS tunnel for local development

## Support

For assistance, please contact [enrico.sagnelli@outlook.com]