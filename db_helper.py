import os
import mysql.connector
from dotenv import load_dotenv
from utils import get_safe_secret
def get_db_connection():
    load_dotenv()
    # 1. Try to get secrets from Environment Variables first (Always works locally & in Actions)
    # This avoids triggering Streamlit's internal logic entirely if not needed
    host = os.environ.get("DB_HOST")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    database = os.environ.get("DB_NAME")
    port = os.environ.get("DB_PORT", 4000)
    print(f"DEBUG: Attempting to connect to host: {host}")
   
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database="test",
            port=int(port),
            ssl_disabled=False
        )
        return conn
    except Exception as e:
        # This will force the error to show in your terminal
        print(f"CRITICAL ERROR: Connection failed with: {e}")
        raise e
    
    # 2. Only if the env variables are missing, try to use Streamlit
    if not host:
        try:
            import streamlit as st
            host = st.secrets.get("DB_HOST")
            user = st.secrets.get("DB_USER")
            password = st.secrets.get("DB_PASSWORD")
            database = st.secrets.get("DB_NAME")
            port = st.secrets.get("DB_PORT", 4000)
        except Exception:
            # If Streamlit is not available or secrets are missing, we stay silent
            pass

    # 3. Create the connection
    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database="test",
        port=int(port),
        ssl_disabled=False
    )
def get_db_connection_config():
    """Returns configuration dictionary for connection pooling in app.py"""
    # We no longer need load_dotenv() here because get_safe_secret handles it
    return {
        "host": get_safe_secret("DB_HOST"),
        "user": get_safe_secret("DB_USER"),
        "password": get_safe_secret("DB_PASSWORD"),
        "database": get_safe_secret("DB_NAME"), # You can put "test" as default in get_safe_secret or here
        "port": int(get_safe_secret("DB_PORT") or 4000),
        "ssl_disabled": False
    }