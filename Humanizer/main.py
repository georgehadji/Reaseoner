import uuid
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from tasks import process_humanization_task
from utils import apply_zws_cloak

app = FastAPI(title="Ghostwriter Enterprise API")

class HumanizeRequest(BaseModel):
    text: str
    tone: str = "Professional"
    iterations: int = 1

@app.post("/humanize")
async def start_humanization(request: HumanizeRequest):
    # Δημιουργία μοναδικού ID για το task
    task_id = str(uuid.uuid4())
    
    # Ανάθεση της εργασίας στον worker (Async)
    process_humanization_task.delay(task_id, request.text, request.tone, request.iterations)
    
    return {"task_id": task_id, "status": "Processing", "message": "Check status endpoint for results"}

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    # Εδώ θα γινόταν ανάκτηση από Redis/Database
    # Επιστρέφει το αποτέλεσμα αν είναι έτοιμο
    return {"task_id": task_id, "status": "Check Redis/DB for result"}