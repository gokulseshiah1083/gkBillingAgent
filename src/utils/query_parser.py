"""
Query Parser for Billing Investigation Agent
Handles natural language query parsing, entity extraction, and intent classification
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging


class IntentType(Enum):
    BILLING_INQUIRY = "billing_inquiry"
    FEE_DISPUTE = "fee_dispute"
    TRANSACTION_INVESTIGATION = "transaction_investigation"
    PAN_RANGE_ANALYSIS = "pan_range_analysis"
    ISSUER_INQUIRY = "issuer_inquiry"
    RULE_VIOLATION = "rule_violation"
    PATTERN_ANALYSIS = "pattern_analysis"
    GENERAL_QUESTION = "general_question"


@dataclass
class ExtractedEntity:
    """Represents an extracted entity from a query"""
    entity_type: str
    value: str
    confidence: float
    start_pos: int
    end_pos: int


@dataclass
class QueryIntent:
    """Represents the classified intent of a query"""
    primary_intent: IntentType
    confidence: float
    keywords: List[str]
    entities: List[str]


class QueryParser:
    """
    Natural language query parser for billing investigations
    
    Capabilities:
    - Entity extraction (PANs, amounts, dates, issuers)
    - Intent classification
    - Query type detection
    - Context understanding
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize patterns for entity extraction
        self._init_entity_patterns()
        
        # Initialize intent keywords
        self._init_intent_keywords()
        
        # Initialize date patterns
        self._init_date_patterns()
    
    def _init_entity_patterns(self):
        """Initialize regex patterns for entity extraction"""
        
        self.entity_patterns = {
            # PAN patterns (various formats)
            'pan': [
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # 16-digit
                r'\b\d{13,19}\b',  # 13-19 digit PANs
                r'\b\d{6}\*{4,8}\d{4}\b'  # Masked PANs
            ],
            
            # Amount patterns
            'amount': [
                r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',  # $1,234.56
                r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|dollars?)',  # 1,234.56 USD
                r'\b\d+(?:\.\d{2})?\b'  # Simple numbers
            ],
            
            # Date patterns
            'date': [
                r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',  # MM/DD/YYYY
                r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b',  # YYYY-MM-DD
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b'  # Month DD, YYYY
            ],
            
            # Transaction ID patterns
            'transaction_id': [
                r'\bTXN\d{8,15}\b',  # TXN followed by digits
                r'\b\d{10,20}\b'  # Long numeric IDs
            ],
            
            # Issuer patterns
            'issuer': [
                r'\b(?:Bank of America|Chase|Wells Fargo|Citibank|Capital One|American Express)\b',
                r'\b(?:JPMorgan|Citi|BofA|WF)\b',  # Common abbreviations
                r'\bIssuer\s+\d+\b'  # Issuer + number
            ],
            
            # PAN range patterns
            'pan_range': [
                r'\b\d{6}(?:[-\s]to[-\s]|\s*-\s*)\d{6}\b',  # 123456 to 654321
                r'\b\d{6}[-\s]\d{6}\b'  # 123456-654321
            ],
            
            # Fee types
            'fee_type': [
                r'\b(?:interchange|assessment|service|late|overlimit|foreign|transaction)\s+fee\b',
                r'\b(?:annual|monthly|processing|settlement)\s+fee\b'
            ]
        }
    
    def _init_intent_keywords(self):
        """Initialize keyword mappings for intent classification"""
        
        self.intent_keywords = {
            IntentType.BILLING_INQUIRY: [
                'billing', 'charged', 'fee', 'cost', 'amount', 'price',
                'why was i charged', 'what is this fee', 'billing question'
            ],
            
            IntentType.FEE_DISPUTE: [
                'dispute', 'wrong charge', 'incorrect fee', 'refund',
                'reversal', 'disagree', 'mistake', 'error'
            ],
            
            IntentType.TRANSACTION_INVESTIGATION: [
                'transaction', 'purchase', 'payment', 'authorization',
                'clearing', 'settlement', 'declined', 'approved'
            ],
            
            IntentType.PAN_RANGE_ANALYSIS: [
                'pan range', 'card range', 'multiple cards', 'batch',
                'all cards', 'range of cards', 'prefix'
            ],
            
            IntentType.ISSUER_INQUIRY: [
                'issuer', 'bank', 'institution', 'financial institution',
                'our bank', 'our cards', 'issuer level'
            ],
            
            IntentType.RULE_VIOLATION: [
                'rule', 'violation', 'policy', 'compliance', 'regulation',
                'should not', 'incorrectly applied', 'wrong rule'
            ],
            
            IntentType.PATTERN_ANALYSIS: [
                'pattern', 'trend', 'multiple', 'several', 'repeated',
                'anomaly', 'unusual', 'strange'
            ],
            
            IntentType.GENERAL_QUESTION: [
                'what', 'how', 'when', 'where', 'who', 'explain',
                'help', 'understand', 'clarify'
            ]
        }
    
    def _init_date_patterns(self):
        """Initialize date parsing patterns"""
        
        self.relative_date_patterns = {
            'today': r'\btoday\b',
            'yesterday': r'\byesterday\b',
            'last_week': r'\blast\s+week\b',
            'last_month': r'\blast\s+month\b',
            'last_48_hours': r'\blast\s+48\s+hours?\b',
            'last_24_hours': r'\blast\s+24\s+hours?\b',
            'past_week': r'\bpast\s+week\b',
            'past_month': r'\bpast\s+month\b'
        }
    
    async def extract_entities(self, query: str) -> Dict[str, List[ExtractedEntity]]:
        """
        Extract entities from natural language query
        
        Args:
            query: Natural language query string
            
        Returns:
            Dictionary mapping entity types to extracted entities
        """
        
        entities = {}
        query_lower = query.lower()
        
        for entity_type, patterns in self.entity_patterns.items():
            extracted = []
            
            for pattern in patterns:
                matches = re.finditer(pattern, query, re.IGNORECASE)
                
                for match in matches:
                    entity = ExtractedEntity(
                        entity_type=entity_type,
                        value=match.group().strip(),
                        confidence=self._calculate_entity_confidence(match.group(), entity_type),
                        start_pos=match.start(),
                        end_pos=match.end()
                    )
                    extracted.append(entity)
            
            if extracted:
                entities[entity_type] = extracted
        
        # Extract relative dates
        relative_dates = self._extract_relative_dates(query)
        if relative_dates:
            entities['relative_date'] = relative_dates
        
        # Extract date ranges
        date_ranges = self._extract_date_ranges(query)
        if date_ranges:
            entities['date_range'] = date_ranges
        
        return entities
    
    async def classify_intent(self, query: str) -> QueryIntent:
        """
        Classify the intent of a natural language query
        
        Args:
            query: Natural language query string
            
        Returns:
            QueryIntent with classified intent and confidence
        """
        
        query_lower = query.lower()
        intent_scores = {}
        
        # Score each intent based on keyword matches
        for intent_type, keywords in self.intent_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in query_lower:
                    score += len(keyword.split())  # Multi-word keywords get higher scores
                    matched_keywords.append(keyword)
            
            if score > 0:
                intent_scores[intent_type] = {
                    'score': score,
                    'keywords': matched_keywords
                }
        
        # Determine primary intent
        if intent_scores:
            primary_intent = max(intent_scores.keys(), key=lambda k: intent_scores[k]['score'])
            score_data = intent_scores[primary_intent]
            
            # Normalize confidence (0.0 to 1.0)
            max_possible_score = len(query.split())  # Rough upper bound
            confidence = min(score_data['score'] / max_possible_score, 1.0)
            
            return QueryIntent(
                primary_intent=primary_intent,
                confidence=confidence,
                keywords=score_data['keywords'],
                entities=[]  # Will be filled by entity extraction
            )
        else:
            # Default to general question if no intent detected
            return QueryIntent(
                primary_intent=IntentType.GENERAL_QUESTION,
                confidence=0.1,
                keywords=[],
                entities=[]
            )
    
    def _calculate_entity_confidence(self, entity_value: str, entity_type: str) -> float:
        """Calculate confidence score for extracted entity"""
        
        confidence = 0.5  # Base confidence
        
        # Adjust confidence based on entity type and format
        if entity_type == 'pan':
            if len(entity_value.replace('-', '').replace(' ', '')) == 16:
                confidence = 0.9
            elif '*' in entity_value:  # Masked PAN
                confidence = 0.8
        
        elif entity_type == 'amount':
            if '$' in entity_value or 'USD' in entity_value:
                confidence = 0.9
            elif '.' in entity_value:
                confidence = 0.8
        
        elif entity_type == 'date':
            if re.match(r'\d{4}-\d{2}-\d{2}', entity_value):  # ISO format
                confidence = 0.9
            elif re.match(r'\d{1,2}/\d{1,2}/\d{4}', entity_value):  # MM/DD/YYYY
                confidence = 0.8
        
        elif entity_type == 'transaction_id':
            if entity_value.startswith('TXN'):
                confidence = 0.9
            elif len(entity_value) >= 10:
                confidence = 0.7
        
        return confidence
    
    def _extract_relative_dates(self, query: str) -> List[ExtractedEntity]:
        """Extract relative date expressions"""
        
        relative_dates = []
        query_lower = query.lower()
        
        for date_type, pattern in self.relative_date_patterns.items():
            matches = re.finditer(pattern, query_lower)
            
            for match in matches:
                entity = ExtractedEntity(
                    entity_type='relative_date',
                    value=date_type,
                    confidence=0.9,
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                relative_dates.append(entity)
        
        return relative_dates
    
    def _extract_date_ranges(self, query: str) -> List[ExtractedEntity]:
        """Extract date range expressions"""
        
        date_ranges = []
        
        # Pattern for "from date1 to date2"
        range_pattern = r'\b(?:from|between)\s+([^,\s]+(?:\s+[^,\s]+)*)\s+(?:to|and|until)\s+([^,\s]+(?:\s+[^,\s]+)*)\b'
        matches = re.finditer(range_pattern, query, re.IGNORECASE)
        
        for match in matches:
            date_range = f"{match.group(1)} to {match.group(2)}"
            entity = ExtractedEntity(
                entity_type='date_range',
                value=date_range,
                confidence=0.8,
                start_pos=match.start(),
                end_pos=match.end()
            )
            date_ranges.append(entity)
        
        return date_ranges
    
    async def parse_query_context(self, query: str, session_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse query with session context
        
        Args:
            query: Current query
            session_history: Previous queries and responses in session
            
        Returns:
            Enhanced query understanding with context
        """
        
        # Extract entities and intent
        entities = await self.extract_entities(query)
        intent = await self.classify_intent(query)
        
        # Analyze context from session history
        context_analysis = self._analyze_session_context(query, session_history)
        
        # Resolve pronouns and references
        resolved_entities = self._resolve_references(entities, context_analysis)
        
        # Determine query scope
        query_scope = self._determine_query_scope(query, entities, context_analysis)
        
        return {
            'original_query': query,
            'entities': resolved_entities,
            'intent': intent,
            'context_analysis': context_analysis,
            'query_scope': query_scope,
            'clarifications_needed': self._identify_clarifications(resolved_entities, intent)
        }
    
    def _analyze_session_context(self, query: str, session_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze session context for query understanding"""
        
        context = {
            'previous_entities': {},
            'topic_continuity': False,
            'reference_resolution': {},
            'conversation_state': 'new'  # new, continuation, followup
        }
        
        if not session_history:
            return context
        
        # Extract entities from previous queries
        for hist_item in session_history[-3:]:  # Look at last 3 interactions
            hist_entities = hist_item.get('entities', {})
            for entity_type, entities in hist_entities.items():
                if entity_type not in context['previous_entities']:
                    context['previous_entities'][entity_type] = []
                context['previous_entities'][entity_type].extend(entities)
        
        # Check for topic continuity
        if session_history:
            last_intent = session_history[-1].get('intent', {}).get('primary_intent')
            current_intent_keywords = query.lower().split()
            
            # Simple heuristic for topic continuity
            context['topic_continuity'] = any(
                word in str(last_intent).lower() 
                for word in current_intent_keywords
            ) if last_intent else False
            
            context['conversation_state'] = 'continuation' if context['topic_continuity'] else 'followup'
        
        return context
    
    def _resolve_references(self, entities: Dict[str, List[ExtractedEntity]], context: Dict[str, Any]) -> Dict[str, List[ExtractedEntity]]:
        """Resolve pronouns and references in entities"""
        
        resolved_entities = entities.copy()
        
        # Look for pronouns and ambiguous references
        pronoun_patterns = {
            'it': ['transaction', 'fee', 'charge'],
            'this': ['transaction', 'fee', 'charge', 'amount'],
            'that': ['transaction', 'fee', 'charge', 'amount'],
            'they': ['transactions', 'fees', 'charges']
        }
        
        # Check for pronouns in query and resolve from context
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                entity_value_lower = entity.value.lower()
                
                if entity_value_lower in pronoun_patterns:
                    # Try to resolve from previous entities
                    previous_entities = context.get('previous_entities', {})
                    
                    for possible_type in pronoun_patterns[entity_value_lower]:
                        if possible_type in previous_entities and previous_entities[possible_type]:
                            # Replace pronoun with most recent entity
                            resolved_entity = previous_entities[possible_type][-1]
                            entity.value = resolved_entity.value
                            entity.entity_type = resolved_entity.entity_type
                            entity.confidence *= 0.8  # Lower confidence for resolved references
                            break
        
        return resolved_entities
    
    def _determine_query_scope(self, query: str, entities: Dict[str, List[ExtractedEntity]], context: Dict[str, Any]) -> str:
        """Determine the scope of the query"""
        
        # Check for scope indicators
        scope_indicators = {
            'single': ['this', 'single', 'one', 'specific'],
            'multiple': ['multiple', 'several', 'all', 'batch'],
            'range': ['range', 'between', 'from', 'to'],
            'pattern': ['pattern', 'trend', 'unusual', 'anomaly']
        }
        
        query_lower = query.lower()
        
        for scope, indicators in scope_indicators.items():
            if any(indicator in query_lower for indicator in indicators):
                return scope
        
        # Determine scope from entities
        if 'pan_range' in entities:
            return 'range'
        elif 'pan' in entities and len(entities['pan']) == 1:
            return 'single'
        elif 'pan' in entities and len(entities['pan']) > 1:
            return 'multiple'
        
        return 'single'  # Default scope
    
    def _identify_clarifications(self, entities: Dict[str, List[ExtractedEntity]], intent: QueryIntent) -> List[str]:
        """Identify what clarifications might be needed"""
        
        clarifications = []
        
        # Check for missing critical entities based on intent
        if intent.primary_intent == IntentType.TRANSACTION_INVESTIGATION:
            if 'pan' not in entities and 'transaction_id' not in entities:
                clarifications.append("Need PAN or transaction ID")
            if 'date' not in entities and 'relative_date' not in entities:
                clarifications.append("Need date or time period")
        
        elif intent.primary_intent == IntentType.PAN_RANGE_ANALYSIS:
            if 'pan_range' not in entities:
                clarifications.append("Need PAN range specification")
            if 'date' not in entities and 'relative_date' not in entities:
                clarifications.append("Need date range")
        
        elif intent.primary_intent == IntentType.FEE_DISPUTE:
            if 'amount' not in entities:
                clarifications.append("Need disputed amount")
            if 'fee_type' not in entities:
                clarifications.append("Need fee type specification")
        
        return clarifications
