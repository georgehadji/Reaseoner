from celery import Celery
import requests
from utils import apply_zws_cloak

celery_app = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

GPTZERO_API_KEY = "YOUR_KEY"

@celery_app.task
def process_humanization_task(task_id, text, tone, iterations):
    current_text = text
    
    for i in range(iterations):
        # Pass 1: Bridge Translation (Mock call)
        # Pass 2: Omni-Humanizer (Mock call)
        humanized = "Humanized result from LLM..." 
        
        # Validation Step
        ai_score = check_gptzero(humanized)
        
        if ai_score < 0.05:
            break
        current_text = humanized

    # Τελικό Cloaking
    final_output = apply_zws_cloak(humanized)
    
    # Αποθήκευση στη Redis για το Frontend
    return final_output

def check_gptzero(text):
    headers = {"x-api-key": GPTZERO_API_KEY}
    response = requests.post("https://api.gptzero.me/v2/predict/text", 
                             headers=headers, json={"document": text})
    return response.json().get("documents", [{}])[0].get("completely_generated_prob", 1.0)