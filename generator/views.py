from django.shortcuts import render, get_object_or_404
import requests
import base64
from io import BytesIO
from PIL import Image
import os
from dotenv import load_dotenv
from django.conf import settings
import uuid
from .models import Character  # Assuming Character is the model for characters

# Load environment variables from .env file
load_dotenv()

HUGGING_FACE_API_KEY = os.getenv("HUGGING_FACE_API_KEY")

API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"
headers = {"Authorization": f"Bearer {HUGGING_FACE_API_KEY}"}

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"API Error: {response.status_code}, {response.text}")

def homepage(request):
    context = {}
    try:
        if request.method == "POST":
            # Récupérer le prompt de l'utilisateur
            user_prompt = request.POST.get("prompt")
            
            # Générer l'image avec l'API
            image_bytes = query({
                "inputs": user_prompt,
            })
            
            # Convertir l'image en Base64 pour l'afficher dans le template
            image = Image.open(BytesIO(image_bytes))
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # Enregistrer l'image dans le dossier media
            image_name = f"{uuid.uuid4()}.png"
            image_path = os.path.join(settings.MEDIA_ROOT, image_name)
            image.save(image_path)

            # Insérer l'image dans la base de données pour le character avec id=1
            character = get_object_or_404(Character, id=1)
            character.image = f"{settings.MEDIA_URL}{image_name}"
            character.save()

            # Passer l'image en Base64, le chemin de l'image et le prompt au contexte
            context["image_base64"] = image_base64
            context["image_path"] = f"{settings.MEDIA_URL}{image_name}"
            context["user_prompt"] = user_prompt
            
        else:
            pass
        
    except Exception as e:
        context["error"] = str(e)
    
    return render(request, "homepage.html", context)
