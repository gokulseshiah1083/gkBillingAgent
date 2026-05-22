"""
Core AI Billing Investigation Agent
Main orchestrator for billing investigations using RAG and multi-step reasoning
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging
from datetime import datetime

from ..retrieval.rag_engine import RAGEngine
from ..security.compliance import ComplianceEngine
from ..tools.data_access import DataAccessManager
from ..utils.query_parser import QueryParser
from ..utils.context_manager import ContextManager


class InvestigationType(Enum):
    SINGLE_TRANSACTION = "single_transaction"
    PAN_RANGE = "pan_range"
    ISSUER_LEVEL = "issuer_level"
    FEE_DISPUTE = "fee_dispute"
    RULE_VIOLATION = "rule_violation"
    GENERAL_INQUIRY = "general_inquiry"


@dataclass
class QueryResult:
    """Result of a billing investigation query"""
    query_id: str
    investigation_type: InvestigationType
    answer: str
    confidence: float
    evidence: List[Dict[str, Any]]
    next_steps: List[str]
    similar_cases: List[Dict[str, Any]]
    processing_time_ms: int
    compliance_flags: List[str]


@dataclass
class InvestigationContext:
    """Context for ongoing investigation"""
    session_id: str
    user_id: str
    user_role: str
    region: str
    query_history: List[Dict[str, Any]]
    current_focus: Optional[str]
    constraints: Dict[str, Any]


class BillingInvestigationAgent:
    """
    Main AI agent for billing investigations
    
    Features:
    - Natural language query processing
    - Multi-step investigation planning
    - RAG-based knowledge retrieval
    - Security and compliance enforcement
    - Explainable results with evidence
    """
    
    def __init__(
        self,
        rag_engine: RAGEngine,
        compliance_engine: ComplianceEngine,
        data_manager: DataAccessManager,
        config: Dict[str, Any]
    ):
        self.rag_engine = rag_engine
        self.compliance_engine = compliance_engine
        self.data_manager = data_manager
        self.config = config
        
        self.query_parser = QueryParser()
        self.context_manager = ContextManager()
        
        self.logger = logging.getLogger(__name__)
        
    async def process_query(
        self,
        query: str,
        context: InvestigationContext
    ) -> QueryResult:
        """
        Process a billing investigation query
        
        Args:
            query: Natural language query from analyst
            context: Investigation context and user information
            
        Returns:
            QueryResult with answer, evidence, and recommendations
        """
        start_time = datetime.now()
        query_id = self._generate_query_id()
        
        try:
            # Step 1: Parse and classify query
            parsed_query = await self._parse_query(query, context)
            
            # Step 2: Validate compliance
            compliance_result = await self._validate_compliance(
                parsed_query, context
            )
            if not compliance_result.allowed:
                return self._create_compliance_denied_result(
                    query_id, parsed_query, compliance_result
                )
            
            # Step 3: Create investigation plan
            investigation_plan = await self._create_investigation_plan(
                parsed_query, context
            )
            
            # Step 4: Execute investigation steps
            investigation_results = await self._execute_investigation(
                investigation_plan, context
            )
            
            # Step 5: Generate response
            response = await self._generate_response(
                parsed_query, investigation_results, context
            )
            
            # Step 6: Apply final compliance checks
            final_response = await self._apply_final_compliance(
                response, context
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update context
            await self.context_manager.update_context(
                context.session_id,
                query_id,
                parsed_query,
                final_response
            )
            
            return QueryResult(
                query_id=query_id,
                investigation_type=parsed_query.investigation_type,
                answer=final_response.answer,
                confidence=final_response.confidence,
                evidence=final_response.evidence,
                next_steps=final_response.next_steps,
                similar_cases=final_response.similar_cases,
                processing_time_ms=int(processing_time),
                compliance_flags=final_response.compliance_flags
            )
            
        except Exception as e:
            self.logger.error(f"Error processing query {query_id}: {str(e)}")
            return self._create_error_result(query_id, query, str(e))
    
    async def _parse_query(
        self,
        query: str,
        context: InvestigationContext
    ) -> Dict[str, Any]:
        """Parse and classify the natural language query"""
        
        # Extract entities and intent
        entities = await self.query_parser.extract_entities(query)
        intent = await self.query_parser.classify_intent(query)
        
        # Determine investigation type
        investigation_type = self._classify_investigation_type(
            intent, entities
        )
        
        # Build query context
        query_context = {
            "original_query": query,
            "entities": entities,
            "intent": intent,
            "investigation_type": investigation_type,
            "user_context": {
                "role": context.user_role,
                "region": context.region,
                "constraints": context.constraints
            }
        }
        
        return query_context
    
    def _classify_investigation_type(
        self,
        intent: Dict[str, Any],
        entities: Dict[str, Any]
    ) -> InvestigationType:
        """Classify the type of investigation needed"""
        
        # Check for single transaction
        if entities.get("pan") and entities.get("transaction_id"):
            return InvestigationType.SINGLE_TRANSACTION
        
        # Check for PAN range
        if entities.get("pan_range") or entities.get("issuer_pan_prefix"):
            return InvestigationType.PAN_RANGE
        
        # Check for issuer level
        if entities.get("issuer_id") or entities.get("bank_name"):
            return InvestigationType.ISSUER_LEVEL
        
        # Check for fee dispute
        if "fee" in intent.get("keywords", []) or "charge" in intent.get("keywords", []):
            return InvestigationType.FEE_DISPUTE
        
        # Check for rule violation
        if "rule" in intent.get("keywords", []) or "violation" in intent.get("keywords", []):
            return InvestigationType.RULE_VIOLATION
        
        return InvestigationType.GENERAL_INQUIRY
    
    async def _validate_compliance(
        self,
        parsed_query: Dict[str, Any],
        context: InvestigationContext
    ) -> Dict[str, Any]:
        """Validate query against compliance rules"""
        
        compliance_check = await self.compliance_engine.validate_query(
            parsed_query,
            context.user_role,
            context.region
        )
        
        return compliance_check
    
    async def _create_investigation_plan(
        self,
        parsed_query: Dict[str, Any],
        context: InvestigationContext
    ) -> List[Dict[str, Any]]:
        """Create multi-step investigation plan"""
        
        investigation_type = parsed_query["investigation_type"]
        entities = parsed_query["entities"]
        
        # Base investigation steps
        base_steps = [
            {
                "step_id": "retrieve_relevant_rules",
                "description": "Retrieve applicable billing rules and policies",
                "tool": "rag_engine",
                "parameters": {
                    "query_type": "rules",
                    "entities": entities
                }
            },
            {
                "step_id": "retrieve_historical_cases",
                "description": "Find similar historical investigations",
                "tool": "rag_engine",
                "parameters": {
                    "query_type": "cases",
                    "entities": entities
                }
            }
        ]
        
        # Type-specific steps
        type_specific_steps = []
        
        if investigation_type == InvestigationType.SINGLE_TRANSACTION:
            type_specific_steps = [
                {
                    "step_id": "retrieve_transaction_data",
                    "description": "Get transaction lifecycle data",
                    "tool": "data_manager",
                    "parameters": {
                        "data_type": "transaction",
                        "filters": {
                            "pan": entities.get("pan"),
                            "transaction_id": entities.get("transaction_id"),
                            "date_range": entities.get("date_range")
                        }
                    }
                },
                {
                    "step_id": "retrieve_billing_details",
                    "description": "Get billing calculation details",
                    "tool": "data_manager",
                    "parameters": {
                        "data_type": "billing",
                        "filters": {
                            "transaction_id": entities.get("transaction_id")
                        }
                    }
                }
            ]
        
        elif investigation_type == InvestigationType.PAN_RANGE:
            type_specific_steps = [
                {
                    "step_id": "retrieve_pan_range_data",
                    "description": "Get transactions for PAN range",
                    "tool": "data_manager",
                    "parameters": {
                        "data_type": "transactions",
                        "filters": {
                            "pan_range": entities.get("pan_range"),
                            "date_range": entities.get("date_range")
                        }
                    }
                },
                {
                    "step_id": "analyze_billing_patterns",
                    "description": "Analyze billing patterns in PAN range",
                    "tool": "data_manager",
                    "parameters": {
                        "analysis_type": "pattern_analysis",
                        "filters": entities
                    }
                }
            ]
        
        elif investigation_type == InvestigationType.ISSUER_LEVEL:
            type_specific_steps = [
                {
                    "step_id": "retrieve_issuer_data",
                    "description": "Get issuer-level transaction data",
                    "tool": "data_manager",
                    "parameters": {
                        "data_type": "issuer_transactions",
                        "filters": {
                            "issuer_id": entities.get("issuer_id"),
                            "date_range": entities.get("date_range")
                        }
                    }
                },
                {
                    "step_id": "analyze_issuer_patterns",
                    "description": "Analyze issuer billing patterns",
                    "tool": "data_manager",
                    "parameters": {
                        "analysis_type": "issuer_analysis",
                        "filters": entities
                    }
                }
            ]
        
        return base_steps + type_specific_steps
    
    async def _execute_investigation(
        self,
        investigation_plan: List[Dict[str, Any]],
        context: InvestigationContext
    ) -> Dict[str, Any]:
        """Execute the investigation plan"""
        
        results = {}
        
        for step in investigation_plan:
            step_id = step["step_id"]
            tool = step["tool"]
            parameters = step["parameters"]
            
            try:
                if tool == "rag_engine":
                    result = await self.rag_engine.retrieve(
                        query_type=parameters.get("query_type"),
                        entities=parameters.get("entities"),
                        context=context
                    )
                elif tool == "data_manager":
                    result = await self.data_manager.query(
                        data_type=parameters.get("data_type"),
                        filters=parameters.get("filters"),
                        context=context
                    )
                else:
                    raise ValueError(f"Unknown tool: {tool}")
                
                results[step_id] = {
                    "status": "success",
                    "data": result,
                    "execution_time": datetime.now().isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Error in step {step_id}: {str(e)}")
                results[step_id] = {
                    "status": "error",
                    "error": str(e),
                    "execution_time": datetime.now().isoformat()
                }
        
        return results
    
    async def _generate_response(
        self,
        parsed_query: Dict[str, Any],
        investigation_results: Dict[str, Any],
        context: InvestigationContext
    ) -> Dict[str, Any]:
        """Generate comprehensive response with explanation"""
        
        # Collect evidence from investigation results
        evidence = []
        rules = []
        similar_cases = []
        
        for step_id, result in investigation_results.items():
            if result["status"] == "success":
                data = result["data"]
                
                if "rules" in step_id:
                    rules.extend(data.get("rules", []))
                elif "cases" in step_id:
                    similar_cases.extend(data.get("cases", []))
                else:
                    evidence.append({
                        "source": step_id,
                        "data": data,
                        "relevance": self._calculate_relevance(data, parsed_query)
                    })
        
        # Generate main answer using LLM
        answer = await self._generate_llm_response(
            parsed_query,
            evidence,
            rules,
            similar_cases,
            context
        )
        
        # Generate next steps
        next_steps = await self._generate_next_steps(
            parsed_query,
            investigation_results,
            context
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            investigation_results,
            evidence,
            rules
        )
        
        return {
            "answer": answer,
            "confidence": confidence,
            "evidence": evidence,
            "next_steps": next_steps,
            "similar_cases": similar_cases[:5],  # Top 5 similar cases
            "compliance_flags": []
        }
    
    async def _generate_llm_response(
        self,
        parsed_query: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        rules: List[Dict[str, Any]],
        similar_cases: List[Dict[str, Any]],
        context: InvestigationContext
    ) -> str:
        """Generate natural language response using LLM"""
        
        # Build prompt
        prompt = self._build_response_prompt(
            parsed_query,
            evidence,
            rules,
            similar_cases
        )
        
        # Get LLM response
        response = await self.rag_engine.llm_generate(prompt)
        
        return response
    
    def _build_response_prompt(
        self,
        parsed_query: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        rules: List[Dict[str, Any]],
        similar_cases: List[Dict[str, Any]]
    ) -> str:
        """Build comprehensive prompt for LLM"""
        
        prompt = f"""
