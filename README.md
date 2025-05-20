# Supplier Invoice Insertion

Automates the ingestion of supplier invoices sent by email directly into Microsoft Dynamics NAV/Business Central (Navision), eliminating manual intervention. The system fetches emails with PDF attachments, extracts QR code data to identify vendor and invoice numbers, validates vendors against Navision, checks for duplicate invoices, and uses OpenAI GPT to suggest appropriate GL accounts.

## Features

* **Email Fetching**: Retrieves emails with PDF attachments from a designated mailbox using Microsoft Graph API .
* **PDF & QR Extraction**: Extracts text from PDFs and decodes embedded QR codes to obtain invoice metadata .
* **Vendor Validation**: Matches vendor NIFs from QR data against Navision’s vendor registry .
* **Duplicate Detection**: Checks if an invoice has already been registered in Navision based on past invoice history .
* **GL Account Suggestion**: Leverages OpenAI’s GPT-4 model to recommend a 6-digit GL account based on vendor history and invoice content .
* **Debug Logging**: Saves intermediate DataFrames and GPT prompts for troubleshooting .

---

## Repository Structure

```
├── .env                         # Environment variables configuration :contentReference[oaicite:11]{index=11}:contentReference[oaicite:12]{index=12}
├── requirements.txt             # Python dependencies :contentReference[oaicite:13]{index=13}:contentReference[oaicite:14]{index=14}
├── config/
│   ├── graph_api.py             # Microsoft Graph API client :contentReference[oaicite:15]{index=15}:contentReference[oaicite:16]{index=16}
│   └── navision_api.py          # Navision OData API client :contentReference[oaicite:17]{index=17}:contentReference[oaicite:18]{index=18}
├── src/
│   └── core/
│       ├── pdf_reader.py        # Extract text from PDF :contentReference[oaicite:19]{index=19}:contentReference[oaicite:20]{index=20}
│       ├── qr_reader.py         # Decode QR codes in PDF :contentReference[oaicite:21]{index=21}:contentReference[oaicite:22]{index=22}
│       ├── email_reader.py      # Filter emails for PDFs :contentReference[oaicite:23]{index=23}:contentReference[oaicite:24]{index=24}
│       ├── vendor_validation.py # Validate NIFs against Navision :contentReference[oaicite:25]{index=25}:contentReference[oaicite:26]{index=26}
│       ├── invoice_validation.py# Detect new vs. duplicate invoices :contentReference[oaicite:27]{index=27}:contentReference[oaicite:28]{index=28}
│       ├── openai_client.py     # GPT-based GL suggestion :contentReference[oaicite:29]{index=29}:contentReference[oaicite:30]{index=30}
│       └── debug_gpt_inputs.py  # Logging helper functions :contentReference[oaicite:31]{index=31}:contentReference[oaicite:32]{index=32}
├── scripts/
│   ├── merged_df.py             # Debug merged DataFrame dump :contentReference[oaicite:33]{index=33}:contentReference[oaicite:34]{index=34}
│   ├── test_merged.py           # Test merged invoices retrieval :contentReference[oaicite:35]{index=35}:contentReference[oaicite:36]{index=36}
│   └── test.py                  # End-to-end invoice processing demo :contentReference[oaicite:37]{index=37}:contentReference[oaicite:38]{index=38}
└── README.md                    # This file
```

---

## Prerequisites

* **Python**: ≥ 3.9
* **Microsoft Azure App**: Registered for client credentials flow.
* **Navision Access**: NTLM credentials with read/write permissions.
* **OpenAI API Key**: With access to GPT-4 or compatible model.

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-org/supplier-invoice-insertion.git
   cd supplier-invoice-insertion
   ```
2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   > *Note: Additional dependencies such as `pandas`, `pdfplumber`, `opencv-python`, `pyzbar`, `scikit-learn`, `openai`, `python-dotenv`, `requests`, and `requests_ntlm` may be required if not already included.*

---

## Configuration

Copy the provided `.env` template and fill in your credentials and endpoints:

```dotenv
TENANT_ID=…
CLIENT_ID=…
CLIENT_SECRET=…
USER_EMAIL=…
SENDER_EMAIL=…
DESTINATION_EMAIL=["a@domain.com","b@domain.com"]
GRAPH_API_BASE_URL=https://graph.microsoft.com/v1.0
SUBSCRIPTION_URL=https://graph.microsoft.com/v1.0/subscriptions
WEBHOOK_PORT=5048
WEBHOOK_URL=https://your-public-url/webhook
NAVISION_BASE_URL=http://your-nav-server:7048/BC140/ODataV4/Company('YourCompany')
NAVISION_USERNAME=…
NAVISION_PASSWORD=…
NAVISION_DOMAIN=…
GPT_KEY=…
```



---

## Usage

1. **Fetch and process invoices**
   Run the end-to-end demo script:

   ```bash
   python scripts/test.py
   ```

   This will:

   * Fetch today’s emails from `SENDER_EMAIL`.
   * Extract QR data and validate vendors.
   * Check for duplicates in Navision.
   * Generate GL account suggestions via GPT.
   * Save debug CSVs under `data/debug/`.

2. **Webhook Listener (Optional)**
   Implement a small HTTP server at `WEBHOOK_PORT` to receive Microsoft Graph change notifications at `WEBHOOK_URL` and trigger processing routines.

3. **Unit & Integration Tests**

   ```bash
   python scripts/test_merged.py
   ```

   Ensures Navision data retrieval and merging behave as expected.

---

## Debugging

* **DataFrame Dumps**: Intermediate DataFrames are saved as CSVs in `data/debug/` via `debug_save_df()` .
* **GPT Prompts**: Raw prompts sent to OpenAI are logged for inspection via `debug_log_gpt_input()` .

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/XYZ`)
3. Commit your changes (`git commit -m 'Add XYZ'`)
4. Push to the branch (`git push origin feature/XYZ`)
5. Open a Pull Request

---

## License

[MIT License](LICENSE)

---

*Last updated: May 19, 2025*
