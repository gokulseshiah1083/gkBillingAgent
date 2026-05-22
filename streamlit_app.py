import asyncio
from typing import Any, Dict

import streamlit as st

from src.agent.core import BillingInvestigationAgent, InvestigationContext
from src.retrieval.rag_engine import RAGEngine
from src.security.compliance import ComplianceEngine
from src.tools.data_access import DataAccessManager
from src.utils.config import load_config


@st.cache_resource
def get_agent() -> BillingInvestigationAgent:
    config = load_config("config/settings.yaml")

    rag_engine = RAGEngine(config.get("models", {}), config.get("vector_db", {}))
    compliance_engine = ComplianceEngine(config.get("security", {}), config.get("compliance", {}))
    data_manager = DataAccessManager(config.get("database", {}))

    return BillingInvestigationAgent(
        rag_engine=rag_engine,
        compliance_engine=compliance_engine,
        data_manager=data_manager,
        config=config,
    )


def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.run(coro)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


st.set_page_config(page_title="GK Billing Agent", page_icon="💳", layout="wide")

st.title("GK Billing Agent")

with st.sidebar:
    st.header("Session")
    user_id = st.text_input("User ID", value="analyst_demo")
    user_role = st.selectbox("Role", options=["billing_analyst", "senior_analyst", "auditor", "admin"], index=0)
    region = st.selectbox("Region", options=["NA", "EU", "AP", "LATAM"], index=0)
    session_id = st.text_input("Session ID", value="streamlit_session")

query = st.text_area(
    "Ask a billing investigation question",
    value="Why was transaction TXN202401154789 charged $12.50?",
    height=120,
)

col1, col2 = st.columns([1, 3])
with col1:
    run_btn = st.button("Investigate", type="primary")
with col2:
    st.caption("This Streamlit UI runs the agent in-process (no FastAPI server required).")

if run_btn:
    agent = get_agent()

    ctx = InvestigationContext(
        session_id=session_id,
        user_id=user_id,
        user_role=user_role,
        region=region,
        query_history=[],
        current_focus=None,
        constraints={"permissions": ["read_transactions", "investigate_billing"]},
    )

    with st.spinner("Investigating..."):
        result = run_async(agent.process_query(query, ctx))

    st.subheader("Answer")
    st.write(result.answer)

    st.subheader("Confidence")
    st.progress(min(max(result.confidence, 0.0), 1.0))
    st.write(result.confidence)

    st.subheader("Next steps")
    for step in result.next_steps:
        st.write(f"- {step}")

    st.subheader("Evidence")
    st.json(result.evidence)

    st.subheader("Similar cases")
    st.json(result.similar_cases)
