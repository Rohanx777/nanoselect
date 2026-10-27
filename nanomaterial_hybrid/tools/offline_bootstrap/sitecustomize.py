"""Only loaded by final verification children through their private PYTHONPATH."""
import os

if os.environ.get("NANOMATERIAL_OFFLINE_VERIFY")=="1":
    from src.offline_guard import install
    install()
