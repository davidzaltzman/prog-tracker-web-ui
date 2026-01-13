from flask import Flask, render_template, request, redirect
import os, requests, base64

app = Flask(__name__)

GITHUB_USER = "davidzaltzman"
REPO_NAME = "ForumNotifier2"
FILE_PATH = "threads.txt"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

edit_target = None  # זיכרון זמני לעריכה

def read_file():
    url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return "", "", r.text
    data = r.json()
    return base64.b64decode(data["content"]).decode(), data["sha"], None

def write_file(content, sha, msg):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_PATH}"
    payload = {
        "message": msg,
        "content": base64.b64encode(content.encode()).decode(),
        "sha": sha
    }
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    requests.put(url, json=payload, headers=headers)

def parse_threads(edit_url=None):
    content, _, _ = read_file()
    threads = []

    for line in content.splitlines():
        paused = line.startswith("[PAUSED]")
        clean = line.replace("[PAUSED]", "").strip()
        parts = [p.strip() for p in clean.split("|")]
        if len(parts) < 2:
            continue

        threads.append({
            "title": parts[0],
            "url": parts[1],
            "paused": paused,
            "edit": edit_url == parts[1]
        })

    return threads

@app.route("/")
def home():
    return render_template("index.html", threads=parse_threads(edit_target))

@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title", "").strip()
    url = request.form.get("url", "").strip()

    if not title:
        return "❌ חובה לתת שם לאשכול"

    content, sha, _ = read_file()
    if url in content:
        return "❌ האשכול כבר קיים"

    new_line = f"{title} | {url} | {request.form['bg_message']} | {request.form['bg_quote']} | {request.form['bg_spoiler']}"
    content = content.rstrip() + "\n" + new_line + "\n"
    write_file(content, sha, f"Add thread: {title}")
    return redirect("/")

@app.route("/toggle", methods=["POST"])
def toggle():
    target = request.form["url"]
    content, sha, _ = read_file()
    lines = []

    for line in content.splitlines():
        raw = line.replace("[PAUSED]", "").strip()
        if target in raw:
            if line.startswith("[PAUSED]"):
                lines.append(raw)
            else:
                lines.append("[PAUSED] " + raw)
        else:
            lines.append(line)

    write_file("\n".join(lines) + "\n", sha, "Toggle thread")
    return redirect("/")

@app.route("/edit-title", methods=["POST"])
def edit_title():
    global edit_target
    edit_target = request.form["url"]
    return redirect("/")

@app.route("/save-title", methods=["POST"])
def save_title():
    global edit_target
    new_title = request.form["new_title"].strip()
    target = request.form["url"]

    if not new_title:
        return "❌ שם לא יכול להיות ריק"

    content, sha, _ = read_file()
    lines = []

    for line in content.splitlines():
        paused = line.startswith("[PAUSED]")
        clean = line.replace("[PAUSED]", "").strip()
        parts = [p.strip() for p in clean.split("|")]

        if len(parts) >= 2 and parts[1] == target:
            rest = " | ".join(parts[1:])
            new_line = f"{new_title} | {rest}"
            if paused:
                new_line = "[PAUSED] " + new_line
            lines.append(new_line)
        else:
            lines.append(line)

    write_file("\n".join(lines) + "\n", sha, "Edit thread title")
    edit_target = None
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
