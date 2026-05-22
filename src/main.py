"""
AI Billing Investigation Agent - Main Application Entry Point
Mastercard Core Billing Intelligence System
"""

import argparse
import asyncio
import logging
import os
import socket
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Security, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import yaml
from pydantic import BaseModel

try:
    from src.agent.core import BillingInvestigationAgent, InvestigationContext, InvestigationType
    from src.retrieval.rag_engine import RAGEngine
    from src.security.compliance import ComplianceEngine
    from src.tools.data_access import DataAccessManager
    from src.utils.config import load_config
    from src.utils.logger import setup_logging
except ImportError:  # pragma: no cover
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.agent.core import BillingInvestigationAgent, InvestigationContext, InvestigationType
    from src.retrieval.rag_engine import RAGEngine
    from src.security.compliance import ComplianceEngine
    from src.tools.data_access import DataAccessManager
    from src.utils.config import load_config
    from src.utils.logger import setup_logging

from src.voice.tts import try_create_speaker


# Configuration
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=False)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"
config = load_config(CONFIG_PATH)

_voice_env = os.getenv("BILLING_AGENT_VOICE")
if _voice_env is not None:
    config.setdefault("features", {})["voice_queries"] = _voice_env.strip().lower() in {"1", "true", "yes", "on"}

# Logging
setup_logging(config.get("logging", {}))
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Application
app = FastAPI(
    title="AI Billing Investigation Agent",
    description="Mastercard Core Billing Intelligence System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get("cors", {}).get("allowed_origins", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Components
agent: Optional[BillingInvestigationAgent] = None
speaker = None


class QueryRequest(BaseModel):
    """Request model for billing investigation queries"""
    query: str
    session_id: Optional[str] = None
    user_context: Optional[dict] = None


class QueryResponse(BaseModel):
    """Response model for billing investigation results"""
    query_id: str
    investigation_type: str
    answer: str
    confidence: float
    evidence: list
    next_steps: list
    similar_cases: list
    processing_time_ms: int
    compliance_flags: list


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    components: dict


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Validate user token and extract user information"""
    # TODO: Implement proper JWT validation
    # For now, return a mock user
    return {
        "user_id": "analyst_123",
        "user_role": "billing_analyst",
        "region": "US",
        "permissions": ["read_transactions", "investigate_billing"]
    }


@app.on_event("startup")
async def startup_event():
    """Initialize application components"""
    global agent, speaker
    
    try:
        logger.info("Starting AI Billing Investigation Agent...")
        
        # Initialize components
        rag_engine = RAGEngine(config.get("models", {}), config.get("vector_db", {}))
        compliance_engine = ComplianceEngine(config.get("security", {}), config.get("compliance", {}))
        data_manager = DataAccessManager(config.get("database", {}))
        
        # Initialize main agent
        agent = BillingInvestigationAgent(
            rag_engine=rag_engine,
            compliance_engine=compliance_engine,
            data_manager=data_manager,
            config=config
        )

        if config.get("features", {}).get("voice_queries", False):
            speaker = try_create_speaker()
        
        logger.info("AI Billing Investigation Agent started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup application resources"""
    logger.info("Shutting down AI Billing Investigation Agent...")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        components={
            "agent": "healthy" if agent else "unhealthy",
            "database": "healthy",  # TODO: Implement actual health check
            "vector_db": "healthy",  # TODO: Implement actual health check
            "compliance": "healthy"
        }
    )


