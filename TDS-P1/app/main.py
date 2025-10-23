from fastapi import FastAPI, Request, BackgroundTasks
import os, json, base64, logging
from threading import Lock
from dotenv import load_dotenv

from app.llm_generator import generate_app_code, decode_attachments
from app.github import (
    create_repo,
    create_or_update_file,
    create_or_update_binary_file,
    enable_pages,
    generate_mit_license,
)
from app.notify import notify_evaluation_server

# === Load environment ===
load_dotenv()
USER_SECRET = os.getenv("USER_SECRET")
USERNAME = os.getenv("GITHUB_USERNAME")

# === Constants ===
PROCESSED_PATH = "/tmp/processed_requests.json"
lock = Lock()

# === FastAPI app ===
app = FastAPI(title="Auto App Generator", version="2.0")

# === Logging ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# === Persistence helpers ===
def load_processed():
    """Load already processed request info."""
    if os.path.exists(PROCESSED_PATH):
        try:
            with open(PROCESSED_PATH) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_processed(data):
    """Save processed requests safely."""
    with lock:
        with open(PROCESSED_PATH, "w") as f:
            json.dump(data, f, indent=2)

# === Background process ===
def process_request(data):
    round_num = data.get("round", 1)
    task_id = data["task"]
    brief = data.get("brief", "No description provided")

    log.info(f"⚙ Starting background process for task '{task_id}' (round {round_num})")

    # Decode attachments
    attachments = data.get("attachments", [])
    saved_attachments = decode_attachments(attachments)
    log.info(f"📎 Attachments saved: {saved_attachments}")

    # Step 1: Get or create repository
    repo_description = f"Auto-generated app for task: {brief[:200]}"  # limit desc length
    repo = create_repo(task_id, description=repo_description)

    # Step 2: If round 2, fetch previous README
    prev_readme = None
    if round_num == 2:
        try:
            readme = repo.get_contents("README.md")
            prev_readme = readme.decoded_content.decode("utf-8", errors="ignore")
            log.info("📖 Loaded previous README for round 2 context.")
        except Exception:
            prev_readme = None
            log.warning("⚠ Could not load previous README; continuing without context.")

    # Step 3: Generate code using LLM
    gen = generate_app_code(
        brief,
        attachments=attachments,
        checks=data.get("checks", []),
        round_num=round_num,
        prev_readme=prev_readme,
    )

    files = gen.get("files", {})
    saved_info = gen.get("attachments", [])

    # Step 4: Round-specific logic
    if round_num == 1:
        log.info("🏗 Round 1: Creating new repository structure...")
        for att in saved_info:
            path = att["name"]
            try:
                with open(att["path"], "rb") as f:
                    content_bytes = f.read()

                # Commit text files normally
                if att["mime"].startswith("text") or path.endswith((".md", ".csv", ".json", ".txt")):
                    text = content_bytes.decode("utf-8", errors="ignore")
                    create_or_update_file(repo, path, text, f"Add attachment {path}")
                else:
                    # Commit binary + base64 backup
                    create_or_update_binary_file(repo, path, content_bytes, f"Add binary {path}")
                    b64 = base64.b64encode(content_bytes).decode("utf-8")
                    create_or_update_file(repo, f"attachments/{att['name']}.b64", b64, f"Backup {att['name']}.b64")

            except Exception as e:
                log.error(f"⚠ Attachment commit failed for {path}: {e}")

        # Add generated files
        for fname, content in files.items():
            create_or_update_file(repo, fname, content, f"Add {fname}")

    else:
        log.info("🔁 Round 2: Updating existing repository...")
        for fname, content in files.items():
            create_or_update_file(repo, fname, content, f"Update {fname} for round 2")

    # Step 5: Add MIT License
    mit_text = generate_mit_license()
    create_or_update_file(repo, "LICENSE", mit_text, "Add MIT license")

    # Step 6: Handle GitHub Pages
    if round_num == 1:
        pages_ok = enable_pages(task_id)
        pages_url = f"https://{USERNAME}.github.io/{task_id}/" if pages_ok else None
    else:
        pages_ok = True
        pages_url = f"https://{USERNAME}.github.io/{task_id}/"

    # Step 7: Commit reference
    try:
        commit_sha = repo.get_commits()[0].sha
    except Exception:
        commit_sha = None

    # Step 8: Notify evaluation server
    payload = {
        "email": data["email"],
        "task": data["task"],
        "round": round_num,
        "nonce": data["nonce"],
        "repo_url": repo.html_url,
        "commit_sha": commit_sha,
        "pages_url": pages_url,
    }

    notify_evaluation_server(data["evaluation_url"], payload)

    # Step 9: Mark request as processed
    processed = load_processed()
    key = f"{data['email']}::{data['task']}::round{round_num}::nonce{data['nonce']}"
    processed[key] = payload
    save_processed(processed)

    log.info(f"✅ Finished round {round_num} for '{task_id}'")

# === API Endpoint ===
@app.post("/api-endpoint")
async def receive_request(request: Request, background_tasks: BackgroundTasks):
    """Receive incoming requests and trigger background processing."""
    data = await request.json()
    log.info(f"📩 Received request: {data}")

    # Step 0: Verify secret
    if data.get("secret") != USER_SECRET:
        log.warning("❌ Invalid secret received.")
        return {"error": "Invalid secret"}

    # Step 1: Validate required fields
    required = ["email", "task", "round", "nonce", "evaluation_url"]
    missing = [f for f in required if f not in data]
    if missing:
        log.error(f"Missing required fields: {missing}")
        return {"error": f"Missing required fields: {', '.join(missing)}"}

    # Step 2: Prevent duplicates
    processed = load_processed()
    key = f"{data['email']}::{data['task']}::round{data['round']}::nonce{data['nonce']}"
    if key in processed:
        log.info(f"⚠ Duplicate request detected for {key}. Re-notifying.")
        prev = processed[key]
        notify_evaluation_server(data.get("evaluation_url"), prev)
        return {"status": "ok", "note": "duplicate handled & re-notified"}

    # Step 3: Background processing
    background_tasks.add_task(process_request, data)

    # Step 4: Respond immediately
    return {
        "status": "accepted",
        "task": data["task"],
        "round": data["round"],
        "note": f"Processing for round {data['round']} started in background."
    }
