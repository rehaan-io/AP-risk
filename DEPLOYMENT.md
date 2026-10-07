# Deployment Guide: AP Risk Intelligence

This document provides exact, step-by-step instructions to deploy the AP Risk Intelligence project for production.

**Architecture Summary:**
*   **Source Code**: GitHub
*   **Backend**: Render (Web Service)
*   **Database**: PostgreSQL on Render
*   **Frontend**: Netlify

---

## Phase 1: GitHub Preparation

We have prepared the repository with a strict `.gitignore` to prevent any `.env` files, node modules, or local caches from being committed.

1.  Open your terminal in the project root directory.
2.  Initialize the git repository (if not already done):
    ```bash
    git init
    ```
3.  Add and commit all files:
    ```bash
    git add .
    git commit -m "Initial commit for deployment"
    ```
4.  Create a new repository on [GitHub](https://github.com/).
5.  Link your local repository and push:
    ```bash
    git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
    git branch -M main
    git push -u origin main
    ```

---

## Phase 2: Render Database & Backend Deployment

### A. Create the PostgreSQL Database
1.  Log in to [Render](https://render.com/).
2.  Click **New +** and select **PostgreSQL**.
3.  Name it (e.g., `ap-risk-db`).
4.  Choose the Free or Pro tier.
5.  Click **Create Database**.
6.  Once created, copy the **Internal Database URL** (if deploying backend on Render) or **External Database URL**.

### B. Create the Backend Service
1.  Click **New +** and select **Web Service**.
2.  Connect your GitHub repository.
3.  Configure the service:
    *   **Name**: `ap-risk-backend`
    *   **Root Directory**: `backend` (Important: Set this so Render builds the backend folder).
    *   **Environment**: `Python 3`
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`

### C. Set Backend Environment Variables
In the Render Web Service settings, click **Environment** and add the following:

| Key | Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | *(Paste Render DB URL)* | Change `postgres://` to `postgresql+asyncpg://` |
| `GEMINI_API_KEY` | *(Your Gemini Key)* | Secret key for AI extraction/explanation |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | *(Your Azure Endpoint)* | e.g. https://your-resource.cognitiveservices.azure.com/ |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | *(Your Azure Key)* | Secret key for document extraction |
| `CORS_ORIGINS` | `https://your-frontend.netlify.app` | Leave blank for now, update after Netlify deployment |

4.  Click **Deploy / Save Changes**.
5.  Once deployed, verify it works by visiting `https://your-backend-url.onrender.com/health`. You should see `{"status": "ok"}`.

### D. Initialize the Database
Render does not run migrations automatically. Since we use `create_all`, we can run our initialization script:
1. Go to your Render Web Service dashboard.
2. Click the **Shell** tab.
3. Run the following command to create tables and insert the default config:
   ```bash
   python aggressive_clean.py
   ```
   *(Note: This completely drops and rebuilds the DB. Only run this once upon initial deployment).*

---

## Phase 3: Netlify Frontend Deployment

### A. Prepare the Frontend
We have updated the frontend code so that all API requests dynamically point to `VITE_API_URL` instead of hardcoded `localhost:8000`.

### B. Deploy to Netlify
1.  Log in to [Netlify](https://www.netlify.com/).
2.  Click **Add new site** -> **Import an existing project**.
3.  Connect to GitHub and select your repository.
4.  Configure the build settings:
    *   **Base directory**: `frontend`
    *   **Build command**: `npm run build`
    *   **Publish directory**: `frontend/dist`
5.  Click **Add environment variables**:
    *   **Key**: `VITE_API_URL`
    *   **Value**: `https://your-backend-url.onrender.com` (No trailing slash)
6.  Click **Deploy site**.

### C. SPA Routing Fix (Netlify)
React Router requires server redirects to handle direct URL visits (like `/exceptions`). We have generated a `_redirects` file handling this. Netlify will automatically process it.

---

## Phase 4: Final Connection (CORS)

For security, the backend rejects unauthorized frontend URLs.
1.  Copy your new Netlify URL (e.g., `https://ap-risk-123.netlify.app`).
2.  Go back to **Render** -> **Web Service** -> **Environment**.
3.  Update the `CORS_ORIGINS` variable:
    *   `CORS_ORIGINS = https://ap-risk-123.netlify.app`
4.  Render will automatically restart the backend.

**Deployment Complete!**
You can now visit your Netlify URL and use the AP Risk Intelligence system in full production.

---

## System Capabilities in Production

*   **File Storage**: 100% cloud-native. The backend processes ZIP file uploads in memory (`io.BytesIO`) using `asyncio` streams. We do not require persistent file storage volumes, meaning Render's ephemeral disk limitation does not affect us.
*   **Background Tasks**: The system correctly utilizes FastAPI `BackgroundTasks` for long-running document extractions.
*   **Real-time Progress**: Server-Sent Events (SSE) stream perfectly across CORS via standard HTTP connections.
