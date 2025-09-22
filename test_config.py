#!/usr/bin/env python3
"""
Test script to verify configuration is loaded correctly
"""

import os
from news_fetcher.config import (
    MAX_ARTICLES_PER_SOURCE, REQUEST_DELAY, MODEL, EMBEDDING_MODEL,
    OUTPUT_DIR, ANALYSIS_DIR, VECTOR_DB_DIR, TIMEOUT
)

def test_configuration():
    """Test that configuration is loaded correctly"""
    print("🔧 Configuration Test")
    print("=" * 40)
    
    config_values = {
        "MAX_ARTICLES_PER_SOURCE": MAX_ARTICLES_PER_SOURCE,
        "REQUEST_DELAY": REQUEST_DELAY,
        "MODEL": MODEL,
        "EMBEDDING_MODEL": EMBEDDING_MODEL,
        "OUTPUT_DIR": OUTPUT_DIR,
        "ANALYSIS_DIR": ANALYSIS_DIR,
        "VECTOR_DB_DIR": VECTOR_DB_DIR,
        "TIMEOUT": TIMEOUT
    }
    
    print("Current configuration values:")
    for key, value in config_values.items():
        env_value = os.getenv(key)
        source = "environment" if env_value is not None else "default"
        print(f"  {key}: {value} ({source})")
    
    print("\n✅ Configuration loaded successfully!")
    
    # Test directory creation
    import tempfile
    test_dirs = [OUTPUT_DIR, ANALYSIS_DIR, VECTOR_DB_DIR]
    print("\n📁 Directory accessibility:")
    for dir_path in test_dirs:
        try:
            # Try to create the directory to test permissions
            os.makedirs(dir_path, exist_ok=True)
            print(f"  ✅ {dir_path}: Accessible")
        except Exception as e:
            print(f"  ❌ {dir_path}: Error - {e}")

if __name__ == "__main__":
    test_configuration()
