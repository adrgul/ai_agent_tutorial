# Pydantic Használat az Alkalmazásban

## Áttekintés

A **Pydantic** egy Python könyvtár adatvalidációhoz és beállításkezeléshez típusannotációk használatával. Az alkalmazásunkban a Pydantic központi szerepet játszik az adatmodellek definiálásában, validációban és API dokumentációban.

## Mi az a Pydantic?

A Pydantic a következőket teszi lehetővé:
- **Típusbiztos adatmodellek** definiálása Python osztályokkal
- **Automatikus validáció** runtime-ban
- **JSON szerializáció/deszerializáció** egyszerűsítése
- **FastAPI integráció** automatikus API dokumentációhoz
- **Default értékek** és **factory függvények** támogatása
- **Egyedi validációs szabályok** definiálása

## Pydantic az Alkalmazásban

### Fő Használati Területek

```
1. Domain modellek (domain/models.py)
   └─> Üzleti entitások: Message, UserProfile, ChatRequest, ChatResponse

2. RAG modellek (rag/models.py)
   └─> Dokumentum és chunk modellek: Document, Chunk, RetrievalResult

3. Konfigurációs modellek (rag/config.py)
   └─> RAG beállítások: RAGConfig, ChunkingConfig, EmbeddingConfig

4. FastAPI request/response modellek (main.py)
   └─> API endpoint sémák és validáció

5. Tool argumentum sémák (services/tools.py)
   └─> LangChain eszköz paraméterek
```

## 1. Domain Modellek

### Fájl: `backend/domain/models.py`

A domain modellek az alkalmazás központi üzleti entitásait reprezentálják.

#### Message Modell

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional, Dict, Any

class Message(BaseModel):
    """Egyetlen üzenet a beszélgetésben."""
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None
```

**Kulcsfontosságú elemek:**
- `Literal["user", "assistant", "system", "tool"]` - Strict enum-szerű típus
- `Field(default_factory=datetime.now)` - Dinamikus default érték generálás
- `Optional[Dict[str, Any]]` - Opcionális mező flexibilis tartalommal

**Használat:**
```python
# Automatikus validáció és default értékek
message = Message(role="user", content="Hello!")
# timestamp automatikusan kitöltődik
# metadata None marad, ha nincs megadva

# Hibás role esetén ValidationError:
# message = Message(role="invalid", content="Hi")  # ❌ ValueError
```

#### UserProfile Modell

```python
class UserProfile(BaseModel):
    """Felhasználói profil perzisztens tároláshoz."""
    user_id: str
    language: str = "hu"
    default_city: str = "Budapest"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    preferences: Dict[str, Any] = Field(default_factory=dict)
```

**Kulcsfontosságú elemek:**
- **Default értékek**: `language = "hu"` - Egyszerű alapértelmezett
- **Factory függvények**: `Field(default_factory=dict)` - Új dict minden példányhoz
- **Perzisztencia**: JSON-ba szerializálható minden mező

**Miért factory függvény?**
```python
# ❌ ROSSZ - Ugyanaz a dict referencia minden példányban:
# preferences: Dict[str, Any] = {}

# ✅ JÓ - Új dict minden példányhoz:
preferences: Dict[str, Any] = Field(default_factory=dict)
```

**Használat:**
```python
# Új felhasználó minimal adatokkal
user = UserProfile(user_id="user_123")
# language="hu", default_city="Budapest", preferences={} automatikusan

# Teljes profil
user = UserProfile(
    user_id="user_456",
    language="en",
    default_city="London",
    preferences={"theme": "dark", "notifications": True}
)
```

#### ChatRequest és ChatResponse

```python
class ChatRequest(BaseModel):
    """Bejövő chat kérés a frontendtől."""
    user_id: str
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    """Válasz a frontendnek."""
    final_answer: str
    tools_used: List[Dict[str, Any]] = Field(default_factory=list)
    memory_snapshot: Dict[str, Any] = Field(default_factory=dict)
    logs: Optional[List[str]] = None
    rag_context: Optional[RAGContext] = None
    rag_metrics: Optional[RAGMetrics] = None
    debug_logs: List[str] = Field(default_factory=list)
```

**FastAPI Integráció:**
```python
from fastapi import FastAPI
from domain.models import ChatRequest, ChatResponse

