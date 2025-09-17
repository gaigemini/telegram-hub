#!/usr/bin/env python3
"""
Startup script for Telegram API Hub
"""
import os
import sys
import uvicorn
from pathlib import Path

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path('.env')
    if not env_path.exists():
        print("❌ .env file not found!")
        print("Please create a .env file with the following variables:")
        print("API_ID=your_api_id")
        print("API_HASH=your_api_hash")
        print("DATABASE_URL=your_database_url")
        return False
    
    # Load and check variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['API_ID', 'API_HASH', 'DATABASE_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ Environment configuration looks good!")
    return True

def main():
    print("🚀 Starting Telegram API Hub...")
    
    # Check environment
    if not check_env_file():
        sys.exit(1)
    
    # Default configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    print(f"📡 Server will run on http://{host}:{port}")
    print(f"🔄 Auto-reload: {'enabled' if reload else 'disabled'}")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()