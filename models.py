from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class Position(enum.Enum):
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    K = "K"
    DEF = "DEF"

class StatType(enum.Enum):
    PASSING_YARDS = "passing_yards"
    RUSHING_YARDS = "rushing_yards"
    RECEIVING_YARDS = "receiving_yards"
    RECEPTIONS = "receptions"
    TOUCHDOWNS = "touchdowns"
    INTERCEPTIONS = "interceptions"
    FUMBLES = "fumbles"

class LineType(enum.Enum):
    OVER_UNDER = "over_under"
    SPREAD = "spread"
    MONEYLINE = "moneyline"
    PROPS = "props"

class Player(Base):
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, index=True)
    nfl_id = Column(String(50), unique=True, index=True)
    name = Column(String(100), nullable=False)
    position = Column(Enum(Position), nullable=False)
    team = Column(String(10), nullable=False)
    jersey_number = Column(Integer)
    height = Column(String(10))
    weight = Column(Integer)
    age = Column(Integer)
    college = Column(String(100))
    years_pro = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    stats = relationship("PlayerStats", back_populates="player")
    betting_lines = relationship("BettingLine", back_populates="player")

class Game(Base):
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    nfl_game_id = Column(String(50), unique=True, index=True)
    season = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    game_type = Column(String(20), nullable=False)  # regular, playoff, super_bowl
    home_team = Column(String(10), nullable=False)
    away_team = Column(String(10), nullable=False)
    home_score = Column(Integer)
    away_score = Column(Integer)
    game_date = Column(DateTime(timezone=True), nullable=False)
    weather_conditions = Column(String(100))
    stadium = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    stats = relationship("PlayerStats", back_populates="game")
    betting_lines = relationship("BettingLine", back_populates="game")

class PlayerStats(Base):
    __tablename__ = "player_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    
    # Passing stats
    passing_yards = Column(Float, default=0)
    passing_attempts = Column(Integer, default=0)
    passing_completions = Column(Integer, default=0)
    passing_touchdowns = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    passing_rating = Column(Float, default=0)
    
    # Rushing stats
    rushing_yards = Column(Float, default=0)
    rushing_attempts = Column(Integer, default=0)
    rushing_touchdowns = Column(Integer, default=0)
    
    # Receiving stats
    receiving_yards = Column(Float, default=0)
    receptions = Column(Integer, default=0)
    receiving_touchdowns = Column(Integer, default=0)
    targets = Column(Integer, default=0)
    
    # General stats
    fumbles = Column(Integer, default=0)
    fumbles_lost = Column(Integer, default=0)
    
    # Fantasy points (calculated)
    fantasy_points = Column(Float, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    player = relationship("Player", back_populates="stats")
    game = relationship("Game", back_populates="stats")

class BettingLine(Base):
    __tablename__ = "betting_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)  # Null for team lines
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    
    line_type = Column(Enum(LineType), nullable=False)
    stat_type = Column(Enum(StatType), nullable=True)  # For prop bets
    line_value = Column(Float, nullable=False)  # The actual line (e.g., 100.5 yards)
    over_odds = Column(Float)  # Decimal odds for over
    under_odds = Column(Float)  # Decimal odds for under
    sportsbook = Column(String(50), nullable=False)
    
    # Result tracking
    actual_value = Column(Float)  # What actually happened
    hit_over = Column(Boolean)  # Did the over hit?
    hit_under = Column(Boolean)  # Did the under hit?
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    player = relationship("Player", back_populates="betting_lines")
    game = relationship("Game", back_populates="betting_lines")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    subscription_tier = Column(String(20), default="free")  # free, basic, premium
    subscription_expires = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


