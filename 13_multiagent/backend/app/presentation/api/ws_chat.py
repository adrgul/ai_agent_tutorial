"""WebSocket chat endpoint."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional
from pydantic import BaseModel
import json
from app.application.usecases.chat_stream import ChatStreamUseCase
from app.application.orchestration.graph_factory import PatternType
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model."""
    pattern: PatternType
    message: str
    customer_id: Optional[str] = None
    channel: Optional[str] = "chat"


@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat.
    
    Client sends:
    {
        "pattern": "router|subagents|handoffs|skills|custom_workflow",
        "message": "user message",
        "customer_id": "optional customer ID",
        "channel": "chat|email"
    }
    
    Server streams:
    - {"type": "trace", "event": {...}}
    - {"type": "word", "content": "..."}
    - {"type": "done", "final": {...}}
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {data[:100]}...")
            
            try:
                request_data = json.loads(data)
                
                # Validate request
                pattern = request_data.get("pattern", "router")
                message = request_data.get("message", "")
                customer_id = request_data.get("customer_id")
                channel = request_data.get("channel", "chat")
                
                if not message:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Message is required"
                    })
                    continue
                
                # Execute chat stream
                use_case = ChatStreamUseCase()
                
                async for event in use_case.execute(
                    pattern=pattern,
                    message=message,
                    customer_id=customer_id,
                    channel=channel,
                ):
                    # Send event to client
                    await websocket.send_json(event)
                
                logger.info("Chat stream completed successfully")
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "message": f"Error: {str(e)}"
                })
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.close()
        except:
            pass
