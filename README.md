# FinanceDesk — Loan & Credit Manager
### Flask + Railway Deployment Version

A complete loan and credit management system for small finance businesses.
Data is saved **permanently on the server** — works from any device, any browser.

---

## What's Inside

```
financedesk_railway/
├── app.py                ← Flask backend (all API routes)
├── requirements.txt      ← flask + gunicorn
├── Procfile              ← Railway/Heroku start command
├── railway.toml          ← Railway deployment config
├── .gitignore
└── templates/
    └── index.html        ← Complete frontend (HTML + CSS + JS)
```

Data is stored in a `data/` folder created automatically at runtime:
```
data/
├── clients.json
├── loans.json
├── payments.json
└── purchases.json
```

---

## Run Locally (Your Own Computer)

### Step 1 — Install Python
Download from https://python.org (version 3.8 or higher)

### Step 2 — Install dependencies
Open terminal / command prompt in this folder and run:
```bash
pip install -r requirements.txt
```

### Step 3 — Start the app
```bash
python app.py
```

### Step 4 — Open in browser
```
http://localhost:5000
```

Sample data loads automatically on first run.

---

## Deploy to Railway (Free — Access from Anywhere)

Railway gives you a live URL so you can open the app from your phone,
laptop, or any device. Data is saved on Railway's server permanently.

### Step 1 — Create GitHub account
Go to https://github.com and sign up (free)

### Step 2 — Create a new repository
- Click the **+** button → New repository
- Name it: `financedesk`
- Set to **Private** (recommended — your business data)
- Click **Create repository**

### Step 3 — Upload all project files
- Open your repository on GitHub
- Click **"uploading an existing file"**
- Drag and drop ALL files from this folder (including subfolders)
- Click **Commit changes**

### Step 4 — Create Railway account
Go to https://railway.app and sign up with GitHub (free)

### Step 5 — Deploy
- Click **"New Project"**
- Choose **"Deploy from GitHub repo"**
- Select your `financedesk` repository
- Railway automatically detects Python and starts deploying

### Step 6 — Set environment variable (important for security)
In Railway dashboard → Your project → Variables tab:
```
SECRET_KEY = choose-any-random-string-like-abc123xyz789
```

### Step 7 — Get your URL
Railway gives you a free URL like:
```
https://financedesk-production.up.railway.app
```

Open this URL on any device. **Bookmark it on your phone!**

---

## Deploy to PythonAnywhere (Alternative — Always Free)

PythonAnywhere is specifically designed for Python apps and has a
truly free tier that never expires.

### Step 1 — Sign up
Go to https://www.pythonanywhere.com and create a free account

### Step 2 — Upload files
- Dashboard → Files tab
- Create folder: `financedesk`
- Upload all project files

### Step 3 — Create Web App
- Dashboard → Web tab → Add a new web app
- Choose: Manual configuration → Python 3.10

### Step 4 — Set WSGI file
Click on the WSGI configuration file link and replace contents with:
```python
import sys
sys.path.insert(0, '/home/YOUR_USERNAME/financedesk')
from app import app as application
```
Replace `YOUR_USERNAME` with your PythonAnywhere username.

### Step 5 — Install Flask
In the Bash console:
```bash
pip install flask --user
```

### Step 6 — Reload and visit
Click **Reload** on the Web tab.
Your app is live at: `https://YOUR_USERNAME.pythonanywhere.com`

---

## Important: Data Persistence on Railway

Railway's free tier keeps your app running. Your JSON data files
persist as long as your service is deployed.

**Best practice:** Click **"⬇ Export JSON Backup"** in the sidebar
once a week. Save the ZIP file to Google Drive or your computer.

To restore from backup: replace the JSON files in the `data/` folder.

---

## Interest Formulas

**Simple Interest** (monthly rate):
```
SI = P × R × T / 100
where R = monthly rate (%), T = months elapsed
```

**Compound Interest** (annual rate):
```
A = P × (1 + R/100)^(T/12)
where R = annual rate (%), T = months elapsed
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main app |
| GET | `/health` | Health check |
| GET/POST | `/api/clients` | List / add clients |
| GET/PUT/DELETE | `/api/clients/<id>` | Get / update / delete client |
| GET | `/api/clients/<id>/history` | Full client history |
| GET/POST | `/api/loans` | List / add loans |
| DELETE | `/api/loans/<id>` | Delete loan |
| GET/POST | `/api/payments` | List / add payments |
| DELETE | `/api/payments/<id>` | Delete payment |
| GET/POST | `/api/purchases` | List / add purchases |
| PUT/DELETE | `/api/purchases/<id>` | Update / delete purchase |
| GET | `/api/dashboard` | Dashboard stats |
| GET | `/api/backup` | Download ZIP backup |

---

## Features

- ✅ Client management with Father/Husband name
- ✅ Loan tracking with collateral + multiple photos
- ✅ Simple & Compound interest (auto-calculated daily)
- ✅ Credit purchase tracking with overdue alerts
- ✅ Repayment recording and history
- ✅ Full client timeline
- ✅ PDF export with record selection
- ✅ Camera capture for photos
- ✅ Dashboard with live stats
- ✅ ZIP backup download
- ✅ Works on mobile and desktop
