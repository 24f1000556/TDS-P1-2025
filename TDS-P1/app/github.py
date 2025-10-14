# app/github_utils.py
import os
from github import Github
from github import GithubException
import httpx
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = os.getenv("GITHUB_USERNAME")
g = Github(GITHUB_TOKEN)

def create_repo(repo_name: str, description: str = ""):
    """
    Create a public repository with the given name.
    """
    user = g.get_user()
    # if repo exists, return it
    try:
        repo = user.get_repo(repo_name)
        print("Repo already exists:", repo.full_name)
        return repo
    except GithubException:
        pass

    repo = user.create_repo(
        name=repo_name,
        description=description,
        private=False,
        auto_init=False,
        license_template="mit"  
    )
    print("Created repo:", repo.full_name)
    return repo

def create_or_update_file(repo, path: str, content: str, message: str):
    """
    Create a file or update if it already exists.
    """
    try:
        # Try to get file to see if exists
        current = repo.get_contents(path)
        sha = current.sha
        repo.update_file(path, message, content, sha)
        print(f"Updated {path} in {repo.full_name}")
    except GithubException as e:
        # If 404 (not found) then create
        if e.status == 404:
            repo.create_file(path, message, content)
            print(f"Created {path} in {repo.full_name}")
        else:
            # some other error
            raise


def create_or_update_binary_file(repo, path: str, binary_content, commit_message: str):
    """
    Create or update a binary file in the repository.
    This function handles binary data like images directly without encoding/decoding.
    """
    try:
        # Try to get file to see if exists
        try:
            current = repo.get_contents(path)
            # Update existing file
            repo.update_file(
                path=path,
                message=commit_message,
                content=binary_content,
                sha=current.sha
            )
            print(f"Updated binary file {path} in {repo.full_name}")
        except GithubException as e:
            # If file doesn't exist, create it
            if e.status == 404:
                repo.create_file(
                    path=path,
                    message=commit_message,
                    content=binary_content
                )
                print(f"Created binary file {path} in {repo.full_name}")
            else:
                # some other error
                raise
        return True
    except Exception as e:
        print(f"Error creating/updating binary file {path}: {e}")
        return False

def enable_pages(repo_name: str, branch: str = "main"):
    """
    Enable GitHub Pages via REST API; expects GITHUB_USERNAME in env.
    """
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/pages"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"source": {"branch": branch, "path": "/"}}
    try:
        r = httpx.post(url, headers=headers, json=data, timeout=30.0)
        if r.status_code in (201, 204):
            print("✅ Pages enabled for", repo_name)
            return True
        else:
            # GitHub sometimes returns 202 while building; treat 202 as success to allow polling
            print("Pages API returned:", r.status_code, r.text)
            return False
    except Exception as e:
        print("Failed to call Pages API:", e)
        return False

def generate_mit_license(owner_name=None):
    year = datetime.utcnow().year
    owner = owner_name or USERNAME or "Owner"
    return f"""
    MIT License
    
    Copyright (c) {year} {owner}

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

    """
