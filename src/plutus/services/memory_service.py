"""
Memory Service - Phase 3 Advanced Feature
=========================================

This service manages conversation memory and context persistence across
sessions. It enables Plutus to remember previous conversations, track
user progress, and provide continuity in financial coaching.

Key Capabilities:
1. Conversation history persistence
2. User insights and preferences storage
3. Goal progress tracking over time
4. Recommendation follow-up and effectiveness
5. Learning from user feedback
6. Context continuity across sessions
"""

import logging
import json
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import asyncio

from ..core.config import get_config
from ..models.state import ConversationState

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Service for managing conversation memory and user insights over time.
    
    This service provides long-term memory capabilities that enable Plutus
    to build relationships with users and improve advice over time.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.config = get_config()
        self.db_path = db_path or self.config.memory_db_path or "plutus_memory.db"
        self._init_database()
        
        # Memory retention policies
        self.retention_policies = {
            "conversations": timedelta(days=90),  # 3 months
            "insights": timedelta(days=365),      # 1 year
            "preferences": timedelta(days=730),   # 2 years
            "goal_progress": timedelta(days=1095) # 3 years
        }
        
        # In-memory cache for recent data
        self._conversation_cache = {}
        self._insight_cache = {}
        self._cache_ttl = timedelta(minutes=30)
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    user_message TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    agent_results TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User insights table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_insights (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    insight_type TEXT NOT NULL,
                    insight_data TEXT NOT NULL,
                    confidence_score REAL,
                    source TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    preference_key TEXT NOT NULL,
                    preference_value TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, preference_key)
                )
            """)
            
            # Goal progress table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goal_progress (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    goal_id TEXT NOT NULL,
                    progress_data TEXT NOT NULL,
                    milestone_type TEXT,
                    recorded_at DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Recommendation tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_tracking (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    recommendation_id TEXT NOT NULL,
                    recommendation_data TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    user_feedback TEXT,
                    effectiveness_score REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_session ON conversations(user_id, session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_user_type ON user_insights(user_id, insight_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_preferences_user ON user_preferences(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_goal_progress_user_goal ON goal_progress(user_id, goal_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendation_tracking_user ON recommendation_tracking(user_id)")
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Memory database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize memory database: {e}")
            raise
    
    async def store_conversation(
        self, 
        user_id: str, 
        session_id: str, 
        user_message: str,
        assistant_response: str,
        agent_results: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> str:
        """Store conversation in memory"""
        
        try:
            conversation_id = f"conv_{user_id}_{session_id}_{datetime.utcnow().timestamp()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO conversations 
                (id, user_id, session_id, timestamp, user_message, assistant_response, agent_results, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                user_id,
                session_id,
                datetime.utcnow().isoformat(),
                user_message,
                assistant_response,
                json.dumps(agent_results),
                json.dumps(metadata)
            ))
            
            conn.commit()
            conn.close()
            
            # Extract insights from conversation
            await self._extract_insights_from_conversation(
                user_id, user_message, assistant_response, agent_results
            )
            
            logger.info(f"📝 Stored conversation {conversation_id}")
            return conversation_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store conversation: {e}")
            raise
    
    async def get_conversation_history(
        self, 
        user_id: str, 
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve conversation history for user"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if session_id:
                cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE user_id = ? AND session_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (user_id, session_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            conversations = []
            
            for row in rows:
                conv_dict = dict(zip(columns, row))
                # Parse JSON fields
                conv_dict["agent_results"] = json.loads(conv_dict["agent_results"] or "[]")
                conv_dict["metadata"] = json.loads(conv_dict["metadata"] or "{}")
                conversations.append(conv_dict)
            
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Failed to get conversation history: {e}")
            return []
    
    async def store_user_insight(
        self, 
        user_id: str, 
        insight_type: str,
        insight_data: Dict[str, Any],
        confidence_score: float = 1.0,
        source: str = "conversation"
    ) -> str:
        """Store user insight for future reference"""
        
        try:
            insight_id = f"insight_{user_id}_{insight_type}_{datetime.utcnow().timestamp()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_insights 
                (id, user_id, insight_type, insight_data, confidence_score, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                insight_id,
                user_id,
                insight_type,
                json.dumps(insight_data),
                confidence_score,
                source
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"💡 Stored insight {insight_type} for user {user_id}")
            return insight_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store insight: {e}")
            raise
    
    async def get_user_insights(
        self, 
        user_id: str, 
        insight_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve user insights"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if insight_type:
                cursor.execute("""
                    SELECT * FROM user_insights 
                    WHERE user_id = ? AND insight_type = ?
                    ORDER BY updated_at DESC
                """, (user_id, insight_type))
            else:
                cursor.execute("""
                    SELECT * FROM user_insights 
                    WHERE user_id = ?
                    ORDER BY updated_at DESC
                """, (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            insights = []
            
            for row in rows:
                insight_dict = dict(zip(columns, row))
                insight_dict["insight_data"] = json.loads(insight_dict["insight_data"])
                insights.append(insight_dict)
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Failed to get user insights: {e}")
            return []
    
    async def store_user_preference(
        self, 
        user_id: str, 
        preference_key: str, 
        preference_value: Any
    ) -> None:
        """Store user preference"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Use REPLACE to handle updates
            cursor.execute("""
                REPLACE INTO user_preferences 
                (id, user_id, preference_key, preference_value, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"pref_{user_id}_{preference_key}",
                user_id,
                preference_key,
                json.dumps(preference_value),
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"⚙️ Stored preference {preference_key} for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store preference: {e}")
            raise
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Retrieve user preferences"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT preference_key, preference_value 
                FROM user_preferences 
                WHERE user_id = ?
            """, (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            preferences = {}
            for key, value in rows:
                preferences[key] = json.loads(value)
            
            return preferences
            
        except Exception as e:
            logger.error(f"❌ Failed to get user preferences: {e}")
            return {}
    
    async def track_goal_progress(
        self, 
        user_id: str, 
        goal_id: str, 
        progress_data: Dict[str, Any],
        milestone_type: Optional[str] = None
    ) -> str:
        """Track progress toward a financial goal"""
        
        try:
            progress_id = f"progress_{user_id}_{goal_id}_{datetime.utcnow().timestamp()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO goal_progress 
                (id, user_id, goal_id, progress_data, milestone_type, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                progress_id,
                user_id,
                goal_id,
                json.dumps(progress_data),
                milestone_type,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"📈 Tracked goal progress for {goal_id}")
            return progress_id
            
        except Exception as e:
            logger.error(f"❌ Failed to track goal progress: {e}")
            raise
    
    async def get_goal_progress_history(
        self, 
        user_id: str, 
        goal_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get goal progress history"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if goal_id:
                cursor.execute("""
                    SELECT * FROM goal_progress 
                    WHERE user_id = ? AND goal_id = ?
                    ORDER BY recorded_at DESC
                """, (user_id, goal_id))
            else:
                cursor.execute("""
                    SELECT * FROM goal_progress 
                    WHERE user_id = ?
                    ORDER BY recorded_at DESC
                """, (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            progress_history = []
            
            for row in rows:
                progress_dict = dict(zip(columns, row))
                progress_dict["progress_data"] = json.loads(progress_dict["progress_data"])
                progress_history.append(progress_dict)
            
            return progress_history
            
        except Exception as e:
            logger.error(f"❌ Failed to get goal progress history: {e}")
            return []
    
    async def track_recommendation(
        self, 
        user_id: str, 
        recommendation_id: str,
        recommendation_data: Dict[str, Any]
    ) -> None:
        """Track a recommendation given to user"""
        
        try:
            tracking_id = f"rec_track_{user_id}_{recommendation_id}_{datetime.utcnow().timestamp()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO recommendation_tracking 
                (id, user_id, recommendation_id, recommendation_data)
                VALUES (?, ?, ?, ?)
            """, (
                tracking_id,
                user_id,
                recommendation_id,
                json.dumps(recommendation_data)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"🎯 Tracking recommendation {recommendation_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to track recommendation: {e}")
            raise
    
    async def update_recommendation_status(
        self, 
        user_id: str, 
        recommendation_id: str,
        status: str,
        user_feedback: Optional[str] = None,
        effectiveness_score: Optional[float] = None
    ) -> None:
        """Update recommendation status based on user feedback"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE recommendation_tracking 
                SET status = ?, user_feedback = ?, effectiveness_score = ?, updated_at = ?
                WHERE user_id = ? AND recommendation_id = ?
            """, (
                status,
                user_feedback,
                effectiveness_score,
                datetime.utcnow().isoformat(),
                user_id,
                recommendation_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"📊 Updated recommendation {recommendation_id} status to {status}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update recommendation status: {e}")
            raise
    
    async def get_conversation_context(
        self, 
        user_id: str, 
        session_id: str,
        lookback_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get recent conversation context for continuity"""
        
        try:
            # Get recent conversations
            cutoff_time = datetime.utcnow() - timedelta(minutes=lookback_minutes)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_message, assistant_response, agent_results, metadata
                FROM conversations 
                WHERE user_id = ? AND session_id = ? AND timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 5
            """, (user_id, session_id, cutoff_time.isoformat()))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Build context
            context = {
                "recent_messages": [],
                "discussed_topics": set(),
                "mentioned_goals": set(),
                "risk_factors_identified": set(),
                "recommendations_given": []
            }
            
            for row in rows:
                user_msg, assistant_resp, agent_results_json, metadata_json = row
                
                context["recent_messages"].append({
                    "user": user_msg,
                    "assistant": assistant_resp
                })
                
                # Extract topics and entities
                agent_results = json.loads(agent_results_json or "[]")
                for result in agent_results:
                    agent_type = result.get("agent_type", "")
                    analysis = result.get("analysis", {})
                    
                    if agent_type == "goal_extraction":
                        extracted_goals = analysis.get("extracted_goals", [])
                        for goal in extracted_goals:
                            context["mentioned_goals"].add(goal.get("type", ""))
                    
                    elif agent_type == "risk_assessment":
                        risk_factors = analysis.get("primary_risk_factors", [])
                        for factor in risk_factors:
                            context["risk_factors_identified"].add(factor.get("category", ""))
                    
                    elif agent_type == "recommendation":
                        recommendations = result.get("recommendations", [])
                        context["recommendations_given"].extend([r.get("title", "") for r in recommendations])
            
            # Convert sets to lists for JSON serialization
            context["discussed_topics"] = list(context["discussed_topics"])
            context["mentioned_goals"] = list(context["mentioned_goals"])
            context["risk_factors_identified"] = list(context["risk_factors_identified"])
            
            return context
            
        except Exception as e:
            logger.error(f"❌ Failed to get conversation context: {e}")
            return {"recent_messages": [], "discussed_topics": [], "mentioned_goals": [], "risk_factors_identified": [], "recommendations_given": []}
    
    async def _extract_insights_from_conversation(
        self, 
        user_id: str, 
        user_message: str,
        assistant_response: str,
        agent_results: List[Dict[str, Any]]
    ) -> None:
        """Extract insights from conversation for future reference"""
        
        try:
            insights_to_store = []
            
            # Extract goal-related insights
            for result in agent_results:
                if result.get("agent_type") == "goal_extraction":
                    extracted_goals = result.get("analysis", {}).get("extracted_goals", [])
                    if extracted_goals:
                        insights_to_store.append({
                            "type": "user_goals",
                            "data": {"goals": extracted_goals, "extracted_from": user_message},
                            "confidence": 0.8
                        })
                
                elif result.get("agent_type") == "risk_assessment":
                    risk_profile = result.get("analysis", {}).get("risk_profile", "")
                    risk_score = result.get("analysis", {}).get("overall_risk_score", 0)
                    if risk_profile:
                        insights_to_store.append({
                            "type": "risk_profile",
                            "data": {"profile": risk_profile, "score": risk_score},
                            "confidence": 0.9
                        })
                
                elif result.get("agent_type") == "recommendation":
                    recommendations = result.get("recommendations", [])
                    if recommendations:
                        insights_to_store.append({
                            "type": "preferences",
                            "data": {"recommendations_shown": [r.get("title", "") for r in recommendations]},
                            "confidence": 0.7
                        })
            
            # Store insights
            for insight in insights_to_store:
                await self.store_user_insight(
                    user_id,
                    insight["type"],
                    insight["data"],
                    insight["confidence"],
                    "conversation_analysis"
                )
        
        except Exception as e:
            logger.error(f"❌ Failed to extract insights: {e}")
    
    async def cleanup_old_data(self) -> None:
        """Clean up old data based on retention policies"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clean up based on retention policies
            for table, retention_period in self.retention_policies.items():
                cutoff_date = datetime.utcnow() - retention_period
                
                if table == "conversations":
                    cursor.execute("""
                        DELETE FROM conversations 
                        WHERE timestamp < ?
                    """, (cutoff_date.isoformat(),))
                
                elif table == "insights":
                    cursor.execute("""
                        DELETE FROM user_insights 
                        WHERE created_at < ?
                    """, (cutoff_date.isoformat(),))
                
                # Similar cleanup for other tables...
            
            conn.commit()
            rows_affected = conn.total_changes
            conn.close()
            
            logger.info(f"🧹 Cleaned up {rows_affected} old memory records")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old data: {e}")


# Global memory service instance
_memory_service = None

def get_memory_service() -> MemoryService:
    """Get memory service singleton"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service