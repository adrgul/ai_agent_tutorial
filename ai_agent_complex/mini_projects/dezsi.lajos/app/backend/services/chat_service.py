from datetime import datetime
from domain.interfaces import IConversationRepository
from domain.models import Message, ChatResponse
from services.agent import TriageAgent

class ChatService:
    def __init__(self, agent: TriageAgent, repo: IConversationRepository):
        self.agent = agent
        self.repo = repo

    async def process_message(self, conversation_id: str, message_content: str) -> ChatResponse:
        # Save User Message
        user_msg = Message(role="user", content=message_content)
        await self.repo.add_message(conversation_id, user_msg)
        
        # Run Agent
        result = await self.agent.run(message_content)
        
        # Save Assistant Message
        # We use the draft body as the main response, but we might want to store the structured output too
        response_text = result["answer_draft"]["body"]
        asst_msg = Message(role="assistant", content=response_text)
        await self.repo.add_message(conversation_id, asst_msg)
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            generated_ticket=result
        )

    async def get_history(self, conversation_id: str):
        return await self.repo.get_history(conversation_id)

    async def clear_history(self, conversation_id: str):
        await self.repo.clear_history(conversation_id)
