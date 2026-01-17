from typing import List, Dict
from domain.interfaces import IConversationRepository
from domain.models import Message

class InMemConversationRepository(IConversationRepository):
    def __init__(self):
        self._conversations: Dict[str, List[Message]] = {}

    async def add_message(self, conversation_id: str, message: Message):
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
        self._conversations[conversation_id].append(message)

    async def get_history(self, conversation_id: str) -> List[Message]:
        return self._conversations.get(conversation_id, [])

    async def clear_history(self, conversation_id: str):
        if conversation_id in self._conversations:
            self._conversations[conversation_id] = []
