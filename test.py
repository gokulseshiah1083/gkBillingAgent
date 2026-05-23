import asyncio
import os
import sys
from pathlib import Path


def _load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)
    except Exception:
        return


async def _run() -> int:
    _load_dotenv_if_present()

    try:
        from src.agent.core import BillingInvestigationAgent, InvestigationContext
        from src.retrieval.rag_engine import RAGEngine
        from src.security.compliance import ComplianceEngine
        from src.tools.data_access import DataAccessManager
        from src.utils.config import load_config
    except Exception as e:
        print(f"IMPORT_ERROR: {e}")
        return 2

    try:
        config = load_config(Path(__file__).parent / "config" / "settings.yaml")

        rag_engine = RAGEngine(config.get("models", {}), config.get("vector_db", {}))
        await rag_engine.ensure_indexed()
        compliance_engine = ComplianceEngine(config.get("security", {}), config.get("compliance", {}))
        data_manager = DataAccessManager(config.get("database", {}))

        agent = BillingInvestigationAgent(
            rag_engine=rag_engine,
            compliance_engine=compliance_engine,
            data_manager=data_manager,
            config=config,
        )

        query = os.getenv("BILLING_AGENT_TEST_QUERY", "Why was transaction TXN202401154789 charged $12.50?")

        ctx = InvestigationContext(
            session_id="test_session",
            user_id="test_user",
            user_role="billing_analyst",
            region="NA",
            query_history=[],
            current_focus=None,
            constraints={"permissions": ["read_transactions", "investigate_billing"]},
        )

        result = await agent.process_query(query, ctx)

        print("QUERY_ID:", result.query_id)
        print("TYPE:", result.investigation_type.value)
        print("CONFIDENCE:", result.confidence)
        print("ANSWER:\n", result.answer)
        print("NEXT_STEPS:")
        for step in result.next_steps:
            print("-", step)

        if not result.answer:
            print("TEST_FAILED: Empty answer")
            return 1

        print("TEST_OK")
        return 0

    except Exception as e:
        print(f"TEST_ERROR: {e}")
        return 1


def main() -> None:
    try:
        code = asyncio.run(_run())
    except KeyboardInterrupt:
        code = 130
    raise SystemExit(code)


if __name__ == "__main__":
    main()
