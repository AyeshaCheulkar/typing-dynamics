"""
prototype_wsgi.py — WSGI configuration for the Prototype Platform on PythonAnywhere.

Copy and paste this into your PythonAnywhere WSGI file:
/var/www/ayeshacheulkar_pythonanywhere_com_wsgi.py
"""
import os
import sys

# Paths: prototype folder + project root
home = os.path.expanduser("~")
project_root = os.path.join(home, "typing-dynamics")
proto_dir = os.path.join(project_root, "prototype_platform")

# Add prototype_platform first so that 'import app' finds prototype_platform/app.py
for p in [proto_dir, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.chdir(proto_dir)

# Admin credentials for the prototype platform
os.environ["PROTO_ADMIN_USER"] = "admin"
os.environ["PROTO_ADMIN_PASSWORD"] = "admin"
os.environ["PROTO_SECRET"] = "prototype-secret-2026-key"

from app import app as application
