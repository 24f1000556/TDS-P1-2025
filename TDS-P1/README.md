# 🤖 LLM Code Deployment

This project automates the **build, deployment, and revision** of small applications using **LLM-assisted generation**. It receives structured requests, generates a minimal web app using an LLM, and deploys to GitHub Pages.

---

## 🚀 Overview

**LLM Code Deployment** is a system that:
1. **Builds** — Receives a JSON request describing an app to build, verifies secrets, generates and deploys a GitHub Pages app.
2. **Revises** — Receives a second round of updates and redeploys the improved version.

---

## 🧠 Features

- 🔐 **Secret verification** for secure task handling  
- ⚙️ **LLM-assisted app generation**  
- 🌐 **Automatic GitHub Pages deployment**  
- 📦 **Attachment parsing** (images, CSV, Markdown, etc.)  
- 🔁 **Round-based revision system**  
- 🪶 **MIT License & clean repo structure**

---

## 🧩 Project Flow

### 🏗️ Build Phase
1. Receives a JSON POST request (via `/api-endpoint`).
2. Verifies the shared secret.
3. Generates a new minimal web app using an LLM.
4. Creates a **GitHub repo** named after the task (e.g., `captcha-solver-...`).
5. Pushes files (`index.html`, `README.md`, `LICENSE`).
6. Enables **GitHub Pages**.

### 🔁 Revise Phase
1. Accepts a second request with updated brief (e.g., add new feature).
2. Verifies secret again.
3. Updates the existing repo.
4. Redeploys to GitHub Pages.

---

## 🛠️ Tech Stack

- **FastAPI** – Backend API  
- **Uvicorn** – ASGI server  
- **OpenAI API (LLM)** – App generation  
- **GitHub REST API / CLI** – Repo creation and deployment  
- **Python 3.13**  
- **JSON-based task system**

---

## ⚙️ Setup Instructions

### 1️⃣ Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```
### 2️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 🌐 Environment Variables
#### Before running the project, you need to set the following environment variables in a .env file or your shell:
```bash
# GitHub
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_USERNAME=your_github_username

# OpenAI
OPENAI_API_KEY=your_openai_api_key
USER_SECRET=your_secret_for_tasks
OPENAI_BASE_URL=https://aipipe.onai/v1
```

### 3️⃣ Run the Server
```bash
uvicorn app.main:app --reload
```
### The API will be accessible at:
```bash
http://127.0.0.1:8000
```

---

### 🧪 Sending a Test Request
Example via cURL:
```bash
curl -X POST http://127.0.0.1:8000/api-endpoint \
     -H "Content-Type: application/json" \
     -d '{
           "email": "student@example.com",
           "secret": "yoursecret",
           "task": "sample-task",
           "round": 1,
           "nonce": "unique123",
           "brief": "Create a simple Hello World app."
         }'
```