app = FastAPI()

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    FastAPI automatikusan:
    1. Validálja a bejövő JSON-t ChatRequest séma szerint
    2. Deszerializálja Python objektummá
    3. Szerializálja a ChatResponse-t JSON-né
    4. Generál OpenAPI (Swagger) dokumentációt
    """
    result = await chat_service.process(request)
    return ChatResponse(
        final_answer=result["answer"],
        tools_used=result.get("tools", []),
        # ... további mezők
    )
```

**Validációs Példák:**
```python
# ✅ Valid kérés
request = ChatRequest(user_id="123", message="Hello!")

# ✅ Valid kérés session_id-val
request = ChatRequest(
    user_id="123",
    message="Hello!",
    session_id="session_456"
)

# ❌ Hibás kérés - hiányzó kötelező mező
# request = ChatRequest(message="Hello!")  # ValidationError: user_id missing

# ❌ Hibás típus
# request = ChatRequest(user_id=123, message="Hi")  # ValidationError: user_id must be str
```

## 2. RAG Modellek

### Fájl: `backend/rag/models.py`

#### Document Modell

```python
import uuid
from pydantic import BaseModel, Field

class Document(BaseModel):
    """Feltöltött dokumentum reprezentációja."""
    
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    filename: str
    content: str
    chunk_count: int = 0
    size_chars: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

**Kulcsfontosságú elemek:**

1. **UUID generálás**: `default_factory=lambda: str(uuid.uuid4())`
   ```python
   # Minden új dokumentum egyedi ID-t kap
   doc = Document(user_id="user_123", filename="file.txt", content="...")
   # doc.doc_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
   ```

2. **Config osztály**: Egyedi JSON szerializáció
   ```python
   # datetime objektumok ISO formátumú stringgé alakulnak
   doc_dict = doc.model_dump()
   # created_at: "2026-01-08T13:45:30.123456"
   ```

3. **Használat:**
   ```python
   # Dokumentum létrehozása feltöltéskor
   doc = Document(
       user_id="user_123",
       filename="report.pdf",
       content="Full PDF text content...",
       chunk_count=15,
       size_chars=5420,
       metadata={"file_type": "pdf", "pages": 5}
   )
   
   # JSON-ba mentés
   with open(f"data/docs/{doc.doc_id}.json", "w") as f:
       f.write(doc.model_dump_json(indent=2))
   ```

#### Chunk Modell

```python
class Chunk(BaseModel):
    """Szöveg chunk metaadatokkal a vektor tároláshoz."""
    
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    user_id: str
    text: str
    chunk_index: int
    start_offset: int = 0
    end_offset: int = 0
    token_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def source_label(self) -> str:
        """Emberbarát forrás címke generálás."""
        filename = self.metadata.get("filename", "unknown")
        section = self.metadata.get("section_heading", "")
        if section:
            return f"{filename} - {section}"
        return f"{filename} (chunk {self.chunk_index + 1})"
```

**Kulcsfontosságú elemek:**

1. **Property decorator**: Számított mező
   ```python
   chunk = Chunk(
       doc_id="doc_123",
       user_id="user_456",
       text="This is a text chunk...",
       chunk_index=3,
       metadata={"filename": "report.pdf", "section_heading": "Introduction"}
   )
   
   # Automatikus címke generálás
   print(chunk.source_label)  # "report.pdf - Introduction"
   ```

2. **Használat RAG pipeline-ban:**
   ```python
   # Dokumentum chunkolása
   chunks = []
   for i, text_segment in enumerate(chunked_texts):
       chunk = Chunk(
           doc_id=document.doc_id,
           user_id=document.user_id,
           text=text_segment,
           chunk_index=i,
           start_offset=offsets[i][0],
           end_offset=offsets[i][1],
           token_count=len(text_segment.split()),
           metadata={
               "filename": document.filename,
               "section_heading": detect_section(text_segment)
           }
       )
       chunks.append(chunk)
   ```

#### RetrievalResult Modell

```python
class RetrievalResult(BaseModel):
    """Lekért chunk hasonlósági pontszámokkal."""
    
    chunk: Chunk
    score: float  # Kombinált hasonlósági pontszám (0-1)
    dense_score: Optional[float] = None  # Vektor hasonlóság
    sparse_score: Optional[float] = None  # BM25 pontszám (jövőbeli hibrid kereséshez)
    rank: int = 0  # Pozíció az eredménylistában (1-indexelve)
    
    @property
    def chunk_id(self) -> str:
        return self.chunk.chunk_id
    
    @property
    def text(self) -> str:
        return self.chunk.text
    
    @property
    def source_label(self) -> str:
        return self.chunk.source_label
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertálás dictionary-vé API válaszokhoz."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_label": self.source_label,
            "score": self.score,
            "dense_score": self.dense_score,
            "sparse_score": self.sparse_score,
            "rank": self.rank,
            "metadata": self.chunk.metadata
        }
```

**Property pattern:**
```python
# Properties gyors hozzáférést biztosítanak nested mezőkhöz
result = RetrievalResult(
    chunk=chunk_obj,
    score=0.92,
    dense_score=0.95,
    rank=1
)

# Egyszerűbb hozzáférés:
print(result.text)  # chunk.text helyett
print(result.source_label)  # chunk.source_label helyett

# API válasz generálás
response_data = result.to_dict()
```

## 3. Konfigurációs Modellek

### Fájl: `backend/rag/config.py`

```python
class ChunkingConfig(BaseModel):
    """Chunk létrehozás beállításai."""
    chunk_size: int = Field(default=512, ge=100, le=2048)
    chunk_overlap: int = Field(default=50, ge=0)
    
    class Config:
        validate_assignment = True

class EmbeddingConfig(BaseModel):
    """Embedding szolgáltatás beállításai."""
    model_name: str = "text-embedding-3-small"
    api_key: str
    batch_size: int = Field(default=100, ge=1, le=500)
    dimensions: int = Field(default=1536, ge=256)

class RAGConfig(BaseModel):
    """Fő RAG konfiguráció."""
    chunking: ChunkingConfig
    embedding: EmbeddingConfig
    vector_store: VectorStoreConfig
    retrieval: RetrievalConfig
    ingestion: IngestionConfig
    
    @classmethod
    def from_env(cls) -> "RAGConfig":
        """Konfiguráció betöltése környezeti változókból."""
        return cls(
            chunking=ChunkingConfig(
                chunk_size=int(os.getenv("CHUNK_SIZE", "512")),
                chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50"))
            ),
            embedding=EmbeddingConfig(
                model_name=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
                api_key=os.getenv("OPENAI_API_KEY"),
                batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
            ),
            # ... további config szakaszok
        )
```

**Kulcsfontosságú elemek:**

1. **Validációs Constraints**:
   ```python
   # ge = greater than or equal (>=)
   # le = less than or equal (<=)
   chunk_size: int = Field(default=512, ge=100, le=2048)
   
   # ✅ Valid értékek
   config = ChunkingConfig(chunk_size=512, chunk_overlap=50)
   config = ChunkingConfig(chunk_size=1024, chunk_overlap=100)
   
   # ❌ Hibás értékek
   # config = ChunkingConfig(chunk_size=50)  # ValidationError: >= 100
   # config = ChunkingConfig(chunk_size=3000)  # ValidationError: <= 2048
   ```

2. **validate_assignment Config**:
   ```python
   config = ChunkingConfig(chunk_size=512)
   
   # validate_assignment = True esetén runtime validáció:
   # config.chunk_size = 50  # ❌ ValidationError
   config.chunk_size = 1024  # ✅ OK
   ```

3. **Class Method Factory**:
   ```python
   # Környezeti változókból konfiguráció betöltése
   rag_config = RAGConfig.from_env()
   
   # Automatikus validáció és default értékek
   print(rag_config.chunking.chunk_size)  # 512 vagy CHUNK_SIZE env var
   print(rag_config.embedding.model_name)  # "text-embedding-3-small" vagy EMBEDDING_MODEL env var
   ```

**Használat az alkalmazásban:**

```python
# main.py
from rag.config import RAGConfig

# Alkalmazás indításkor
rag_config = RAGConfig.from_env()

# Config átadása szolgáltatásoknak
embedding_service = OpenAIEmbeddingService(rag_config.embedding)
vector_store = ChromaVectorStore(rag_config.vector_store)
chunker = OverlappingChunker(rag_config.chunking)
```

## 4. Field() Használata

A `Field()` függvény a Pydantic egyik legfontosabb eszköze a mezők testreszabásához.

### Default Értékek

```python
# Statikus default
name: str = Field(default="Unknown")

# Dinamikus default (factory)
created_at: datetime = Field(default_factory=datetime.now)

# Üres lista/dict (factory kötelező!)
tags: List[str] = Field(default_factory=list)
metadata: Dict[str, Any] = Field(default_factory=dict)
```

### Validációs Constraints

```python
from pydantic import Field

# Numerikus constraints
age: int = Field(ge=0, le=150)  # 0 <= age <= 150
score: float = Field(gt=0.0, lt=1.0)  # 0.0 < score < 1.0
count: int = Field(ge=1)  # count >= 1

# String constraints
username: str = Field(min_length=3, max_length=20)
email: str = Field(regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Lista constraints
items: List[str] = Field(min_items=1, max_items=10)
```

### Dokumentáció és Metadata

```python
class User(BaseModel):
    user_id: str = Field(
        description="Unique user identifier",
        example="user_123456"
    )
    age: int = Field(
        ge=0,
        le=150,
        description="User's age in years",
        example=25
    )
```

**FastAPI dokumentációban megjelenik:**
```json
{
  "user_id": {
    "type": "string",
    "description": "Unique user identifier",
    "example": "user_123456"
  },
  "age": {
    "type": "integer",
    "minimum": 0,
    "maximum": 150,
    "description": "User's age in years",
    "example": 25
  }
}
```

## 5. JSON Szerializáció és Deszerializáció

### Model → JSON

```python
message = Message(role="user", content="Hello!")

# 1. Dict formátumban
message_dict = message.model_dump()
# {'role': 'user', 'content': 'Hello!', 'timestamp': datetime(...), 'metadata': None}

# 2. JSON string
message_json = message.model_dump_json()
# '{"role":"user","content":"Hello!","timestamp":"2026-01-08T13:45:30.123456","metadata":null}'

# 3. JSON file-ba írás
with open("message.json", "w") as f:
    f.write(message.model_dump_json(indent=2))
```

### JSON → Model

```python
# 1. Dict-ből
message_dict = {
    "role": "user",
    "content": "Hello!",
    "timestamp": "2026-01-08T13:45:30.123456"
}
message = Message(**message_dict)

# 2. JSON string-ből
message_json = '{"role":"user","content":"Hello!"}'
message = Message.model_validate_json(message_json)

# 3. JSON file-ból
with open("message.json", "r") as f:
    message_data = json.load(f)
message = Message(**message_data)
```

### Egyedi JSON Encoders

```python
class Document(BaseModel):
    doc_id: str
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Használat
doc = Document(doc_id="123", created_at=datetime.now())
json_str = doc.model_dump_json()
# created_at ISO formátumban: "2026-01-08T13:45:30.123456"
```

## 6. Validáció és Hibakezelés

### Automatikus Validáció

```python
from pydantic import ValidationError

try:
    # Hibás típus
    message = Message(role="invalid_role", content="Hi")
except ValidationError as e:
    print(e.json())
    """
    [
      {
        "type": "literal_error",
        "loc": ["role"],
        "msg": "Input should be 'user', 'assistant', 'system' or 'tool'",
        "input": "invalid_role"
      }
    ]
    """

try:
    # Hiányzó kötelező mező
    request = ChatRequest(message="Hello!")
except ValidationError as e:
    print(e.json())
    """
    [
      {
        "type": "missing",
        "loc": ["user_id"],
        "msg": "Field required",
        "input": {"message": "Hello!"}
      }
    ]
    """
```

### FastAPI Error Handling

```python
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    # FastAPI automatikusan validál
    # ValidationError esetén 422 Unprocessable Entity HTTP válasz
    
    try:
        result = await chat_service.process(request)
        return ChatResponse(**result)
    except ValidationError as e:
        # Ez csak akkor kell, ha manuálisan dolgozunk modelekkel
        raise HTTPException(status_code=422, detail=e.errors())
```

## 7. Használati Minták az Alkalmazásban

### Pattern 1: Repository Layer

```python
# infrastructure/repositories.py
class FileUserRepository:
    """Felhasználói profilok file-alapú tárolása."""
    
    async def save(self, profile: UserProfile) -> None:
        """Profil mentése JSON file-ba."""
        file_path = Path(self.data_dir) / f"{profile.user_id}.json"
        
        # Pydantic automatikus JSON szerializáció
        with open(file_path, "w") as f:
            f.write(profile.model_dump_json(indent=2))
    
    async def load(self, user_id: str) -> Optional[UserProfile]:
        """Profil betöltése JSON file-ból."""
        file_path = Path(self.data_dir) / f"{user_id}.json"
        
        if not file_path.exists():
            return None
        
        with open(file_path, "r") as f:
            data = json.load(f)
        
        # Pydantic automatikus validáció
        return UserProfile(**data)
```

**Előnyök:**
- Automatikus validáció betöltéskor
- Típusbiztos mentés/betöltés
- Verziókezelés (ha séma változik, ValidationError jelzi)

### Pattern 2: Service Layer Response

```python
# services/chat_service.py
class ChatService:
    async def process(self, request: ChatRequest) -> Dict[str, Any]:
        """Chat kérés feldolgozása."""
        
        # 1. Felhasználó betöltése
        user = await self.user_repo.load(request.user_id)
        if not user:
            # Default profil létrehozása Pydantic-cal
            user = UserProfile(user_id=request.user_id)
            await self.user_repo.save(user)
        
        # 2. Ágens futtatása
        result = await self.agent.run(
            user_message=request.message,
            user_id=request.user_id,
            session_id=request.session_id
        )
        
        # 3. ChatResponse modell létrehozása
        response = ChatResponse(
            final_answer=result["final_answer"],
            tools_used=result.get("tools_called", []),
            memory_snapshot={
                "user_id": user.user_id,
                "language": user.language,
                "preferences": user.preferences
            },
            rag_context=RAGContext(
                rewritten_query=result.get("rewritten_query"),
                citations=result.get("citations", []),
                chunk_count=result.get("chunk_count", 0)
            ) if result.get("rag_used") else None,
            debug_logs=result.get("debug_logs", [])
        )
        
        return response
```

### Pattern 3: Tool Arguments Validation

```python
# services/tools.py
from langchain_core.tools import tool

@tool
async def get_weather(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
) -> Dict[str, Any]:
    """
    Get weather forecast for a location.
    
    Args:
        city: City name (e.g., "Budapest")
        lat: Latitude coordinate
        lon: Longitude coordinate
    """
    # LangChain belül Pydantic validációt használ
    # Típushibák esetén automatikus hiba
    
    if not city and (lat is None or lon is None):
        return {"error": "Either city or coordinates required"}
    
    # Eszköz logika...
```

**LangChain + Pydantic:**
```python
# Pydantic modell explicit eszköz argumentumokhoz
class WeatherArgs(BaseModel):
    city: Optional[str] = Field(None, description="City name")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")

from langchain_core.tools import StructuredTool

weather_tool = StructuredTool.from_function(
    func=get_weather_impl,
    name="weather",
    description="Get weather forecast",
    args_schema=WeatherArgs  # Pydantic modell használata
)
```

## 8. Haladó Minták

### Nested Models

```python
class RAGContext(BaseModel):
    """RAG kontextus API válaszokban."""
    rewritten_query: Optional[str] = None
    citations: List[str] = Field(default_factory=list)
    chunk_count: int = 0
    used_in_response: bool = False
    chunks: List[RAGChunk] = Field(default_factory=list)  # Nested model!

class RAGChunk(BaseModel):
    """RAG chunk metaadat."""
    chunk_id: str
    text: str
    source_label: str
    score: float

class ChatResponse(BaseModel):
    """Chat válasz."""
    final_answer: str
    tools_used: List[Dict[str, Any]] = Field(default_factory=list)
    rag_context: Optional[RAGContext] = None  # Nested model!
```

**Használat:**
```python
response = ChatResponse(
    final_answer="The weather is sunny.",
    rag_context=RAGContext(
        rewritten_query="weather forecast Budapest",
        citations=["weather_data.pdf - Section 2"],
        chunk_count=3,
        used_in_response=True,
        chunks=[
            RAGChunk(
                chunk_id="chunk_123",
                text="Budapest weather is sunny with 25°C...",
                source_label="weather_data.pdf",
                score=0.92
            )
        ]
    )
)

# Automatikus nested validáció és szerializáció
response_json = response.model_dump_json()
```

### Model Inheritance

```python
class BaseEntity(BaseModel):
    """Alap entitás időbélyegekkel."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Document(BaseEntity):
    """Dokumentum örökli az időbélyegeket."""
    doc_id: str
    user_id: str
    filename: str
    content: str

