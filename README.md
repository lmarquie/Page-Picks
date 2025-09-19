# 🏈 Page Picks NFL Analytics

A comprehensive NFL analytics platform for player performance analysis and betting insights.

## 🌐 Live Website

**Deploy this to Railway, Render, or Vercel to get a live website!**

## 🚀 Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
python working_api.py

# Visit http://localhost:8000/demo
```

### Deploy to Web
1. Follow the [DEPLOYMENT.md](DEPLOYMENT.md) guide
2. Deploy to Railway (recommended) or Render
3. Get your live website URL!

## ✨ Features

- **Real-time 2025 NFL data** - Updated weekly
- **Player analysis** - Hit rates, trends, performance metrics
- **Smart picks** - AI-powered betting recommendations
- **Injury tracking** - Automatically excludes injured players
- **Team change filtering** - Excludes players who changed teams
- **Interactive demo** - Beautiful web interface

## 📊 Data Sources

- **nflverse** - Official NFL play-by-play data
- **ESPN** - Real-time injury reports
- **FantasyPros** - Team change tracking

## 🔄 Updates

Run `python update_2025_and_injuries.py` weekly to get the latest data.

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python
- **Database**: SQLite (production: PostgreSQL)
- **Frontend**: HTML, CSS, JavaScript
- **Data**: Pandas, BeautifulSoup, Requests
- **Deployment**: Railway/Render/Vercel

## 📈 API Endpoints

- `GET /` - Home page
- `GET /demo` - Interactive demo
- `GET /api/players` - List all players
- `GET /api/picks/best` - Get best picks
- `GET /api/analytics/trending` - Trending players
- `GET /health` - Health check

## 🎯 Perfect For

- Fantasy football players
- Sports bettors
- NFL analysts
- Data enthusiasts
- Anyone who loves football!

---

**Ready to deploy? Check out [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step instructions!** 🚀