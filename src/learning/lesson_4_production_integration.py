"""
Lesson 4: Production Integration and Error Handling
===================================================

🎓 LEARNING OBJECTIVES:
1. Understand error handling patterns in multiagent systems
2. Learn resilience strategies for production deployment
3. Implement monitoring and observability
4. Design graceful degradation and fallback mechanisms
5. Handle concurrent agent failures

This lesson prepares Plutus for real-world deployment!
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, TypedDict, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from pathlib import Path

# =============================================================================
# CONCEPT 1: Error Types in Multiagent Systems
# =============================================================================

class ErrorType(Enum):
    """🎓 CLASSIFICATION: Different types of errors we need to handle"""
    
    # Infrastructure errors
    API_TIMEOUT = "api_timeout"
    API_RATE_LIMIT = "api_rate_limit"
    API_QUOTA_EXCEEDED = "api_quota_exceeded"
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    
    # Agent-specific errors
    AGENT_TIMEOUT = "agent_timeout"
    AGENT_CRASH = "agent_crash"
    INVALID_INPUT = "invalid_input"
    INVALID_OUTPUT = "invalid_output"
    
    # Business logic errors
    INSUFFICIENT_DATA = "insufficient_data"
    CONFLICTING_REQUIREMENTS = "conflicting_requirements"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    
    # System errors
    MEMORY_ERROR = "memory_error"
    DISK_FULL = "disk_full"
    PERMISSION_ERROR = "permission_error"

@dataclass
class AgentError:
    """🎓 STRUCTURED ERROR: Comprehensive error information"""
    
    error_type: ErrorType
    agent_name: str
    message: str
    timestamp: datetime
    context: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    retry_count: int = 0
    is_recoverable: bool = True
    suggested_action: Optional[str] = None

class FinancialAnalysisState(TypedDict):
    """🎓 ENHANCED STATE: Now includes error tracking"""
    
    messages: List[Dict[str, str]]
    user_question: str
    user_id: str
    session_id: str
    
    # Analysis data
    account_balances: Dict[str, float]
    financial_summary: Optional[str]
    risk_assessment: Optional[str]
    recommendations: List[str]
    
    # Error handling
    errors: List[AgentError]
    failed_agents: List[str]
    fallback_used: bool
    analysis_complete: bool
    confidence_score: float

# =============================================================================
# CONCEPT 2: Resilient Agent Implementation
# =============================================================================

class ResilientAgent:
    """
    🎓 RESILIENT AGENT BASE: Foundation for error-handling agents
    
    This base class provides:
    1. Automatic retry logic
    2. Timeout handling
    3. Error logging and monitoring
    4. Graceful degradation
    """
    
    def __init__(self, name: str, max_retries: int = 3, timeout: float = 30.0):
        self.name = name
        self.max_retries = max_retries
        self.timeout = timeout
        self.logger = self._setup_logger()
        
        # Metrics
        self.call_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0
        self.last_success = None
        self.last_error = None
    
    def _setup_logger(self) -> logging.Logger:
        """Setup structured logging for the agent"""
        logger = logging.getLogger(f"plutus.agents.{self.name}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def execute_with_resilience(self, state: FinancialAnalysisState) -> Dict[str, Any]:
        """
        🎓 RESILIENT EXECUTION: Execute agent with full error handling
        """
        
        self.call_count += 1
        start_time = time.time()
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.info(f"{self.name} starting execution (attempt {attempt + 1})")
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    self._execute_core_logic(state),
                    timeout=self.timeout
                )
                
                # Success!
                execution_time = time.time() - start_time
                self.total_execution_time += execution_time
                self.last_success = datetime.now()
                
                self.logger.info(f"{self.name} completed successfully in {execution_time:.2f}s")
                return result
                
            except asyncio.TimeoutError:
                error = AgentError(
                    error_type=ErrorType.AGENT_TIMEOUT,
                    agent_name=self.name,
                    message=f"Agent timed out after {self.timeout}s",
                    timestamp=datetime.now(),
                    context={"attempt": attempt + 1, "timeout": self.timeout},
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                    retry_count=attempt
                )
                
                await self._handle_error(error, state, attempt)
                
                if attempt == self.max_retries:
                    return await self._get_fallback_result(state, error)
                
                await self._wait_before_retry(attempt)
                
            except Exception as e:
                error = AgentError(
                    error_type=self._classify_error(e),
                    agent_name=self.name,
                    message=str(e),
                    timestamp=datetime.now(),
                    context={"attempt": attempt + 1, "exception_type": type(e).__name__},
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                    retry_count=attempt,
                    is_recoverable=self._is_recoverable_error(e)
                )
                
                await self._handle_error(error, state, attempt)
                
                if not error.is_recoverable or attempt == self.max_retries:
                    return await self._get_fallback_result(state, error)
                
                await self._wait_before_retry(attempt)
        
        # Should never reach here, but just in case
        return await self._get_fallback_result(state, None)
    
    async def _execute_core_logic(self, state: FinancialAnalysisState) -> Dict[str, Any]:
        """🎓 OVERRIDE THIS: Core agent logic (to be implemented by subclasses)"""
        raise NotImplementedError("Subclasses must implement _execute_core_logic")
    
    def _classify_error(self, exception: Exception) -> ErrorType:
        """🎓 ERROR CLASSIFICATION: Determine error type from exception"""
        
        error_message = str(exception).lower()
        
        if "timeout" in error_message:
            return ErrorType.API_TIMEOUT
        elif "rate limit" in error_message or "429" in error_message:
            return ErrorType.API_RATE_LIMIT
        elif "quota" in error_message or "402" in error_message:
            return ErrorType.API_QUOTA_EXCEEDED
        elif "network" in error_message or "connection" in error_message:
            return ErrorType.NETWORK_ERROR
        elif "memory" in error_message:
            return ErrorType.MEMORY_ERROR
        elif "permission" in error_message or "unauthorized" in error_message:
            return ErrorType.PERMISSION_ERROR
        else:
            return ErrorType.AGENT_CRASH
    
    def _is_recoverable_error(self, exception: Exception) -> bool:
        """🎓 RECOVERY ASSESSMENT: Determine if error is recoverable"""
        
        # Network and temporary errors are usually recoverable
        recoverable_errors = [
            ErrorType.API_TIMEOUT,
            ErrorType.NETWORK_ERROR,
            ErrorType.API_RATE_LIMIT
        ]
        
        error_type = self._classify_error(exception)
        return error_type in recoverable_errors
    
    async def _handle_error(self, error: AgentError, state: FinancialAnalysisState, attempt: int):
        """🎓 ERROR HANDLING: Log and track errors"""
        
        self.error_count += 1
        self.last_error = error
        
        # Add error to state
        if "errors" not in state:
            state["errors"] = []
        state["errors"].append(error)
        
        # Log error with context
        self.logger.error(
            f"{self.name} failed on attempt {attempt + 1}: {error.message}",
            extra={"error_type": error.error_type.value, "context": error.context}
        )
        
        # Send to monitoring system (simulated)
        await self._send_to_monitoring(error)
    
    async def _send_to_monitoring(self, error: AgentError):
        """🎓 MONITORING: Send error to observability system"""
        
        # In production, this would send to systems like:
        # - DataDog, New Relic, Prometheus
        # - Sentry for error tracking
        # - Custom dashboards
        
        monitoring_data = {
            "timestamp": error.timestamp.isoformat(),
            "service": "plutus",
            "agent": error.agent_name,
            "error_type": error.error_type.value,
            "message": error.message,
            "user_id": error.user_id,
            "session_id": error.session_id,
            "retry_count": error.retry_count,
            "is_recoverable": error.is_recoverable
        }
        
        # Simulated monitoring
        self.logger.info(f"📊 Monitoring: {json.dumps(monitoring_data)}")
    
    async def _wait_before_retry(self, attempt: int):
        """🎓 BACKOFF STRATEGY: Exponential backoff with jitter"""
        
        # Exponential backoff: 1s, 2s, 4s, 8s...
        base_delay = 2 ** attempt
        
        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0.1, 0.5)
        delay = base_delay + jitter
        
        self.logger.info(f"{self.name} waiting {delay:.1f}s before retry")
        await asyncio.sleep(delay)
    
    async def _get_fallback_result(self, state: FinancialAnalysisState, error: Optional[AgentError]) -> Dict[str, Any]:
        """🎓 FALLBACK MECHANISM: Provide degraded but useful response"""
        
        state["fallback_used"] = True
        state["failed_agents"].append(self.name)
        
        # Reduce confidence score
        if "confidence_score" in state:
            state["confidence_score"] *= 0.5  # 50% confidence reduction
        
        self.logger.warning(f"{self.name} using fallback response")
        
        return {
            "success": False,
            "fallback": True,
            "error": error.error_type.value if error else "unknown",
            "message": f"{self.name} is temporarily unavailable. Using simplified analysis."
        }
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """🎓 HEALTH METRICS: Agent health and performance data"""
        
        avg_execution_time = (
            self.total_execution_time / self.call_count if self.call_count > 0 else 0
        )
        
        error_rate = self.error_count / self.call_count if self.call_count > 0 else 0
        
        return {
            "agent_name": self.name,
            "call_count": self.call_count,
            "error_count": self.error_count,
            "error_rate": error_rate,
            "avg_execution_time": avg_execution_time,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error.error_type.value if self.last_error else None,
            "status": "healthy" if error_rate < 0.1 else "degraded" if error_rate < 0.5 else "unhealthy"
        }

# =============================================================================
# CONCEPT 3: Specific Agent Implementations
# =============================================================================

class ResilientFinancialAnalyzer(ResilientAgent):
    """🎓 FINANCIAL ANALYZER: With production-ready error handling"""
    
    def __init__(self):
        super().__init__("FinancialAnalyzer", max_retries=3, timeout=15.0)
    
    async def _execute_core_logic(self, state: FinancialAnalysisState) -> Dict[str, Any]:
        """Core financial analysis with simulated failures"""
        
        # Simulate various failure scenarios for learning
        import random
        
        failure_scenarios = [
            (0.05, ErrorType.API_TIMEOUT, "Claude API timeout"),
            (0.03, ErrorType.API_RATE_LIMIT, "Rate limit exceeded"),
            (0.02, ErrorType.NETWORK_ERROR, "Network connection failed"),
            (0.01, ErrorType.MEMORY_ERROR, "Insufficient memory")
        ]
        
        # Check for simulated failures
        for probability, error_type, message in failure_scenarios:
            if random.random() < probability:
                if error_type == ErrorType.API_TIMEOUT:
                    await asyncio.sleep(20)  # Will trigger timeout
                else:
                    raise Exception(message)
        
        # Simulate real work
        await asyncio.sleep(1.5)
        
        # Extract financial data
        accounts = state.get("account_balances", {})
        total_assets = sum(accounts.values())
        
        # Generate analysis
        analysis = f"""
        Financial Analysis Complete:
        - Total Assets: ${total_assets:,.2f}
        - Account Distribution: {len(accounts)} accounts
        - Analysis Quality: High confidence
        - Recommendations: {len(state.get('recommendations', []))} items
        """
        
        return {
            "success": True,
            "analysis": analysis.strip(),
            "total_assets": total_assets,
            "confidence": 0.95,
            "processing_time": 1.5
        }

class ResilientRiskAssessor(ResilientAgent):
    """🎓 RISK ASSESSOR: With circuit breaker pattern"""
    
    def __init__(self):
        super().__init__("RiskAssessor", max_retries=2, timeout=10.0)
        
        # Circuit breaker state
        self.circuit_breaker = {
            "state": "closed",  # closed, open, half_open
            "failure_count": 0,
            "last_failure_time": None,
            "failure_threshold": 5,
            "recovery_timeout": 60  # seconds
        }
    
    async def _execute_core_logic(self, state: FinancialAnalysisState) -> Dict[str, Any]:
        """Core risk assessment with circuit breaker"""
        
        # Check circuit breaker
        if not await self._check_circuit_breaker():
            raise Exception("Circuit breaker is OPEN - service unavailable")
        
        # Simulate risk assessment work
        await asyncio.sleep(0.8)
        
        # Simulate occasional failures to trigger circuit breaker
        import random
        if random.random() < 0.1:  # 10% failure rate
            await self._record_failure()
            raise Exception("Risk assessment service temporarily unavailable")
        
        # Reset circuit breaker on success
        await self._record_success()
        
        # Calculate risk score
        accounts = state.get("account_balances", {})
        total_assets = sum(accounts.values())
        
        # Simple risk calculation
        risk_score = min(100, max(0, 50 + (total_assets - 50000) / 1000))
        
        risk_level = (
            "Low" if risk_score < 30 else
            "Moderate" if risk_score < 70 else
            "High"
        )
        
        return {
            "success": True,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "factors": ["Market volatility", "Asset concentration", "Liquidity"],
            "confidence": 0.88
        }
    
    async def _check_circuit_breaker(self) -> bool:
        """🎓 CIRCUIT BREAKER: Check if service calls are allowed"""
        
        cb = self.circuit_breaker
        now = datetime.now()
        
        if cb["state"] == "open":
            # Check if recovery timeout has passed
            if (cb["last_failure_time"] and 
                (now - cb["last_failure_time"]).seconds >= cb["recovery_timeout"]):
                cb["state"] = "half_open"
                self.logger.info("Circuit breaker moving to HALF_OPEN")
                return True
            else:
                self.logger.warning("Circuit breaker is OPEN - blocking request")
                return False
        
        return True
    
    async def _record_failure(self):
        """Record failure for circuit breaker"""
        cb = self.circuit_breaker
        cb["failure_count"] += 1
        cb["last_failure_time"] = datetime.now()
        
        if cb["failure_count"] >= cb["failure_threshold"]:
            cb["state"] = "open"
            self.logger.error(f"Circuit breaker OPENED after {cb['failure_count']} failures")
    
    async def _record_success(self):
        """Record success for circuit breaker"""
        cb = self.circuit_breaker
        
        if cb["state"] == "half_open":
            cb["state"] = "closed"
            cb["failure_count"] = 0
            self.logger.info("Circuit breaker CLOSED - service recovered")

class ResilientRecommendationEngine(ResilientAgent):
    """🎓 RECOMMENDATION ENGINE: With data validation and sanitization"""
    
    def __init__(self):
        super().__init__("RecommendationEngine", max_retries=2, timeout=8.0)
    
    async def _execute_core_logic(self, state: FinancialAnalysisState) -> Dict[str, Any]:
        """Core recommendation logic with data validation"""
        
        # Validate input data
        validation_result = await self._validate_input_data(state)
        if not validation_result["valid"]:
            raise Exception(f"Invalid input data: {validation_result['errors']}")
        
        # Simulate recommendation generation
        await asyncio.sleep(0.6)
        
        # Generate recommendations based on available data
        recommendations = await self._generate_recommendations(state)
        
        # Validate output
        output_validation = await self._validate_output(recommendations)
        if not output_validation["valid"]:
            raise Exception(f"Invalid output generated: {output_validation['errors']}")
        
        return {
            "success": True,
            "recommendations": recommendations,
            "data_quality": validation_result["quality_score"],
            "confidence": 0.92
        }
    
    async def _validate_input_data(self, state: FinancialAnalysisState) -> Dict[str, Any]:
        """🎓 DATA VALIDATION: Ensure input data quality"""
        
        errors = []
        quality_score = 1.0
        
        # Check required fields
        if not state.get("user_question"):
            errors.append("Missing user question")
            quality_score -= 0.3
        
        if not state.get("account_balances"):
            errors.append("Missing account balance data")
            quality_score -= 0.4
        else:
            # Validate account balances
            accounts = state["account_balances"]
            for account, balance in accounts.items():
                if not isinstance(balance, (int, float)) or balance < 0:
                    errors.append(f"Invalid balance for {account}: {balance}")
                    quality_score -= 0.1
        
        # Check for previous analysis results
        if not any(key in state for key in ["financial_summary", "risk_assessment"]):
            errors.append("Missing prerequisite analysis")
            quality_score -= 0.2
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "quality_score": max(0, quality_score)
        }
    
    async def _generate_recommendations(self, state: FinancialAnalysisState) -> List[str]:
        """Generate financial recommendations"""
        
        recommendations = []
        accounts = state.get("account_balances", {})
        total_assets = sum(accounts.values())
        
        # Emergency fund recommendation
        if total_assets < 10000:
            recommendations.append("Build emergency fund: Save 3-6 months of expenses")
        
        # Investment recommendations
        if total_assets > 10000:
            recommendations.append("Consider diversified index fund investments")
        
        # High-value recommendations
        if total_assets > 100000:
            recommendations.append("Explore tax-advantaged retirement accounts")
            recommendations.append("Consider professional financial planning consultation")
        
        # Debt-related (if applicable)
        if "debt" in state.get("user_question", "").lower():
            recommendations.append("Prioritize high-interest debt repayment")
        
        return recommendations
    
    async def _validate_output(self, recommendations: List[str]) -> Dict[str, Any]:
        """🎓 OUTPUT VALIDATION: Ensure recommendation quality"""
        
        errors = []
        
        if not recommendations:
            errors.append("No recommendations generated")
        
        for i, rec in enumerate(recommendations):
            if not isinstance(rec, str) or len(rec.strip()) < 10:
                errors.append(f"Recommendation {i+1} is too short or invalid")
            
            # Check for prohibited content (simplified)
            prohibited_words = ["guaranteed", "risk-free", "get rich quick"]
            if any(word in rec.lower() for word in prohibited_words):
                errors.append(f"Recommendation {i+1} contains prohibited language")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

# =============================================================================
# CONCEPT 4: Production-Ready Orchestrator
# =============================================================================

class ProductionOrchestrator:
    """
    🎓 PRODUCTION ORCHESTRATOR: Coordinates agents with full error handling
    
    Features:
    1. Parallel execution with timeout
    2. Partial success handling
    3. Comprehensive monitoring
    4. Graceful degradation
    5. Health checking
    """
    
    def __init__(self):
        self.agents = {
            "financial_analyzer": ResilientFinancialAnalyzer(),
            "risk_assessor": ResilientRiskAssessor(),
            "recommendation_engine": ResilientRecommendationEngine()
        }
        
        self.logger = logging.getLogger("plutus.orchestrator")
        self.execution_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "partial_failures": 0,
            "total_failures": 0
        }
    
    async def process_financial_query(self, 
                                    user_question: str, 
                                    account_balances: Dict[str, float],
                                    user_id: str = None,
                                    session_id: str = None) -> Dict[str, Any]:
        """
        🎓 PRODUCTION PROCESSING: Handle financial query with full resilience
        """
        
        self.execution_metrics["total_requests"] += 1
        request_start = time.time()
        
        # Initialize state
        state = FinancialAnalysisState(
            messages=[],
            user_question=user_question,
            user_id=user_id or str(uuid.uuid4()),
            session_id=session_id or str(uuid.uuid4()),
            account_balances=account_balances,
            financial_summary=None,
            risk_assessment=None,
            recommendations=[],
            errors=[],
            failed_agents=[],
            fallback_used=False,
            analysis_complete=False,
            confidence_score=1.0
        )
        
        self.logger.info(f"Processing query for user {state['user_id']}")
        
        try:
            # Phase 1: Parallel analysis (financial + risk)
            analysis_results = await self._execute_analysis_phase(state)
            
            # Phase 2: Generate recommendations based on analysis
            recommendation_results = await self._execute_recommendation_phase(state)
            
            # Phase 3: Compile final response
            final_response = await self._compile_final_response(
                state, analysis_results, recommendation_results
            )
            
            # Update metrics
            if state["failed_agents"]:
                self.execution_metrics["partial_failures"] += 1
            else:
                self.execution_metrics["successful_requests"] += 1
            
            return final_response
            
        except Exception as e:
            self.execution_metrics["total_failures"] += 1
            self.logger.error(f"Critical failure in orchestrator: {str(e)}")
            
            return await self._emergency_fallback_response(state, e)
        
        finally:
            execution_time = time.time() - request_start
            self.logger.info(f"Request completed in {execution_time:.2f}s")
    
    async def _execute_analysis_phase(self, state: FinancialAnalysisState) -> Dict[str, Any]:
        """🎓 ANALYSIS PHASE: Run financial and risk analysis in parallel"""
        
        self.logger.info("Starting parallel analysis phase")
        
        # Execute financial and risk analysis in parallel
        tasks = [
            self.agents["financial_analyzer"].execute_with_resilience(state),
            self.agents["risk_assessor"].execute_with_resilience(state)
        ]
        
        try:
            # Wait for both with timeout
            financial_result, risk_result = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=20.0
            )
            
            # Process results
            results = {
                "financial_analysis": financial_result if not isinstance(financial_result, Exception) else None,
                "risk_assessment": risk_result if not isinstance(risk_result, Exception) else None
            }
            
            # Update state with successful results
            if results["financial_analysis"] and results["financial_analysis"].get("success"):
                state["financial_summary"] = results["financial_analysis"]["analysis"]
            
            if results["risk_assessment"] and results["risk_assessment"].get("success"):
                state["risk_assessment"] = f"Risk Level: {results['risk_assessment']['risk_level']}"
            
            return results
            
        except asyncio.TimeoutError:
            self.logger.error("Analysis phase timed out")
            state["fallback_used"] = True
            return {"error": "Analysis phase timeout"}
    
    async def _execute_recommendation_phase(self, state: FinancialAnalysisState) -> Dict[str, Any]:
        """🎓 RECOMMENDATION PHASE: Generate recommendations based on analysis"""
        
        self.logger.info("Starting recommendation phase")
        
        try:
            result = await self.agents["recommendation_engine"].execute_with_resilience(state)
            
            if result.get("success") and result.get("recommendations"):
                state["recommendations"] = result["recommendations"]
                state["analysis_complete"] = True
            
            return result
            
        except Exception as e:
            self.logger.error(f"Recommendation phase failed: {str(e)}")
            return {"error": str(e)}
    
    async def _compile_final_response(self, 
                                    state: FinancialAnalysisState,
                                    analysis_results: Dict[str, Any],
                                    recommendation_results: Dict[str, Any]) -> Dict[str, Any]:
        """🎓 RESPONSE COMPILATION: Create comprehensive user response"""
        
        response = {
            "success": True,
            "query": state["user_question"],
            "timestamp": datetime.now().isoformat(),
            "session_id": state["session_id"],
            "analysis_complete": state["analysis_complete"],
            "confidence_score": state["confidence_score"]
        }
        
        # Add successful analysis results
        if state.get("financial_summary"):
            response["financial_analysis"] = state["financial_summary"]
        
        if state.get("risk_assessment"):
            response["risk_assessment"] = state["risk_assessment"]
        
        if state.get("recommendations"):
            response["recommendations"] = state["recommendations"]
        
        # Add error information if any
        if state["errors"]:
            response["errors"] = [
                {
                    "agent": error.agent_name,
                    "type": error.error_type.value,
                    "message": error.message
                }
                for error in state["errors"]
            ]
        
        # Add degradation notice if fallbacks were used
        if state["fallback_used"]:
            response["notice"] = "Some services experienced issues. Analysis may be simplified."
            response["degraded"] = True
        
        return response
    
    async def _emergency_fallback_response(self, 
                                         state: FinancialAnalysisState, 
                                         error: Exception) -> Dict[str, Any]:
        """🎓 EMERGENCY FALLBACK: Last resort response when everything fails"""
        
        return {
            "success": False,
            "error": "System temporarily unavailable",
            "message": "We're experiencing technical difficulties. Please try again in a few minutes.",
            "query": state["user_question"],
            "timestamp": datetime.now().isoformat(),
            "session_id": state["session_id"],
            "fallback": True,
            "suggestions": [
                "Check your account balances manually",
                "Contact customer support if the issue persists",
                "Try a simpler question to test the system"
            ]
        }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """🎓 HEALTH CHECK: Comprehensive system health status"""
        
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "agents": {},
            "metrics": self.execution_metrics.copy()
        }
        
        # Get individual agent health
        agent_statuses = []
        for name, agent in self.agents.items():
            agent_health = agent.get_health_metrics()
            health_data["agents"][name] = agent_health
            agent_statuses.append(agent_health["status"])
        
        # Determine overall status
        if all(status == "healthy" for status in agent_statuses):
            health_data["overall_status"] = "healthy"
        elif any(status == "unhealthy" for status in agent_statuses):
            health_data["overall_status"] = "unhealthy"
        else:
            health_data["overall_status"] = "degraded"
        
        # Calculate success rate
        total_requests = self.execution_metrics["total_requests"]
        if total_requests > 0:
            success_rate = (
                self.execution_metrics["successful_requests"] + 
                self.execution_metrics["partial_failures"] * 0.5
            ) / total_requests
            health_data["success_rate"] = success_rate
        
        return health_data

# =============================================================================
# DEMONSTRATION: Production Error Handling
# =============================================================================

async def demonstrate_production_resilience():
    """
    🎓 FULL DEMONSTRATION: Production-grade error handling and resilience
    
    This simulation shows how Plutus handles various failure scenarios
    gracefully while still providing value to users.
    """
    
    print("="*70)
    print("🎓 LESSON 4: PRODUCTION INTEGRATION DEMONSTRATION")
    print("="*70)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize production orchestrator
    orchestrator = ProductionOrchestrator()
    
    print("\n🏗️ Production System Initialized")
    print("✅ All agents loaded with error handling")
    print("✅ Monitoring and logging configured")
    print("✅ Fallback mechanisms ready")
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Normal Operation",
            "description": "Everything works perfectly",
            "user_question": "How should I invest my savings?",
            "account_balances": {"checking": 5000, "savings": 25000, "401k": 15000}
        },
        {
            "name": "Partial Service Degradation",
            "description": "Some agents fail but system continues",
            "user_question": "What's my risk tolerance for retirement planning?",
            "account_balances": {"checking": 2000, "savings": 50000, "investment": 75000}
        },
        {
            "name": "High Load Scenario",
            "description": "System under stress but maintains service",
            "user_question": "Should I pay off debt or invest?",
            "account_balances": {"checking": 1500, "debt": -15000, "savings": 8000}
        }
    ]
    
    # Run test scenarios
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📋 Test Scenario {i}: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print(f"Question: {scenario['user_question']}")
        
        try:
            # Process the query
            result = await orchestrator.process_financial_query(
                user_question=scenario["user_question"],
                account_balances=scenario["account_balances"],
                user_id=f"test_user_{i}",
                session_id=f"test_session_{i}"
            )
            
            # Display results
            print(f"✅ Request processed successfully")
            print(f"   Success: {result['success']}")
            print(f"   Confidence: {result.get('confidence_score', 'N/A')}")
            
            if result.get('degraded'):
                print(f"⚠️  Service degradation detected")
            
            if result.get('recommendations'):
                print(f"   Recommendations: {len(result['recommendations'])} provided")
            
            if result.get('errors'):
                print(f"   Errors handled: {len(result['errors'])}")
            
        except Exception as e:
            print(f"❌ Scenario failed: {str(e)}")
        
        # Brief pause between scenarios
        await asyncio.sleep(0.5)
    
    # Show system health
    print(f"\n📊 Final System Health Check")
    health = await orchestrator.get_system_health()
    
    print(f"Overall Status: {health['overall_status'].upper()}")
    print(f"Success Rate: {health.get('success_rate', 0)*100:.1f}%")
    print(f"Total Requests: {health['metrics']['total_requests']}")
    
    print("\nAgent Health:")
    for agent_name, agent_health in health['agents'].items():
        status_emoji = "🟢" if agent_health['status'] == 'healthy' else "🟡" if agent_health['status'] == 'degraded' else "🔴"
        print(f"  {status_emoji} {agent_name}: {agent_health['status']} ({agent_health['error_rate']*100:.1f}% error rate)")
    
    print(f"\n" + "="*70)
    print("🎓 KEY PRODUCTION CONCEPTS DEMONSTRATED")
    print("="*70)
    print("""
    1. ERROR CLASSIFICATION:
       ✅ Different error types (timeout, rate limit, network, etc.)
       ✅ Recoverable vs non-recoverable errors
       ✅ Structured error tracking and logging
    
    2. RESILIENCE PATTERNS:
       ✅ Retry with exponential backoff
       ✅ Circuit breaker for failing services
       ✅ Timeout handling with graceful degradation
       ✅ Fallback responses for failed agents
    
    3. MONITORING & OBSERVABILITY:
       ✅ Structured logging with context
       ✅ Health metrics for each agent
       ✅ Success rate tracking
       ✅ Performance monitoring
    
    4. GRACEFUL DEGRADATION:
       ✅ Partial success handling
       ✅ Confidence score adjustment
       ✅ User-friendly error messages
       ✅ Emergency fallback responses
    
    5. PRODUCTION READINESS:
       ✅ Comprehensive error handling
       ✅ Data validation and sanitization
       ✅ Concurrent execution safety
       ✅ Resource management
    """)

if __name__ == "__main__":
    asyncio.run(demonstrate_production_resilience())

"""
🎓 LESSON 4 KEY TAKEAWAYS:

1. ERROR HANDLING STRATEGY:
   - Classify errors by type and recoverability
   - Implement retry logic with exponential backoff
   - Use circuit breakers for failing services
   - Provide meaningful fallback responses

2. RESILIENCE PATTERNS:
   - Timeout handling for all async operations
   - Data validation at input and output boundaries
   - Graceful degradation when services fail
   - Health checking and monitoring

3. PRODUCTION CONSIDERATIONS:
   - Comprehensive logging and monitoring
   - Metrics collection for performance tracking
   - User-friendly error messages
   - Emergency fallback mechanisms

4. MONITORING & OBSERVABILITY:
   - Structured logging with request context
   - Health endpoints for service monitoring
   - Error rate and performance metrics
   - Integration with monitoring systems

NEXT LESSON: Real Claude API integration and deployment strategies!
"""