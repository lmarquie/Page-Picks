#!/usr/bin/env python3
"""
Setup script for website deployment
"""

import os
import subprocess
import sys

def check_requirements():
    """Check if all requirements are installed"""
    print("🔍 Checking requirements...")
    
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import pandas
        import requests
        import beautifulsoup4
        print("✅ All requirements are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing requirement: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def test_api():
    """Test if the API starts correctly"""
    print("🧪 Testing API startup...")
    
    try:
        # Test import
        from working_api import app
        print("✅ API imports successfully")
        return True
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def create_gitignore():
    """Create .gitignore file"""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
env.bak/
venv.bak/

# Database
*.db
*.sqlite
*.sqlite3

# Downloaded data
play_by_play_2025.csv
play_by_play_2025.rds

# Environment
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Temporary files
*.tmp
*.temp
"""
    
    with open('.gitignore', 'w') as f:
        f.write(gitignore_content)
    
    print("✅ Created .gitignore file")

def main():
    """Main setup function"""
    print("🚀 Setting up Page Picks NFL Analytics for website deployment...")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Please install requirements first:")
        print("pip install -r requirements.txt")
        return
    
    # Test API
    if not test_api():
        print("\n❌ API test failed. Please check your code.")
        return
    
    # Create gitignore
    create_gitignore()
    
    print("\n✅ Setup complete!")
    print("\n📋 Next steps:")
    print("1. Create a GitHub repository")
    print("2. Upload all files to GitHub")
    print("3. Deploy to Railway or Render")
    print("4. Follow the DEPLOYMENT.md guide")
    print("\n🌐 Your NFL analytics will be live on the web!")

if __name__ == "__main__":
    main()
