"""Chat streaming use case - orchestrates graph execution and streaming."""
import asyncio
from typing import AsyncGenerator, Dict, Any
import time
from app.domain.state import SupportState
from app.domain.events import TraceEvent
from app.application.orchestration.graph_factory import GraphFactory, PatternType
from app.infrastructure.cache.memory_cache import routing_cache, kb_cache, synthesis_cache
from app.core.logging import get_logger
from app.core.config import config

logger = get_logger(__name__)


class ChatStreamUseCase:
    """
    Use case for streaming chat interactions.
    
    This orchestrates the entire flow:
    1. Initialize state
    2. Execute graph for selected pattern
    3. Stream trace events and response words
    4. Return final result with statistics
    """
    
    async def execute(
        self,
        pattern: PatternType,
        message: str,
        customer_id: str = None,
        channel: str = "chat",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute the chat stream.
        
        Args:
            pattern: Which multi-agent pattern to use
            message: User message
            customer_id: Optional customer identifier
            channel: Communication channel (chat, email, etc.)
            
        Yields:
            Stream of events:
            - {"type": "trace", "event": {...}}
            - {"type": "word", "content": "..."}
            - {"type": "done", "final": {...}}
        """
        start_time = time.time()
        
        try:
            # Initialize state
            initial_state: SupportState = {
                "messages": [{"role": "user", "content": message}],
                "selected_pattern": pattern,
                "active_agent": None,
                "ticket": None,
                "agent_assist": None,
                "sources": [],
                "trace": [],
                "recursion_depth": 0,
                "customer_id": customer_id,
                "customer_tier": None,
                "channel": channel,
                "final_answer": None,
                "routing_decision": None,
                "specialist_results": None,
            }
            
            # Create graph
            graph = GraphFactory.create(pattern)
            
            # Execute graph with recursion limit
            logger.info(f"Executing pattern '{pattern}' for message: {message[:50]}...")
            
            final_state = None
            try:
                # Run the graph
                result = graph.invoke(
                    initial_state,
                    config={"recursion_limit": config.MAX_RECURSION_LIMIT}
                )
                final_state = result
                
                # Stream trace events in real-time
                for event in result.get("trace", []):
                    yield {
                        "type": "trace",
                        "event": event.model_dump() if hasattr(event, "model_dump") else event
                    }
                    await asyncio.sleep(0.01)  # Small delay for UI smoothness
                
            except Exception as e:
                logger.error(f"Graph execution error: {e}", exc_info=True)
                # Add error trace event
                error_event = TraceEvent.node_end("error", {"error": str(e)})
                yield {
                    "type": "trace",
                    "event": error_event.model_dump()
                }
                # Generate fallback response
                final_state = initial_state.copy()
                final_state["final_answer"] = f"I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists. Error: {str(e)}"
            
            # Get final answer
            final_answer = final_state.get("final_answer", "I'm sorry, I couldn't generate a response.")
            
            # Stream the answer word by word with proper spacing
            words = final_answer.split()
            for i, word in enumerate(words):
                # Add space before word (except first), then the word
                content = f" {word}" if i > 0 else word
                yield {"type": "word", "content": content}
                await asyncio.sleep(0.02)  # Simulate typing effect
            
            # Calculate statistics
            end_time = time.time()
            cache_stats = {
                "routing": routing_cache.get_stats(),
                "kb": kb_cache.get_stats(),
                "synthesis": synthesis_cache.get_stats(),
            }
            
            # Prepare final result
            final_result = {
                "text": final_answer,
                "pattern": pattern,
                "ticket": final_state.get("ticket").model_dump() if final_state.get("ticket") else None,
                "agent_assist": final_state.get("agent_assist").model_dump() if final_state.get("agent_assist") else None,
                "sources": final_state.get("sources", []),
                "active_agent": final_state.get("active_agent"),
                "stats": {
                    "latency_ms": int((end_time - start_time) * 1000),
                    "cache_stats": cache_stats,
                    "recursion_depth": final_state.get("recursion_depth", 0),
                    "trace_events": len(final_state.get("trace", [])),
                },
                "state_snapshot": {
                    "selected_pattern": pattern,
                    "active_agent": final_state.get("active_agent"),
                    "recursion_depth": final_state.get("recursion_depth", 0),
                    "sources_count": len(final_state.get("sources", [])),
                    "messages_count": len(final_state.get("messages", [])),
                }
            }
            
            # Send done message
            yield {
                "type": "done",
                "final": final_result
            }
            
            logger.info(f"Chat stream completed in {final_result['stats']['latency_ms']}ms")
            
        except Exception as e:
            logger.error(f"Fatal error in chat stream: {e}", exc_info=True)
            # Send error as done message
            yield {
                "type": "done",
                "final": {
                    "text": "A system error occurred. Please try again.",
                    "error": str(e),
                    "pattern": pattern,
                }
            }