@app.post("/investigate", response_model=QueryResponse)
async def investigate_billing(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Main endpoint for billing investigations
    
    Args:
        request: Investigation query request
        current_user: Authenticated user information
    
    Returns:
        Investigation results with evidence and recommendations
    """
    try:
        # Create investigation context
        context = InvestigationContext(
            session_id=request.session_id or f"session_{hash(request.query) % 1000000}",
            user_id=current_user["user_id"],
            user_role=current_user["user_role"],
            region=current_user["region"],
            query_history=[],  # TODO: Implement session management
            current_focus=None,
            constraints={
                "permissions": current_user["permissions"],
                "data_access": current_user.get("data_access", {})
            }
        )
        
        # Process investigation query
        result = await agent.process_query(request.query, context)

        if speaker is not None and config.get("features", {}).get("voice_queries", False):
            background_tasks.add_task(speaker.speak, result.answer)
        
        # Return response
        return QueryResponse(
            query_id=result.query_id,
            investigation_type=result.investigation_type.value,
            answer=result.answer,
            confidence=result.confidence,
            evidence=result.evidence,
            next_steps=result.next_steps,
            similar_cases=result.similar_cases,
            processing_time_ms=result.processing_time_ms,
            compliance_flags=result.compliance_flags
        )
        
    except Exception as e:
        logger.error(f"Error processing investigation query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/investigation/types")
async def get_investigation_types():
    """Get available investigation types"""
    return {
        "types": [
            {
                "type": "single_transaction",
                "description": "Investigate a single transaction",
                "example": "Why was transaction TXN123456 charged $12.50?"
            },
            {
                "type": "pan_range",
                "description": "Analyze billing patterns across a PAN range",
                "example": "Show anomalies for PAN range 542418 to 542425"
            },
            {
                "type": "issuer_level",
                "description": "Investigate issuer-wide billing patterns",
                "example": "Analyze Chase Bank transactions over $1000"
            },
            {
                "type": "fee_dispute",
                "description": "Investigate fee disputes and calculations",
                "example": "Why was interchange fee applied to this transaction?"
            },
            {
                "type": "rule_violation",
                "description": "Investigate potential rule violations",
                "example": "Check if billing rules were correctly applied"
            }
        ]
    }


@app.get("/investigation/examples")
async def get_investigation_examples():
    """Get example investigation queries"""
    return {
        "examples": [
            {
                "category": "Single Transaction",
                "queries": [
                    "Why was transaction TXN202401154789 charged $12.50?",
                    "Transaction 1234567890123456 was authorized for $45.00 but settled for $47.25. Why the difference?",
                    "Show me the fee breakdown for transaction ABC123456789"
                ]
            },
            {
                "category": "PAN Range Analysis",
                "queries": [
                    "Show all billing anomalies for PAN range 542418 to 542425 in the last 48 hours",
                    "Analyze billing patterns for cards starting with 414720",
                    "Find all transactions with incorrect fees for PAN range 123456-123459"
                ]
            },
            {
                "category": "Issuer Level",
                "queries": [
                    "Analyze billing patterns for Chase Bank transactions over $1000 in the past month",
                    "Show me all issues with Bank of America transactions this week",
                    "What are the common billing problems for issuer 123456?"
                ]
            },
            {
                "category": "Fee Disputes",
                "queries": [
                    "What are the interchange rates for restaurant transactions in the US?",
                    "Why was foreign transaction fee applied to this domestic purchase?",
                    "Explain the assessment fee calculation for this transaction"
                ]
            }
        ]
    }


@app.get("/metrics")
async def get_metrics():
    """Get system performance metrics"""
    # TODO: Implement actual metrics collection
    return {
        "performance": {
            "average_response_time_ms": 45000,
            "queries_per_hour": 125,
            "success_rate": 0.95,
            "confidence_average": 0.89
        },
        "usage": {
            "daily_queries": 1250,
            "active_users": 45,
            "top_investigation_types": ["single_transaction", "pan_range", "fee_dispute"]
        },
        "system": {
            "uptime_percentage": 99.9,
            "database_connections": 15,
            "vector_db_health": "healthy",
            "cache_hit_rate": 0.78
        }
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--voice", action="store_true")
    parser.add_argument("--host", default=os.getenv("BILLING_AGENT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("BILLING_AGENT_PORT", "8080")))
    args = parser.parse_args()

    if args.voice:
        os.environ["BILLING_AGENT_VOICE"] = "true"
        config.setdefault("features", {})["voice_queries"] = True

    # Pre-flight check: uvicorn may swallow bind errors (esp. with reload).
    # We detect forbidden ports early and fall back.
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((args.host, args.port))
    except OSError as e:
        if getattr(e, "winerror", None) == 10013 and args.port == 8080:
            print(
                "[WinError 10013] Port 8080 bind forbidden. Falling back to port 8001. "
                "Open http://localhost:8001/docs"
            )
            args.port = 8001
        else:
            raise
    finally:
        try:
            sock.close()
        except Exception:
            pass

    reload_enabled = config.get("development", {}).get("hot_reload", True)
    try:
        uvicorn.run(
            "src.main:app" if reload_enabled else app,
            host=args.host,
            port=args.port,
            reload=reload_enabled,
            log_level=config.get("logging", {}).get("level", "info").lower(),
        )
    except OSError as e:
        if getattr(e, "winerror", None) == 10013:
            if args.port == 8080:
                fallback_port = 8001
                print(
                    "[WinError 10013] Port 8080 bind forbidden. Retrying on port 8001. "
                    "If this also fails, allow python.exe in Windows Firewall or choose an allowed port."
                )
                uvicorn.run(
                    "src.main:app" if reload_enabled else app,
                    host=args.host,
                    port=fallback_port,
                    reload=reload_enabled,
                    log_level=config.get("logging", {}).get("level", "info").lower(),
                )
                raise SystemExit(0)
            raise SystemExit(
                "[WinError 10013] Port bind forbidden. Try a different port, e.g. "
                "`python -m src.main --port 8001 --voice`, or allow python.exe in Windows Firewall."
            )
        raise
