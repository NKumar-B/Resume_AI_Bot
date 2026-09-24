# 🤖 Resume_AI_Bot - AI Resume & Job Description Matcher

A production-structured, full-stack AI-powered Telegram Bot and FastAPI REST API for multi-resume screening, skill match analysis, weighted match score calculation, ATS-style keyword evaluation, 1-line improvement suggestions, and clickable course recommendations.
---

## 🌟 Features

- **Multi-Format Job Description Input**: Accepts JD as PDF, DOCX, or pasted plain text message.
- **Consolidated Multi-Resume Upload**: Upload multiple candidate PDF or DOCX resumes in a single Telegram session without message spam.
- **Transparent Resume-to-JD Match Score (0–100%)**: Weighted scoring based on skill match (50%), experience (20%), project relevance (15%), education (10%), and ATS alignment (5%).
- **Detailed Score Basis & Breakdown**: Displays exact points earned for Skill Match (50), Experience (20), Projects (15), Education (10), and ATS Alignment (5).
- **Matched Skills Identification**: Identifies explicit skills present in both JD and resume.
- **Skill Mismatch & Gaps**: Highlights missing required skills using neutral wording ("Not found in resume").
- **Actionable 1-Line Improvement Suggestions**: Exactly 3 concise, single-sentence career improvement recommendations per candidate.
- **Targeted Course Recommendations**: Exactly 3 relevant learning resources with clickable URLs from reputable providers (Coursera, Udemy, edX, AWS, Microsoft, etc.).
- **Final Comparative Summary**: Formatted summary table ranking all processed candidates by match score.
- **Interactive Telegram Buttons**: Tap-to-analyze buttons (`[ ⚡ ANALYZE RESUMES NOW ]`, `[ 🔄 Start New Job Description ]`).
- **AI Engine with Resilient Fallback**: Supports OpenRouter / OpenAI API (`OPENROUTER_API_KEY`) with an automatic fast heuristic fallback system if AI API rate limits or delays occur.
- **Decoupled Architecture & REST API**: Core AI analysis engine is independent of Telegram, exposed via FastAPI (`POST /analyze`) for future React/WhatsApp/Discord integrations.

---

## 📁 Project Structure

```
Resume_AI_Bot/
│
├── app.py                  # FastAPI application entrypoint & REST API server
├── telegram_bot.py         # Telegram bot implementation with state machine & inline buttons
├── ai_analyzer.py          # Core AI analysis engine (OpenRouter/OpenAI & fallback)
├── resume_parser.py        # PDF & DOCX resume parser & candidate name detector
├── jd_parser.py            # Job Description parser & text normalizer
├── course_recommender.py   # Course recommendation engine with URL validation
├── formatter.py            # Telegram HTML formatting for cards & summary tables
├── config.py               # Environment configuration & validation
│
├── uploads/                # Temporary file uploads directory
├── .env                    # Environment variables file (secrets)
├── .env.example            # Environment variables example template
├── .gitignore              # Git ignore rules
├── requirements.txt        # Python package dependencies
└── README.md               # Project documentation
```

---

## 🚀 Quick Start & Installation (Windows PowerShell)

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

3. **Install required dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

---

## 🔑 Environment Configuration

1. Copy `.env.example` to `.env`:
   ```powershell
   copy .env.example .env
   ```

2. Open `.env` in your text editor and fill in your credentials:
   ```ini
   # Telegram Bot Token (Obtained from @BotFather)
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

   # OpenRouter or OpenAI API Key
   OPENROUTER_API_KEY=your_openrouter_or_openai_api_key_here

   # Model selection (e.g. openrouter/free or openai/gpt-4o-mini)
   OPENROUTER_MODEL=openrouter/free

   # Server Port
   PORT=8000
   ```

---

## 🤖 How to Create a Telegram Bot

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot` to BotFather.
3. Choose a name for your bot (e.g., `AI Resume Matcher`).
4. Choose a username ending in `bot` (e.g., `NithinResumeMatcherBot`).
5. Copy the HTTP API token provided by BotFather into your `.env` file as `TELEGRAM_BOT_TOKEN`.

---

## 🏃 Running the Application

### Option A: Run Telegram Bot
To start the Telegram bot in polling mode:
```powershell
.\.venv\Scripts\python.exe telegram_bot.py
```

### Option B: Run FastAPI Web Server
To start the REST API server:
```powershell
.\.venv\Scripts\python.exe app.py
```
*Or using uvicorn directly:*
```powershell
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
Access the interactive API documentation at: `http://localhost:8000/docs`

---

## 📱 Telegram Mobile Workflow

1. Open **Telegram** on your mobile phone and search for your bot (e.g., `@NithinResumeMatcherBot`).
2. Send **/start** to initialize the session.
3. **Upload Job Description**: Upload a PDF/DOCX file or paste text directly.
4. **Upload Resumes**: Use the paperclip icon 📎 to upload candidate PDF or DOCX resume(s). The bot dynamically updates a single status card with file names and count (`RESUMES QUEUED FOR ANALYSIS`).
5. Tap **`[ ⚡ ANALYZE RESUMES NOW ]`** to execute analysis.
6. Review each candidate's card (Match Score, Score Breakdown, Matched Skills, Skill Mismatches, 3 Concise 1-Line Suggestions, and 3 Clickable Course Links).
7. Review the **Final Candidate Comparison Summary Table**.

---

## 🔒 Security & Privacy Notice

- **Temporary Processing**: Uploaded files are parsed in temporary buffers and are not permanently stored or published.
- **Session Isolation**: Each Telegram user has an isolated session. Candidate data is never shared across users.
- **API Keys Protection**: Sensitive keys (`TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`) are stored in `.env` and ignored by `.gitignore`.

---

## ☁️ Deployment to Render

To deploy this application to Render:

1. Create a new **Web Service** or **Background Worker** on [Render.com](https://render.com).
2. Connect your GitHub repository: `https://github.com/NKumar-B/Resume_AI_Bot.git`
3. Set Environment details:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command (for Telegram Bot)**: `python telegram_bot.py`
   - **Start Command (for Web API)**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables in Render settings:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENROUTER_API_KEY`
   - `OPENROUTER_MODEL`