You are an expert billing investigation analyst for Mastercard. You need to answer the following query:

Query: {parsed_query['original_query']}

Investigation Type: {parsed_query['investigation_type'].value}

Relevant Rules:
{self._format_rules(rules)}

Evidence from Data Sources:
{self._format_evidence(evidence)}

Similar Historical Cases:
{self._format_similar_cases(similar_cases)}

Please provide:
1. A clear, concise answer to the query
2. Explanation of the root cause
3. Evidence supporting your conclusion
4. Any discrepancies found

Focus on being accurate, explainable, and helpful for the billing analyst.
"""
        
        return prompt
    
    def _format_rules(self, rules: List[Dict[str, Any]]) -> str:
        """Format rules for prompt"""
        if not rules:
            return "No specific rules found."
        
        formatted = []
        for rule in rules[:10]:  # Limit to prevent prompt overflow
            formatted.append(f"- {rule.get('name', 'Unknown')}: {rule.get('description', 'No description')}")
        
        return "\n".join(formatted)
    
    def _format_evidence(self, evidence: List[Dict[str, Any]]) -> str:
        """Format evidence for prompt"""
        if not evidence:
            return "No evidence found."
        
        formatted = []
        for ev in evidence[:15]:  # Limit to prevent prompt overflow
            source = ev.get("source", "Unknown")
            data_summary = self._summarize_data(ev.get("data", {}))
            relevance = ev.get("relevance", 0)
            formatted.append(f"- {source} (relevance: {relevance:.2f}): {data_summary}")
        
        return "\n".join(formatted)
    
    def _format_similar_cases(self, cases: List[Dict[str, Any]]) -> str:
        """Format similar cases for prompt"""
        if not cases:
            return "No similar cases found."
        
        formatted = []
        for case in cases[:5]:  # Limit to prevent prompt overflow
            summary = case.get("summary", "No summary")
            outcome = case.get("outcome", "Unknown outcome")
            formatted.append(f"- Case: {summary} -> {outcome}")
        
        return "\n".join(formatted)
    
    def _summarize_data(self, data: Dict[str, Any]) -> str:
        """Summarize data for prompt"""
        if isinstance(data, dict):
            keys = list(data.keys())[:5]
            return f"Data with keys: {', '.join(keys)}"
        elif isinstance(data, list):
            return f"List with {len(data)} items"
        else:
            return str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
    
    async def _generate_next_steps(
        self,
        parsed_query: Dict[str, Any],
        investigation_results: Dict[str, Any],
        context: InvestigationContext
    ) -> List[str]:
        """Generate recommended next steps"""
        
        next_steps = []
        
        # Standard next steps based on investigation type
        investigation_type = parsed_query["investigation_type"]
        
        if investigation_type == InvestigationType.SINGLE_TRANSACTION:
            next_steps.extend([
                "Verify transaction amount against original authorization",
                "Check if any pricing rules were recently updated",
                "Review fee calculation breakdown",
                "Confirm cardholder agreement terms"
            ])
        
        elif investigation_type == InvestigationType.PAN_RANGE:
            next_steps.extend([
                "Analyze pattern across affected PAN range",
                "Check for recent system updates affecting this range",
                "Verify feeder file processing logic",
                "Consider generating reversal file if needed"
            ])
        
        elif investigation_type == InvestigationType.ISSUER_LEVEL:
            next_steps.extend([
                "Review issuer-specific pricing agreements",
                "Check for recent changes to interchange rates",
                "Analyze transaction volume patterns",
                "Coordinate with issuer relationship team"
            ])
        
        # Add specific next steps based on investigation results
        for step_id, result in investigation_results.items():
            if result["status"] == "error":
                next_steps.append(f"Manually investigate {step_id} - system error occurred")
        
        return next_steps[:8]  # Limit to 8 recommendations
    
    def _calculate_confidence(
        self,
        investigation_results: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        rules: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score for the response"""
        
        # Base confidence from successful steps
        successful_steps = sum(1 for r in investigation_results.values() if r["status"] == "success")
        total_steps = len(investigation_results)
        step_confidence = successful_steps / total_steps if total_steps > 0 else 0.0
        
        # Evidence quality factor
        evidence_factor = min(len(evidence) / 10, 1.0)  # Cap at 10 pieces of evidence
        
        # Rule coverage factor
        rule_factor = min(len(rules) / 5, 1.0)  # Cap at 5 relevant rules
        
        # Combined confidence
        confidence = (step_confidence * 0.4 + evidence_factor * 0.3 + rule_factor * 0.3)
        
        return round(confidence, 2)
    
    def _calculate_relevance(self, data: Any, parsed_query: Dict[str, Any]) -> float:
        """Calculate relevance score of data to query"""
        # Simple relevance calculation - can be enhanced with ML
        entities = parsed_query.get("entities", {})
        
        relevance = 0.0
        
        if isinstance(data, dict):
            # Check for entity matches
            for entity_key, entity_value in entities.items():
                if entity_value and str(entity_value).lower() in str(data).lower():
                    relevance += 0.2
        
        return min(relevance, 1.0)
    
    async def _apply_final_compliance(
        self,
        response: Dict[str, Any],
        context: InvestigationContext
    ) -> Dict[str, Any]:
        """Apply final compliance checks to response"""
        
        compliance_result = await self.compliance_engine.validate_response(
            response,
            context.user_role,
            context.region
        )
        
        response["compliance_flags"] = compliance_result.get("flags", [])
        
        if compliance_result.get("masked_data"):
            response["answer"] = compliance_result["masked_answer"]
        
        return response
    
    def _generate_query_id(self) -> str:
        """Generate unique query ID"""
        import uuid
        return f"query_{uuid.uuid4().hex[:12]}"
    
    def _create_compliance_denied_result(
        self,
        query_id: str,
        parsed_query: Dict[str, Any],
        compliance_result: Dict[str, Any]
    ) -> QueryResult:
        """Create result for compliance-denied queries"""
        
        return QueryResult(
            query_id=query_id,
            investigation_type=parsed_query["investigation_type"],
            answer=f"Query cannot be processed due to compliance restrictions: {compliance_result.get('reason', 'Unknown reason')}",
            confidence=0.0,
            evidence=[],
            next_steps=["Contact compliance team for access"],
            similar_cases=[],
            processing_time_ms=0,
            compliance_flags=["COMPLIANCE_DENIED"]
        )
    
    def _create_error_result(
        self,
        query_id: str,
        original_query: str,
        error_message: str
    ) -> QueryResult:
        """Create result for failed queries"""
        
        return QueryResult(
            query_id=query_id,
            investigation_type=InvestigationType.GENERAL_INQUIRY,
            answer=f"Error processing query: {error_message}",
            confidence=0.0,
            evidence=[],
            next_steps=["Try rephrasing the query", "Contact support team"],
            similar_cases=[],
            processing_time_ms=0,
            compliance_flags=["ERROR"]
        )