class Chunk(BaseEntity):
    """Chunk is örökli az időbélyegeket."""
    chunk_id: str
    doc_id: str
    text: str
```

### Union Types és Discriminators

```python
from typing import Union
from pydantic import Field, BaseModel

class ToolSuccess(BaseModel):
    type: Literal["success"] = "success"
    result: Dict[str, Any]
    message: str

class ToolError(BaseModel):
    type: Literal["error"] = "error"
    error_code: str
    error_message: str

# Union type discriminator-ral
ToolResult = Union[ToolSuccess, ToolError]

# Használat
def process_result(result: ToolResult):
    if result.type == "success":
        # TypeScript-szerű type narrowing
        print(f"Success: {result.message}")
    else:
        print(f"Error: {result.error_message}")
```

## 9. Legjobb Gyakorlatok

### 1. Factory Függvények Használata Mutable Default Értékekhez

```python
# ❌ ROSSZ - Ugyanaz a lista/dict referencia minden példányban
class Message(BaseModel):
    tags: List[str] = []
    metadata: Dict[str, Any] = {}

# ✅ JÓ - Minden példány új lista/dict-et kap
class Message(BaseModel):
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### 2. Explicit Típusok és Optional

```python
# ❌ Kerülendő - Any mindenhol
class Config(BaseModel):
    settings: Any

# ✅ JÓ - Specifikus típusok
class Config(BaseModel):
    timeout: int
    retries: int
    headers: Dict[str, str]
    enabled: bool

# ✅ JÓ - Optional explicit jelölése
class User(BaseModel):
    name: str
    email: Optional[str] = None
    age: Optional[int] = None
```

