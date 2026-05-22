# Deploy to Streamlit Community Cloud

Target URL: https://gkbillingagent.streamlit.app

## 1) Push to GitHub
Streamlit Community Cloud deploys from a public (or approved private) GitHub repo.

- Create a GitHub repo (or use an existing one)
- Commit and push this project

Required files already added:
- `streamlit_app.py` (Streamlit entrypoint)
- `requirements.txt` (root)
- `.streamlit/config.toml`

## 2) Create the Streamlit app
1. Go to https://share.streamlit.io/
2. Click **New app**
3. Select your repo + branch
4. Set **Main file path** to:
   - `streamlit_app.py`
5. Set **App URL** (app name/subdomain) to:
   - `gkbillingagent`

After deploy, the global link will be:
- https://gkbillingagent.streamlit.app

## 3) Configure secrets (OpenAI key, etc.)
Do **not** commit `.env` with secrets.

In Streamlit Cloud:
1. Open your app settings
2. Add secrets under **Secrets** (they become environment variables)

Example:
```toml
OPENAI_API_KEY = "..."
PINECONE_API_KEY = "..."
ORACLE_HOST = "..."
```

## 4) Notes / constraints
- Streamlit Community Cloud is designed for web apps, not long-running FastAPI servers.
- This project’s Streamlit UI runs the agent in-process (no separate server required).
- `pyttsx3` voice output typically won’t work in Streamlit Cloud (no local audio device). Keep voice mode for local runs.

## 5) Local run (Streamlit)
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Then open:
- http://localhost:8501
