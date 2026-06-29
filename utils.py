import os
import streamlit as st

def get_safe_secret(key):
    # 1. First, check if Streamlit is actually running in a way that supports secrets
    if hasattr(st, 'secrets'):
        try:
            # We attempt to access the key. 
            # If the secrets.toml file is missing, this will trigger the error
            # which we catch immediately below.
            return st.secrets[key]
        except Exception:
            # If it fails (because no secrets.toml exists), we just ignore the error
            pass
            
    # 2. Fallback: Always look in environment variables (your .env file)
    return os.getenv(key)