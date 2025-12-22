import os
from typing import List, Dict, Any, Type
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

from domain.interfaces import ILLMClient, IVectorDBClient

class GeminiClient(ILLMClient):
    def __init__(self, model_name: str = "gemini-3-flash-preview", temperature: float = 0):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("ERROR: GOOGLE_API_KEY not found in environment")
        else:
            print(f"DEBUG: Initializing GeminiClient with key length {len(api_key)}")
        
        # Override model if set in env
        env_model = os.getenv("LLM_MODEL")
        if env_model:
            model_name = env_model
            print(f"DEBUG: Using model: {model_name}")
        else:
            print(f"DEBUG: Using default model: {model_name}")

        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=temperature, google_api_key=api_key)

    async def generate(self, prompt: str) -> str:
        response = await self.llm.ainvoke(prompt)
        return response.content

    async def generate_structured(self, prompt: str, response_model: Type[Any]) -> Any:
        try:
            structured_llm = self.llm.with_structured_output(response_model)
            return await structured_llm.ainvoke(prompt)
        except Exception as e:
            print(f"ERROR in Gemini generate_structured: {e}")
            raise e

class QdrantVectorDB(IVectorDBClient):
    def __init__(self, path: str = "./qdrant_db", collection_name: str = "medical_kb"):
        self.client = QdrantClient(path=path)
        self.collection_name = collection_name
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
             print("ERROR: GOOGLE_API_KEY for Embeddings not found")
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
        
        # Ensure collection exists
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE), # text-embedding-004 has 768 dim
            )

    async def search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        try:
            print(f"DEBUG: Embedding query: {query}")
            query_vector = self.embeddings.embed_query(query)
            print(f"DEBUG: Query embedded, performing search...")
            # print(f"DEBUG: Client type: {type(self.client)}")
            # print(f"DEBUG: Client attributes: {dir(self.client)[:10]}")
            
            # Use query_points as search is deprecated/removed in this version
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit
            )
            # query_points returns QueryResponse which has 'points' attribute
            hits = results.points
            
            print(f"DEBUG: Search returned {len(hits)} hits")
            return [{"text": hit.payload.get("text", ""), "source": hit.payload.get("source", ""), "score": hit.score} for hit in hits]
        except Exception as e:
            print(f"ERROR in search: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def upsert(self, text: str, metadata: Dict[str, Any]):
        vector = self.embeddings.embed_query(text)
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={"text": text, **metadata}
        )
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
