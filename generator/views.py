from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView
from .models import GameConcept, Character, Location
from rest_framework import serializers
import requests
import json
import os
from dotenv import load_dotenv
import time
from django.shortcuts import get_object_or_404
import base64
from io import BytesIO
from PIL import Image
from django.conf import settings
import uuid
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

# Chargement des variables d'environnement
load_dotenv()

# Serializers
class CharacterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Character
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class GameConceptSerializer(serializers.ModelSerializer):
    characters = CharacterSerializer(many=True, read_only=True)
    locations = LocationSerializer(many=True, read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = GameConcept
        fields = ['id', 'game_genre', 'visual_atmosphere', 'thematic_keywords', 
                 'cultural_references', 'language', 'universe_description', 
                 'story_act_1', 'story_act_2', 'story_act_3', 'created_at', 
                 'updated_at', 'user', 'characters', 'locations', 'image']

class GameGeneratorViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    queryset = GameConcept.objects.all()
    serializer_class = GameConceptSerializer

    def parse_ai_response(self, response_text):
        """Parse la réponse de l'IA pour extraire les différentes parties"""
        sections = {
            "universe_description": "",
            "story_acts": ["", "", ""],
            "characters": [],
            "locations": []
        }
        
        current_section = None
        current_text = []
        
        # Analyse ligne par ligne de la réponse
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Détection des sections
            if "UNIVERS:" in line.upper():
                if current_section == "characters" and current_text:
                    sections["characters"].append("\n".join(current_text))
                elif current_section == "locations" and current_text:
                    sections["locations"].append("\n".join(current_text))
                current_section = "universe"
                current_text = []
                continue
            elif "ACTE 1:" in line.upper():
                if current_section == "universe":
                    sections["universe_description"] = "\n".join(current_text)
                current_section = "act1"
                current_text = []
                continue
            elif "ACTE 2:" in line.upper():
                if current_section == "act1":
                    sections["story_acts"][0] = "\n".join(current_text)
                current_section = "act2"
                current_text = []
                continue
            elif "ACTE 3:" in line.upper():
                if current_section == "act2":
                    sections["story_acts"][1] = "\n".join(current_text)
                current_section = "act3"
                current_text = []
                continue
            elif "PERSONNAGE" in line.upper() and ":" in line:
                if current_section == "act3":
                    sections["story_acts"][2] = "\n".join(current_text)
                elif current_section == "characters" and current_text:
                    sections["characters"].append("\n".join(current_text))
                current_section = "characters"
                current_text = []
                continue
            elif "LIEU" in line.upper() and ":" in line:
                if current_section == "characters" and current_text:
                    sections["characters"].append("\n".join(current_text))
                elif current_section == "locations" and current_text:
                    sections["locations"].append("\n".join(current_text))
                current_section = "locations"
                current_text = []
                continue
            
            # Accumulation du texte selon la section
            current_text.append(line)
        
        # Ajout du dernier élément
        if current_section == "characters" and current_text:
            sections["characters"].append("\n".join(current_text))
        elif current_section == "locations" and current_text:
            sections["locations"].append("\n".join(current_text))
        elif current_section == "act3":
            sections["story_acts"][2] = "\n".join(current_text)
            
        return sections

    def create_character_from_text(self, text, game):
        """Crée un personnage à partir du texte généré"""
        if not text or "[nom]" in text.lower():
            return None
            
        lines = text.split('\n')
        character_data = {
            "name": "Personnage",
            "character_class": "Non spécifié",
            "narrative_role": "Non spécifié",
            "background": "",
            "gameplay": "Non spécifié"
        }
        
        for line in lines:
            line = line.strip()
            if "NOM:" in line.upper():
                value = line.split(":", 1)[1].strip()
                if value and "[nom]" not in value.lower():
                    character_data["name"] = value
            elif "CLASSE:" in line.upper():
                value = line.split(":", 1)[1].strip()
                if value and "[type/classe du personnage]" not in value.lower():
                    character_data["character_class"] = value
            elif "RÔLE:" in line.upper():
                value = line.split(":", 1)[1].strip()
                if value and "[rôle dans l'histoire]" not in value.lower():
                    character_data["narrative_role"] = value
            elif "BACKGROUND:" in line.upper():
                value = line.split(":", 1)[1].strip()
                if value:
                    character_data["background"] = value
            elif "GAMEPLAY:" in line.upper():
                value = line.split(":", 1)[1].strip()
                if value and "[style de jeu unique]" not in value.lower():
                    character_data["gameplay"] = value
        
        if character_data["name"] == "Personnage" and character_data["character_class"] == "Non spécifié":
            return None
            
        return Character.objects.create(
            game=game,
            name=character_data["name"],
            character_class=character_data["character_class"],
            narrative_role=character_data["narrative_role"],
            background=character_data["background"] or text,
            gameplay_description=character_data["gameplay"]
        )

    def create_location_from_text(self, text, game):
        """Crée un lieu à partir du texte généré"""
        if not text:
            return None
            
        lines = text.split('\n')
        location_data = {
            "name": "Lieu",
            "description": "",
            "significance": "Non spécifié"
        }
        
        for line in lines:
            line = line.strip()
            if "NOM:" in line.upper():
                value = line.split(":", 1)[1].strip()
                if value and "[nom du lieu]" not in value.lower():
                    location_data["name"] = value
            elif "DESCRIPTION:" in line.upper():
                value = line.split(":", 1)[1].strip()
                if value and "[description atmosphérique]" not in value.lower():
                    location_data["description"] = value
            elif "IMPORTANCE:" in line.upper():
                value = line.split(":", 1)[1].strip()
                if value and "[rôle dans l'histoire]" not in value.lower():
                    location_data["significance"] = value
        
        if location_data["name"] == "Lieu" and not location_data["description"]:
            return None
            
        return Location.objects.create(
            game=game,
            name=location_data["name"],
            description=location_data["description"] or text,
            significance=location_data["significance"]
        )

    @action(detail=False, methods=['post'])
    def generate_game(self, request):
        # Utilisation directe de l'utilisateur connecté
        data = request.data.copy()
        data['user'] = request.user.id
        
        # Récupération des données du formulaire
        game_genre = data.get('game_genre')
        visual_atmosphere = data.get('visual_atmosphere')
        thematic_keywords = data.get('thematic_keywords')
        cultural_references = data.get('cultural_references', '')
        language = data.get('language', 'fr')

        # Création du prompt pour Mistral
        prompt = f"""[INST]Tu es un expert en game design. Génère un concept de jeu vidéo détaillé avec les éléments suivants:
Genre: {game_genre}
Ambiance: {visual_atmosphere}
Thèmes: {thematic_keywords}
Références: {cultural_references}

Réponds en suivant strictement ce format:

UNIVERS:
[Description détaillée de l'univers du jeu]

ACTE 1:
[Description du premier acte]

ACTE 2:
[Description du deuxième acte avec un retournement de situation]

ACTE 3:
[Description du troisième acte et conclusion]

PERSONNAGE 1:
Nom: [nom]
Classe: [type/classe du personnage]
Rôle: [rôle dans l'histoire]
Background: [histoire du personnage]
Gameplay: [style de jeu unique]

PERSONNAGE 2:
[Même format que personnage 1]

PERSONNAGE 3:
[Même format que personnage 1]

LIEU 1:
Nom: [nom du lieu]
Description: [description atmosphérique]
Importance: [rôle dans l'histoire]

LIEU 2:
[Même format que lieu 1]

LIEU 3:
[Même format que lieu 1]

Assure-toi de suivre exactement ce format et de fournir des réponses détaillées pour chaque section.[/INST]"""

        # Appel à l'API 
        api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
        headers = {
            "Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_TOKEN')}"
        }
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 2000,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True
            }
        }
        
        try:
            max_retries = 3
            retry_delay = 2  # secondes
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(api_url, headers=headers, json=payload)
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(retry_delay)
            
            ai_response = response.json()
            
            # Extraction du texte généré
            generated_text = ai_response[0]['generated_text']
            
            # Parse la réponse
            parsed_response = self.parse_ai_response(generated_text)
            
            # Génération de l'image avec Stable Diffusion
            image_prompt = f"A video game scene featuring {game_genre} style, with {visual_atmosphere} atmosphere, including elements of {thematic_keywords}"
            image_api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"
            image_headers = {
                "Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_TOKEN')}"
            }
            
            try:
                # Appel à l'API Stable Diffusion avec retry
                max_retries = 5  # Augmentation du nombre de tentatives
                retry_delay = 5  # Augmentation du délai entre les tentatives
                
                for attempt in range(max_retries):
                    try:
                        image_response = requests.post(
                            image_api_url,
                            headers=image_headers,
                            json={"inputs": image_prompt}
                        )
                        
                        if image_response.status_code == 200:
                            # Créer le dossier media/concept s'il n'existe pas
                            os.makedirs('media/concept', exist_ok=True)
                            
                            # Générer un nom de fichier unique
                            image_filename = f"game_{int(time.time())}.png"
                            image_path = f"concept/{image_filename}"
                            
                            # Sauvegarder l'image
                            with open(f"media/{image_path}", "wb") as f:
                                f.write(image_response.content)
                            break
                        elif image_response.status_code == 503:
                            if attempt < max_retries - 1:
                                print(f"Service indisponible, nouvelle tentative dans {retry_delay} secondes...")
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Augmentation progressive du délai
                                continue
                            else:
                                image_path = None
                                print(f"Erreur génération image après {max_retries} tentatives: {image_response.status_code}, {image_response.text}")
                        else:
                            image_path = None
                            print(f"Erreur génération image: {image_response.status_code}, {image_response.text}")
                            break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        image_path = None
                        print(f"Erreur génération image: {str(e)}")
                        break
            except Exception as e:
                image_path = None
                print(f"Erreur génération image: {str(e)}")

            # Création du concept de jeu avec l'image
            game_data = {
                'game_genre': game_genre,
                'visual_atmosphere': visual_atmosphere,
                'thematic_keywords': thematic_keywords,
                'cultural_references': cultural_references,
                'language': language,
                'universe_description': parsed_response["universe_description"],
                'story_act_1': parsed_response["story_acts"][0],
                'story_act_2': parsed_response["story_acts"][1],
                'story_act_3': parsed_response["story_acts"][2],
                'user': request.user,
                'image': image_path
            }
            
            game_concept = GameConcept.objects.create(**game_data)
            
            # Création des personnages
            for character_text in parsed_response["characters"]:
                self.create_character_from_text(character_text, game_concept)
            
            # Création des lieux
            for location_text in parsed_response["locations"]:
                self.create_location_from_text(location_text, game_concept)
            
            return Response(GameConceptSerializer(game_concept).data, status=status.HTTP_201_CREATED)
            
        except requests.exceptions.RequestException as e:
            return Response(
                {"error": f"Erreur lors de l'appel à l'API Hugging Face: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {"error": f"Erreur lors du traitement: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Vues Frontend
@login_required
def home(request):
    """Vue de la page d'accueil"""
    # Récupérer tous les jeux de la base de données avec les informations de l'utilisateur
    games_list = GameConcept.objects.select_related('user').all().order_by('-created_at')
    
    # Créer un paginator avec 1 jeu par page
    paginator = Paginator(games_list, 1)
    page = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Pour chaque jeu, on ajoute le pseudo du créateur
    for game in page_obj:
        game.creator_username = game.user.username
    
    context = {
        'page_obj': page_obj,
        'total_games': games_list.count(),
        'current_page': page,
        'total_pages': paginator.num_pages,
    }
    
    return render(request, 'home.html', context)

@login_required
def generate_game_view(request):
    """Vue pour générer un nouveau jeu"""
    if request.method == 'POST':
        try:
            # Récupération des données du formulaire
            game_genre = request.POST.get('game_genre')
            visual_atmosphere = request.POST.get('visual_atmosphere')
            thematic_keywords = request.POST.get('thematic_keywords')
            cultural_references = request.POST.get('cultural_references', '')
            language = request.POST.get('language', 'fr')

            # Récupération du cookie de session et du token CSRF
            session_cookie = request.COOKIES.get('sessionid')
            csrf_token = request.COOKIES.get('csrftoken')

            # Appel à l'API pour générer le jeu
            response = requests.post(
                'http://127.0.0.1:8000/api/games/generate_game/',
                json={
                    'game_genre': game_genre,
                    'visual_atmosphere': visual_atmosphere,
                    'thematic_keywords': thematic_keywords,
                    'cultural_references': cultural_references,
                    'language': language,
                    'user': request.user.id
                },
                headers={
                    'X-CSRFToken': csrf_token,
                    'Cookie': f'sessionid={session_cookie}; csrftoken={csrf_token}',
                    'Referer': 'http://127.0.0.1:8000'
                }
            )
            
            if response.status_code == 201:
                game_data = response.json()
                return render(request, 'success.html', {
                    'game_id': game_data['id'],
                    'game_genre': game_data['game_genre']
                })
            else:
                return render(request, 'generate_game.html', {
                    'error': f'Une erreur est survenue lors de la génération du jeu. Status: {response.status_code}, Message: {response.text}'
                })
                
        except Exception as e:
            return render(request, 'generate_game.html', {
                'error': str(e)
            })
            
    return render(request, 'generate_game.html')

@login_required
def game_detail(request, game_id):
    """Vue détaillée d'un jeu"""
    # Récupérer le jeu sans filtrer par utilisateur
    game = get_object_or_404(GameConcept, id=game_id)
    # Ajouter le nom du créateur au contexte
    creator_username = game.user.username
    return render(request, 'game_detail.html', {
        'game': game,
        'creator_username': creator_username
    })

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
    
@login_required
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