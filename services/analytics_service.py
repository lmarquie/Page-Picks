from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from models import Player, PlayerStats, BettingLine, StatType, LineType
from datetime import datetime, timedelta
import statistics

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_player_line_analysis(self, player_id: int, stat_type: StatType, 
                                line_value: float, games_back: int = 20) -> Dict:
        """
        Analyze how often a player has hit a specific line over the past N games
        
        Example: How often has CeeDee Lamb exceeded 100 receiving yards in the past 20 games?
        """
        # Get player's recent games and stats
        recent_stats = self._get_recent_player_stats(player_id, stat_type, games_back)
        
        if not recent_stats:
            return {
                "player_id": player_id,
                "stat_type": stat_type.value,
                "line_value": line_value,
                "games_analyzed": 0,
                "hit_rate": 0.0,
                "total_hits": 0,
                "average_value": 0.0,
                "median_value": 0.0,
                "games": []
            }
        
        # Calculate hit rate
        hits = sum(1 for stat in recent_stats if stat >= line_value)
        hit_rate = hits / len(recent_stats) if recent_stats else 0.0
        
        # Calculate additional statistics
        values = [stat for stat in recent_stats if stat is not None]
        avg_value = statistics.mean(values) if values else 0.0
        median_value = statistics.median(values) if values else 0.0
        
        # Prepare game-by-game breakdown
        games_breakdown = self._get_games_breakdown(player_id, stat_type, games_back)
        
        return {
            "player_id": player_id,
            "stat_type": stat_type.value,
            "line_value": line_value,
            "games_analyzed": len(recent_stats),
            "hit_rate": round(hit_rate * 100, 2),  # Percentage
            "total_hits": hits,
            "average_value": round(avg_value, 2),
            "median_value": round(median_value, 2),
            "games": games_breakdown
        }
    
    def get_multiple_line_analysis(self, player_id: int, stat_type: StatType, 
                                  line_values: List[float], games_back: int = 20) -> Dict:
        """
        Analyze hit rates for multiple line values for the same player/stat
        """
        results = {}
        
        for line_value in line_values:
            analysis = self.get_player_line_analysis(player_id, stat_type, line_value, games_back)
            results[f"line_{line_value}"] = analysis
        
        return {
            "player_id": player_id,
            "stat_type": stat_type.value,
            "games_analyzed": analysis["games_analyzed"],
            "line_analyses": results
        }
    
    def get_position_analysis(self, position: str, stat_type: StatType, 
                             line_value: float, games_back: int = 20) -> Dict:
        """
        Analyze how often players at a specific position hit a line
        """
        # Get all players at this position
        players = self.db.query(Player).filter(Player.position == position).all()
        
        position_analyses = []
        for player in players:
            analysis = self.get_player_line_analysis(player.id, stat_type, line_value, games_back)
            if analysis["games_analyzed"] > 0:  # Only include players with data
                position_analyses.append({
                    "player_id": player.id,
                    "player_name": player.name,
                    "team": player.team,
                    "hit_rate": analysis["hit_rate"],
                    "games_analyzed": analysis["games_analyzed"]
                })
        
        # Sort by hit rate
        position_analyses.sort(key=lambda x: x["hit_rate"], reverse=True)
        
        return {
            "position": position,
            "stat_type": stat_type.value,
            "line_value": line_value,
            "total_players": len(position_analyses),
            "players": position_analyses
        }
    
    def get_team_analysis(self, team: str, stat_type: StatType, 
                          line_value: float, games_back: int = 20) -> Dict:
        """
        Analyze how often players from a specific team hit a line
        """
        # Get all players from this team
        players = self.db.query(Player).filter(Player.team == team).all()
        
        team_analyses = []
        for player in players:
            analysis = self.get_player_line_analysis(player.id, stat_type, line_value, games_back)
            if analysis["games_analyzed"] > 0:
                team_analyses.append({
                    "player_id": player.id,
                    "player_name": player.name,
                    "position": player.position.value,
                    "hit_rate": analysis["hit_rate"],
                    "games_analyzed": analysis["games_analyzed"]
                })
        
        # Sort by hit rate
        team_analyses.sort(key=lambda x: x["hit_rate"], reverse=True)
        
        return {
            "team": team,
            "stat_type": stat_type.value,
            "line_value": line_value,
            "total_players": len(team_analyses),
            "players": team_analyses
        }
    
    def _get_recent_player_stats(self, player_id: int, stat_type: StatType, 
                                games_back: int) -> List[float]:
        """Get recent stat values for a player"""
        # Get recent games (last N games)
        recent_games = self._get_recent_games(games_back)
        game_ids = [game.id for game in recent_games]
        
        # Get player stats for these games
        stats_query = self.db.query(PlayerStats).filter(
            PlayerStats.player_id == player_id,
            PlayerStats.game_id.in_(game_ids)
        ).order_by(PlayerStats.game_id.desc())
        
        stats = stats_query.all()
        
        # Extract the specific stat value
        stat_values = []
        for stat in stats:
            value = self._extract_stat_value(stat, stat_type)
            if value is not None:
                stat_values.append(value)
        
        return stat_values
    
    def _get_games_breakdown(self, player_id: int, stat_type: StatType, 
                            games_back: int) -> List[Dict]:
        """Get game-by-game breakdown for a player"""
        recent_games = self._get_recent_games(games_back)
        game_ids = [game.id for game in recent_games]
        
        # Get player stats with game info
        stats_query = self.db.query(PlayerStats, Game).join(Game).filter(
            PlayerStats.player_id == player_id,
            PlayerStats.game_id.in_(game_ids)
        ).order_by(Game.game_date.desc())
        
        games_breakdown = []
        for stat, game in stats_query.all():
            value = self._extract_stat_value(stat, stat_type)
            games_breakdown.append({
                "game_id": game.id,
                "week": game.week,
                "season": game.season,
                "opponent": self._get_opponent(game, stat.player.team),
                "stat_value": value,
                "game_date": game.game_date.isoformat()
            })
        
        return games_breakdown
    
    def _get_recent_games(self, games_back: int):
        """Get the most recent N games"""
        return self.db.query(Game).order_by(Game.game_date.desc()).limit(games_back).all()
    
    def _extract_stat_value(self, stat: PlayerStats, stat_type: StatType) -> Optional[float]:
        """Extract the specific stat value from PlayerStats object"""
        stat_mapping = {
            StatType.PASSING_YARDS: stat.passing_yards,
            StatType.RUSHING_YARDS: stat.rushing_yards,
            StatType.RECEIVING_YARDS: stat.receiving_yards,
            StatType.RECEPTIONS: stat.receptions,
            StatType.TOUCHDOWNS: stat.passing_touchdowns + stat.rushing_touchdowns + stat.receiving_touchdowns,
            StatType.INTERCEPTIONS: stat.interceptions,
            StatType.FUMBLES: stat.fumbles
        }
        
        return stat_mapping.get(stat_type)
    
    def _get_opponent(self, game: Game, player_team: str) -> str:
        """Get the opponent team for a player"""
        if game.home_team == player_team:
            return game.away_team
        else:
            return game.home_team