### 3. Validációs Constraints Használata

```python
class ChunkingConfig(BaseModel):
    # Explicit boundaries
    chunk_size: int = Field(ge=100, le=2048, description="Characters per chunk")
    chunk_overlap: int = Field(ge=0, description="Overlap between chunks")
    
    # String validáció
    separator: str = Field(min_length=1, max_length=10)
    
    # Lista validáció
    stop_words: List[str] = Field(max_items=1000)
```

### 4. Dokumentáció FastAPI-hoz

```python
class ChatRequest(BaseModel):
    """Chat kérés modell automatikus API dokumentációval."""
    
    user_id: str = Field(
        description="Unique identifier for the user",
        example="user_1234567890"
    )
    message: str = Field(
        description="User's message content",
        min_length=1,
        max_length=10000,
        example="What's the weather in Budapest?"
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session identifier for conversation continuity",
        example="session_abcdef123456"
    )
```

### 5. Config Osztály Használata

```python
class Document(BaseModel):
    doc_id: str
    created_at: datetime
    content: str
    
    class Config:
        # JSON encoder egyedi típusokhoz
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
        # Értékadás validálása
        validate_assignment = True
        
        # Extra mezők kezelése
        extra = "forbid"  # vagy "allow", "ignore"
        
        # Alias használata
        fields = {
            "doc_id": {"alias": "documentId"}
        }
```

