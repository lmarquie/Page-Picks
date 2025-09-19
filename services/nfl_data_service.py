import httpx
import asyncio
from typing import List, Dict, Optional
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class NFLDataService:
    def __init__(self):
        self.api_key = os.getenv("NFL_API_KEY")
        self.base_url = os.getenv("NFL_API_BASE_URL", "https://api.nfl.com/v1")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def get_players(self, team: Optional[str] = None) -> List[Dict]:
        """Fetch all NFL players or players from a specific team"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/players"
                params = {"team": team} if team else {}
                
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                return response.json().get("players", [])
        except Exception as e:
            logger.error(f"Error fetching players: {e}")
            return []
    
    async def get_player_stats(self, player_id: str, season: int, week: Optional[int] = None) -> List[Dict]:
        """Fetch player statistics for a specific season and week"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/players/{player_id}/stats"
                params = {"season": season}
                if week:
                    params["week"] = week
                
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                return response.json().get("stats", [])
        except Exception as e:
            logger.error(f"Error fetching player stats for {player_id}: {e}")
            return []
    
    async def get_games(self, season: int, week: Optional[int] = None) -> List[Dict]:
        """Fetch games for a specific season and week"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/games"
                params = {"season": season}
                if week:
                    params["week"] = week
                
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                return response.json().get("games", [])
        except Exception as e:
            logger.error(f"Error fetching games: {e}")
            return []
    
    async def get_current_season(self) -> int:
        """Get the current NFL season year"""
        current_year = datetime.now().year
        # NFL season typically starts in September
        if datetime.now().month >= 9:
            return current_year
        else:
            return current_year - 1
    
    async def get_recent_games(self, weeks: int = 20) -> List[Dict]:
        """Get recent games for the last N weeks"""
        current_season = await self.get_current_season()
        all_games = []
        
        # Get current week and work backwards
        current_week = await self.get_current_week()
        
        for week_offset in range(weeks):
            week = current_week - week_offset
            if week <= 0:
                # Move to previous season
                season = current_season - 1
                week = 18 + week  # NFL regular season has 18 weeks
            else:
                season = current_season
            
            games = await self.get_games(season, week)
            all_games.extend(games)
        
        return all_games
    
    async def get_current_week(self) -> int:
        """Get the current NFL week"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/schedule/current"
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                data = response.json()
                return data.get("week", 1)
        except Exception as e:
            logger.error(f"Error fetching current week: {e}")
            return 1

# Mock data service for development/testing when API is not available
class MockNFLDataService:
    def __init__(self):
        self.mock_players = [
            {
                "id": "1",
                "name": "CeeDee Lamb",
                "position": "WR",
                "team": "DAL",
                "jersey_number": 88,
                "height": "6'2\"",
                "weight": 200,
                "age": 24,
                "college": "Oklahoma",
                "years_pro": 4
            },
            {
                "id": "2", 
                "name": "Josh Allen",
                "position": "QB",
                "team": "BUF",
                "jersey_number": 17,
                "height": "6'5\"",
                "weight": 237,
                "age": 27,
                "college": "Wyoming",
                "years_pro": 6
            }
        ]
        
        self.mock_stats = [
            {
                "player_id": "1",
                "game_id": "1",
                "receiving_yards": 125.5,
                "receptions": 8,
                "targets": 12,
                "receiving_touchdowns": 1,
                "week": 1,
                "season": 2024
            },
            {
                "player_id": "1", 
                "game_id": "2",
                "receiving_yards": 89.0,
                "receptions": 6,
                "targets": 9,
                "receiving_touchdowns": 0,
                "week": 2,
                "season": 2024
            }
        ]
    
    async def get_players(self, team: Optional[str] = None) -> List[Dict]:
        if team:
            return [p for p in self.mock_players if p["team"] == team]
        return self.mock_players
    
    async def get_player_stats(self, player_id: str, season: int, week: Optional[int] = None) -> List[Dict]:
        stats = [s for s in self.mock_stats if s["player_id"] == player_id and s["season"] == season]
        if week:
            stats = [s for s in stats if s["week"] == week]
        return stats
    
    async def get_games(self, season: int, week: Optional[int] = None) -> List[Dict]:
        return [
            {
                "id": "1",
                "season": season,
                "week": week or 1,
                "home_team": "DAL",
                "away_team": "PHI",
                "home_score": 28,
                "away_score": 24,
                "game_date": "2024-09-08T20:00:00Z"
            }
        ]
    
    async def get_current_season(self) -> int:
        return 2024
    
    async def get_current_week(self) -> int:
        return 5
    
    async def get_recent_games(self, weeks: int = 20) -> List[Dict]:
        games = []
        for i in range(weeks):
            games.extend(await self.get_games(2024, i + 1))
        return games


