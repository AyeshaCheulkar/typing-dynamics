"""
pythonanywhere_wsgi.py — TEMPLATE for the PythonAnywhere WSGI config file.

On PythonAnywhere you do NOT run `python app.py`. Instead the site is served by
a WSGI file located at:
    /var/www/<yourusername>_pythonanywhere_com_wsgi.py

Open that file (Web tab → "WSGI configuration file"), DELETE its contents, and
paste the block below — editing the two lines marked CHANGE THIS.
"""

import os
import sys

# 1) CHANGE THIS to the folder you uploaded the project into.
#    e.g. /home/ayesha/typing-dynamics
project_home = "/home/YOURUSERNAME/typing-dynamics"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 2) CHANGE THIS password. This is what unlocks /admin and the CSV export.
#    The username defaults to "admin" unless you set ADMIN_USER too.
os.environ["ADMIN_USER"] = "admin"
os.environ["ADMIN_PASSWORD"] = "PUT-A-STRONG-PASSWORD-HERE"

# Import the Flask app. PythonAnywhere looks for a variable named `application`.
from app import app as application