### 6. Error Handling

```python
from pydantic import ValidationError
from fastapi import HTTPException

async def create_document(data: Dict[str, Any]) -> Document:
    """Dokumentum létrehozása validációval."""
    try:
        document = Document(**data)
        await repository.save(document)
        return document
    except ValidationError as e:
        # Validációs hibák logolása
        logger.error(f"Document validation failed: {e.json()}")
        raise HTTPException(
            status_code=422,
            detail=e.errors()
        )
```

## 10. Teljes Példa: Document Upload Flow

```python
# 1. API Endpoint (main.py)
@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    user_id: str = Form(...),
    file: UploadFile = File(...)
) -> DocumentUploadResponse:
    """
    Dokumentum feltöltés Pydantic validációval.
    FastAPI automatikusan generálja az OpenAPI sémát.
    """
    
    # 2. File tartalom beolvasása
    content = await file.read()
    text_content = content.decode("utf-8")
    
    # 3. Document modell létrehozása (automatikus validáció)
    document = Document(
        user_id=user_id,
        filename=file.filename,
        content=text_content,
        size_chars=len(text_content),
        metadata={"content_type": file.content_type}
    )
    # doc_id és created_at automatikusan generálódik
    
    # 4. Mentés repository-n keresztül
    await document_repo.save(document)
    
    # 5. Chunkolás
    chunker = OverlappingChunker(config.chunking)
    text_chunks = chunker.chunk_text(document.content)
    
    chunks = []
    for i, text_chunk in enumerate(text_chunks):
        # Chunk modell létrehozása (automatikus validáció)
        chunk = Chunk(
            doc_id=document.doc_id,
            user_id=document.user_id,
            text=text_chunk,
            chunk_index=i,
            token_count=len(text_chunk.split()),
            metadata={
                "filename": document.filename,
                "section": detect_section(text_chunk)
            }
        )
        chunks.append(chunk)
    
    # 6. Vektor tárolás
    await vector_store.add_chunks(chunks)
    
    # 7. Response modell (automatikus JSON szerializáció)
    return DocumentUploadResponse(
        doc_id=document.doc_id,
        filename=document.filename,
        chunk_count=len(chunks),
        size_chars=document.size_chars,
        status="success",
        message=f"Uploaded {len(chunks)} chunks successfully"
    )

# Response modell
class DocumentUploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    size_chars: int
    status: str
    message: str
```

