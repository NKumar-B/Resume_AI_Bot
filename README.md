# Resume_AI_Bot - AI Resume & Job Description Matcher

A production-structured, multi-channel AI-powered platform supporting **Telegram Bot**, **WhatsApp Bot**, and a **FastAPI REST API** for multi-resume screening, automatic document type classification, weighted match score calculation, ATS-style keyword evaluation, 1-line improvement suggestions, and clickable course recommendations.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=flat-square&logo=fastapi&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot_API-26A5E4?style=flat-square&logo=telegram&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Cloud_API-25D366?style=flat-square&logo=whatsapp&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI%2FOpenRouter-GPT--4o--mini-412991?style=flat-square&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-4c1?style=flat-square)

---

## Key Features

- **Multi-Channel Platform**: Simultaneous support for **Telegram Bot**, **WhatsApp Bot**, and **REST API**.
- **Automatic Document Type Classification**: Smart classifier (`doc_classifier.py`) that automatically identifies whether an uploaded file or text is a **Job Description (JD)** or a **Resume/CV**, ensuring JDs are taken as JDs only and Resumes as Resumes only without state mix-ups.
- **Multi-Format Document Input**: Accepts JDs and Resumes as PDF, DOCX, or pasted plain text messages.
- **Consolidated Multi-Resume Upload**: Queue multiple candidate PDF/DOCX resumes per job description without chat spam.
- **Transparent Match Score (0–100%)**: Weighted scoring based on Skill Match (50%), Experience (20%), Project Relevance (15%), Education (10%), and ATS Alignment (5%).
- **Matched Skills Identification**: Highlights skills explicitly matched between the resume and job description.
- **Skill Mismatch & Gap Analysis**: Highlights missing required skills using neutral terminology ("Not found in resume").
- **Actionable 1-Line Improvement Suggestions**: Exactly 3 single-sentence, highly concise career improvement recommendations per candidate.
- **Targeted Course Recommendations**: Exactly 3 relevant learning resources with clickable URLs from Coursera, Udemy, edX, AWS, Microsoft, etc.
- **Final Comparative Summary**: Formatted summary table ranking all candidate resumes by match score.
- **Resilient AI Engine & Fallback**: OpenRouter / OpenAI API integration (`OPENROUTER_API_KEY`) with an automatic deterministic fallback analyzer if API limits occur.

---

## Project Structure

```text
Resume_AI_Bot/
│
├── app.py                  # FastAPI server & REST API / WhatsApp Webhook endpoints
├── telegram_bot.py         # Telegram bot handler with state machine & inline buttons
├── whatsapp_bot.py         # WhatsApp bot handler for Meta Cloud API & Twilio
├── doc_classifier.py       # Smart classifier for automatic JD vs. Resume identification
├── ai_analyzer.py          # Core AI analysis engine (OpenRouter/OpenAI & fallback)
├── resume_parser.py        # PDF & DOCX resume parser & candidate name extractor
├── jd_parser.py            # Job Description parser & title extractor
├── course_recommender.py   # Course recommendation engine with URL validation
├── formatter.py            # Telegram HTML card & summary table formatter
├── config.py               # Central environment configuration & validation
│
├── uploads/                # Temporary file upload directory
├── .env                    # Environment variables file (secrets)
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
├── requirements.txt        # Python package dependencies
└── README.md               # Project documentation
```

---

## Technologies Used

| Category | Badges |
| :--- | :--- |
| **Language** | ![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white) |
| **Web Framework** | ![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white) ![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI_Server-4051B5?style=for-the-badge&logo=uvicorn&logoColor=white) |
| **Integrations** | ![Telegram](https://img.shields.io/badge/Telegram_Bot_API-v20%2B-26A5E4?style=for-the-badge&logo=telegram&logoColor=white) ![WhatsApp](https://img.shields.io/badge/WhatsApp_Cloud_API-v19.0-25D366?style=for-the-badge&logo=whatsapp&logoColor=white) |
| **AI Engine** | ![OpenAI](https://img.shields.io/badge/OpenAI_/_OpenRouter-GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white) |
| **License** | ![License](https://img.shields.io/badge/License-MIT-4c1?style=for-the-badge) |

---

## Quick Start & Installation (Windows PowerShell)

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/NKumar-B/Resume_AI_Bot.git
   cd Resume_AI_Bot
   ```

2. **Create and activate a virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

---

## Environment Configuration

1. Copy `.env.example` to `.env`:
   ```powershell
   copy .env.example .env
   ```

2. Open `.env` and fill in your API credentials:
   ```ini
   # Telegram Bot Token (from @BotFather)
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

   # WhatsApp Cloud API (Meta WhatsApp Business API)
   WHATSAPP_API_TOKEN=your_whatsapp_cloud_api_token_here
   WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id_here
   WHATSAPP_VERIFY_TOKEN=resume_bot_verify_token

   # OpenRouter / OpenAI API Key
   OPENROUTER_API_KEY=your_openrouter_or_openai_api_key_here
   OPENAI_MODEL=openai/gpt-4o-mini

   # Server Port
   PORT=8000
   ```

---

## Running the Bots & Services

### 1. Run Telegram Bot
Start the Telegram bot polling service:
```powershell
.\.venv\Scripts\python.exe telegram_bot.py
```

### 2. Run FastAPI Server (REST API & WhatsApp Webhook)
Start the web server hosting the REST API and WhatsApp webhook endpoints:
```powershell
.\.venv\Scripts\python.exe app.py
```
*Access interactive API documentation at:* `http://localhost:8000/docs`

---

## User Workflows

### Telegram Workflow
1. Start chat with your bot on Telegram and send `/start`.
2. **Send Job Description**: Upload a PDF/DOCX file or paste text. The bot identifies it as a JD.
3. **Send Resumes**: Upload candidate PDF/DOCX resume(s). The bot updates a consolidated status card (`RESUMES QUEUED FOR ANALYSIS`).
4. Tap **`[ ⚡ ANALYZE RESUMES NOW ]`** or send `/analyze`.
5. View detailed analysis cards and the final comparative summary ranking table.

### WhatsApp Workflow
1. Send `/start` or `Hello` to your WhatsApp Business number.
2. **Send Job Description**: Send text or upload a PDF/DOCX file. The bot identifies it as a Job Description.
3. **Send Resumes**: Send candidate PDF/DOCX resume(s). The bot queues them and displays total count.
4. Send `/analyze` to execute AI match analysis.
5. Receive individual candidate analysis cards and the summary comparison table formatted in WhatsApp Markdown (`*bold*`, `•` bullets).

---

## Security & Privacy Notice

- **Isolated Sessions**: User sessions are isolated by Telegram Chat ID and WhatsApp phone number (`wa_id`).
- **Temporary Buffers**: Uploaded documents are processed in-memory and temporary local buffers.
- **Environment Isolation**: API tokens and keys are loaded securely via `.env` and excluded from git source control.

---

## License
Licensed under the MIT License.
