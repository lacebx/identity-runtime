"""Identity Runtime - Core FastAPI Service

The identity layer that sits between users/developers and any LLM.
Loads identity specs, manages memories, assembles context.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import logging

from identity_loader import IdentityLoader
from memory_engine import MemoryEngine
from context_builder import ContextBuilder
from eval_engine import EvalEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Identity Runtime API",
    description="Portable AI identity layer - own your AI's soul, not just its prompt.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In prod: restrict to your extension/SDK origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components
identity_loader = IdentityLoader()
memory_engine = MemoryEngine()
context_builder = ContextBuilder(memory_engine, identity_loader)
eval_engine = EvalEngine(memory_engine)


# --- Request/Response Models ---

class ContextRequest(BaseModel):
    message: str
    identity_id: str
    user_id: str
    session_id: Optional[str] = None

class ContextResponse(BaseModel):
    augmented_context: str
    identity_name: str
    memories_used: int
    session_id: str

class EvaluateRequest(BaseModel):
    message: str
    response: str
    identity_id: str
    user_id: str
    session_id: Optional[str] = None

class EvaluateResponse(BaseModel):
    memories_stored: int
    summary: str
    tags: List[str]

class MemoriesResponse(BaseModel):
    identity_id: str
    user_id: str
    memories: List[dict]
    total: int


# --- Endpoints ---

@app.get("/")
def root():
    return {
        "service": "Identity Runtime",
        "version": "1.0.0",
        "status": "running",
        "tagline": "Every AI deserves its own soul."
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/context", response_model=ContextResponse)
async def get_context(req: ContextRequest):
    """
    Assemble identity context before sending a message to an LLM.
    
    1. Load identity spec
    2. Retrieve relevant memories
    3. Assemble augmented context string
    Returns: context string to prepend to user's message
    """
    try:
        identity = identity_loader.load(req.identity_id)
        if not identity:
            raise HTTPException(status_code=404, detail=f"Identity '{req.identity_id}' not found")
        
        session_id = req.session_id or f"{req.user_id}_{req.identity_id}"
        
        result = await context_builder.build(
            message=req.message,
            identity=identity,
            user_id=req.user_id,
            session_id=session_id
        )
        
        logger.info(f"Context built for identity={req.identity_id} user={req.user_id} memories={result['memories_used']}")
        
        return ContextResponse(
            augmented_context=result["context"],
            identity_name=identity["identity"]["name"],
            memories_used=result["memories_used"],
            session_id=session_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Context build error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest):
    """
    Evaluate an exchange and decide what to store as memory.
    
    Called after every LLM response.
    The eval engine determines:
    - Was a preference revealed?
    - Was a correction made?
    - Is there a milestone or decision worth remembering?
    """
    try:
        identity = identity_loader.load(req.identity_id)
        if not identity:
            raise HTTPException(status_code=404, detail=f"Identity '{req.identity_id}' not found")
        
        session_id = req.session_id or f"{req.user_id}_{req.identity_id}"
        
        result = await eval_engine.evaluate(
            message=req.message,
            response=req.response,
            identity=identity,
            user_id=req.user_id,
            session_id=session_id
        )
        
        logger.info(f"Eval complete identity={req.identity_id} stored={result['memories_stored']}")
        
        return EvaluateResponse(
            memories_stored=result["memories_stored"],
            summary=result["summary"],
            tags=result["tags"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Eval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/identity/{identity_id}")
def get_identity(identity_id: str):
    """Get a loaded identity spec by ID."""
    identity = identity_loader.load(identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail=f"Identity '{identity_id}' not found")
    return identity


@app.get("/identity")
def list_identities():
    """List all available identity specs."""
    return {"identities": identity_loader.list_all()}


@app.get("/memories/{user_id}/{identity_id}", response_model=MemoriesResponse)
def get_memories(user_id: str, identity_id: str, limit: int = 50):
    """Get stored memories for a user/identity pair."""
    memories = memory_engine.get_all(user_id=user_id, identity_id=identity_id, limit=limit)
    return MemoriesResponse(
        identity_id=identity_id,
        user_id=user_id,
        memories=memories,
        total=len(memories)
    )


@app.delete("/memories/{user_id}/{identity_id}")
def clear_memories(user_id: str, identity_id: str):
    """Clear all memories for a user/identity pair."""
    deleted = memory_engine.clear(user_id=user_id, identity_id=identity_id)
    return {"deleted": deleted, "message": "Memories cleared."}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
