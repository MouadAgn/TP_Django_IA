from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import GameConcept, Character, Location
from rest_framework import serializers
import requests
import json
import os
from dotenv import load_dotenv
import time

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

    class Meta:
        model = GameConcept
        fields = '__all__'

class GameGeneratorViewSet(viewsets.ModelViewSet):
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
        # Récupération des données du formulaire
        game_genre = request.data.get('game_genre')
        visual_atmosphere = request.data.get('visual_atmosphere')
        thematic_keywords = request.data.get('thematic_keywords')
        cultural_references = request.data.get('cultural_references', '')

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
            
            # Création du concept de jeu
            game_concept = GameConcept.objects.create(
                game_genre=game_genre,
                visual_atmosphere=visual_atmosphere,
                thematic_keywords=thematic_keywords,
                cultural_references=cultural_references,
                universe_description=parsed_response["universe_description"],
                story_act_1=parsed_response["story_acts"][0],
                story_act_2=parsed_response["story_acts"][1],
                story_act_3=parsed_response["story_acts"][2]
            )
            
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