## 11. Debugging és Tesztelés

### Model Inspection

```python
# Schema lekérése
print(ChatRequest.model_json_schema())
"""
{
  "title": "ChatRequest",
  "type": "object",
  "properties": {
    "user_id": {"type": "string"},
    "message": {"type": "string"},
    "session_id": {"type": "string", "nullable": true}
  },
  "required": ["user_id", "message"]
}
"""

# Fields információ
for field_name, field_info in ChatRequest.model_fields.items():
    print(f"{field_name}: {field_info.annotation}, required={field_info.is_required()}")
```

### Unit Testing

```python
import pytest
from pydantic import ValidationError

def test_message_creation():
    """Message modell létrehozás tesztelése."""
    message = Message(role="user", content="Hello")
    
    assert message.role == "user"
    assert message.content == "Hello"
    assert message.timestamp is not None
    assert message.metadata is None

def test_message_invalid_role():
    """Hibás role validáció tesztelése."""
    with pytest.raises(ValidationError) as exc_info:
        Message(role="invalid", content="Hi")
    
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("role",)
    assert "literal_error" in errors[0]["type"]

def test_user_profile_defaults():
    """UserProfile default értékek tesztelése."""
    profile = UserProfile(user_id="123")
    
    assert profile.language == "hu"
    assert profile.default_city == "Budapest"
    assert profile.preferences == {}
    assert profile.created_at is not None

def test_chat_response_serialization():
    """ChatResponse JSON szerializáció tesztelése."""
    response = ChatResponse(
        final_answer="Answer",
        tools_used=[{"tool": "weather", "result": "sunny"}],
        debug_logs=["[MCP] Connected"]
    )
    
    json_str = response.model_dump_json()
    assert "Answer" in json_str
    assert "weather" in json_str
    assert "[MCP] Connected" in json_str
```

