# Deploying to PythonAnywhere (free, always-on)

This hosts the Typing Dynamics platform 24/7 so your friends can fill it in from
anywhere, using your existing SQLite database. Takes ~15 minutes.

Your friends will use:   `https://YOURUSERNAME.pythonanywhere.com/`
You (researcher) will use: `https://YOURUSERNAME.pythonanywhere.com/admin`

---

## 1. Create a free account
Go to <https://www.pythonanywhere.com> → **Pricing & signup** → **Create a Beginner
account** (free). Pick a username — it becomes your web address, so choose something
sensible (e.g. `ayeshastudy`).

## 2. Get the project onto the server (via GitHub — recommended)
The code lives at <https://github.com/AyeshaCheulkar/typing-dynamics> (public).

Open a **Bash console** (Consoles tab → Bash) and run:
```bash
cd ~
git clone https://github.com/AyeshaCheulkar/typing-dynamics.git
cd typing-dynamics
ls        # you should see app.py, db.py, templates/, static/ ...
```

*Updating later* is then just: `cd ~/typing-dynamics && git pull` → **Reload** (step 7).

<details><summary>Alternative: upload deploy.zip instead of git</summary>

1. **Files** tab → **Upload a file** → upload `deploy.zip` to your home folder.
2. In a Bash console:
   ```bash
   mkdir -p ~/typing-dynamics && cd ~/typing-dynamics && unzip ~/deploy.zip
   ```
</details>

## 3. Install Flask
In the same Bash console:
```bash
pip install --user flask
```

## 4. Create the web app
1. Go to the **Web** tab → **Add a new web app** → **Next**.
2. Choose **Manual configuration** (NOT "Flask") → **Next**.
3. Choose **Python 3.10** (or the highest 3.x offered) → **Next**.
4. It creates the app and shows a settings page. Leave it for the next step.

## 5. Point it at the app + set your admin password
1. On the **Web** tab, find **"WSGI configuration file"** and click the link
   (it looks like `/var/www/YOURUSERNAME_pythonanywhere_com_wsgi.py`).
2. **Delete everything** in that file.
3. Open **`pythonanywhere_wsgi.py`** from your uploaded project, copy its contents,
   and paste them in.
4. Edit the two marked lines:
   - `project_home = "/home/YOURUSERNAME/typing-dynamics"` → put your real username.
   - `os.environ["ADMIN_PASSWORD"] = "..."` → choose a strong password.
5. **Save** (green button).

## 6. (Recommended) Serve static files efficiently
Still on the **Web** tab, under **"Static files"**, add:
| URL        | Directory                                   |
|------------|---------------------------------------------|
| `/static/` | `/home/YOURUSERNAME/typing-dynamics/static` |

## 7. Launch
Click the big green **Reload** button at the top of the Web tab.
Open `https://YOURUSERNAME.pythonanywhere.com/` — the writing page should load.

---

## Using it
- **Share with friends:** send them `https://YOURUSERNAME.pythonanywhere.com/`
  Ask each person to use a **consistent Participant ID** (e.g. P01, P02 …).
- **Check data / download:** go to `.../admin`. Your browser will ask for a
  username (`admin`) and the password you set. From there you can read every
  response, include/exclude sessions, and **Download CSV**.

## Getting your data back
- Easiest: `/admin` → **Download CSV**.
- Full database: **Files** tab → open `typing-dynamics/` → download `data.db`.

## Updating the app later
Re-upload changed files (Files tab) or `git pull`, then hit **Reload** on the Web tab.

## Notes / limits (free tier)
- Free accounts occasionally need you to click "Run until 3 months from now" to keep
  the app alive — PythonAnywhere emails a reminder. Fine for a short study.
- SQLite handles ~10 participants easily. The database persists across reloads.
- Debug mode is OFF in this setup (the WSGI server ignores `app.run`), so the app is
  safe to expose. `/admin`, the CSV export and raw session JSON are all password-locked.
