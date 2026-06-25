import os
import json
import logging
import threading
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore, storage

logger = logging.getLogger(__name__)

_firebase_app = None
_lock = threading.Lock()

def init_firebase() -> Optional[firebase_admin.App]:
    """
    Initializes the Firebase Admin SDK thread-safely.
    Loads credentials from the environment variables in the following priority order:
    1. FIREBASE_CREDENTIALS_JSON (raw service account JSON string)
    2. FIREBASE_CREDENTIALS_PATH (path to a credentials JSON file)
    3. Application Default Credentials (ADC)
    """
    global _firebase_app
    
    if _firebase_app is not None:
        return _firebase_app
        
    with _lock:
        # Double-check inside lock
        if _firebase_app is not None:
            return _firebase_app
            
        cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
        
        cred = None
        
        # 1. Try loading from raw JSON string
        if cred_json:
            try:
                cred_info = json.loads(cred_json)
                cred = credentials.Certificate(cred_info)
                logger.info("Initializing Firebase using credentials JSON from environment.")
            except Exception as e:
                logger.warning("Failed to load Firebase credentials from FIREBASE_CREDENTIALS_JSON: %s", e)
                
        # 2. Try loading from credentials file path
        if not cred and cred_path:
            if os.path.exists(cred_path):
                try:
                    cred = credentials.Certificate(cred_path)
                    logger.info("Initializing Firebase using credentials file from path: %s", cred_path)
                except Exception as e:
                    logger.warning("Failed to load Firebase credentials from path %s: %s", cred_path, e)
            else:
                logger.warning("FIREBASE_CREDENTIALS_PATH path does not exist: %s", cred_path)
                
        # 3. Fallback to Application Default Credentials (ADC)
        if not cred:
            try:
                cred = credentials.ApplicationDefault()
                logger.info("Initializing Firebase using Application Default Credentials (ADC).")
            except Exception as e:
                logger.warning("Application Default Credentials not available: %s. Falling back to default app initialization.", e)
                cred = None
                
        options = {}
        if bucket_name:
            options["storageBucket"] = bucket_name
            logger.info("Firebase storage bucket configured: %s", bucket_name)
            
        try:
            # Ensure Firebase has not been initialized previously
            if not firebase_admin._apps:
                _firebase_app = firebase_admin.initialize_app(cred, options)
                logger.info("Firebase Admin SDK initialized successfully.")
            else:
                _firebase_app = firebase_admin.get_app()
                logger.info("Firebase Admin SDK already initialized. Using existing default app instance.")
        except Exception as e:
            logger.error("Failed to initialize Firebase Admin SDK: %s", e)
            raise RuntimeError(f"Failed to initialize Firebase Admin SDK: {e}")
            
        return _firebase_app


def get_firestore():
    """
    Returns an initialized Firestore client instance.
    """
    init_firebase()
    return firestore.client()


def get_storage_bucket():
    """
    Returns an initialized Firebase Storage bucket instance.
    """
    init_firebase()
    return storage.bucket()