## 12. Összefoglalás

### Pydantic Előnyei az Alkalmazásban

✅ **Típusbiztonság**
- Runtime validáció minden modellnél
- IDE autocomplete és type checking
- Kevesebb runtime hiba

✅ **Automatizmus**
- JSON szerializáció/deszerializáció
- FastAPI dokumentáció generálás
- Default értékek kezelése

✅ **Karbantarthatóság**
- Egyértelmű séma definíciók
- Verziókezelés validációval
- Refactoring biztonság

✅ **Fejlesztői Élmény**
- Kevesebb boilerplate kód
- Automatikus validációs hibák
- OpenAPI/Swagger dokumentáció

### Fő Használati Területek

1. **Domain modellek** - Üzleti entitások (Message, UserProfile, etc.)
2. **RAG modellek** - Dokumentum, Chunk, RetrievalResult
3. **API sémák** - ChatRequest, ChatResponse
4. **Konfiguráció** - RAGConfig, ChunkingConfig
5. **Validáció** - Automatikus típus és constraint ellenőrzés

### Kulcsfontosságú Eszközök

- `BaseModel` - Alap osztály minden modellhez
- `Field()` - Mező konfigurálás (default, validáció, dokumentáció)
- `@property` - Számított mezők
- `Config` osztály - Globális modell beállítások
- `model_dump()` / `model_dump_json()` - Szerializáció
- `model_validate_json()` - Deszerializáció

### Következő Lépések

- Egyedi validátorok írása `@field_validator` használatával
- Model validators `@model_validator` használatával
- Generikus típusok használata (`Generic[T]`)
- Pydantic Settings használata környezeti változókhoz
- Performance optimalizáció nagy modellekhez
