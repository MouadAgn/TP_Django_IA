from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class GameConcept(models.Model):
    # Champs de base pour le formulaire
    game_genre = models.CharField(max_length=100)
    visual_atmosphere = models.CharField(max_length=100)
    thematic_keywords = models.CharField(max_length=200)
    cultural_references = models.CharField(max_length=200, blank=True, null=True)
    language = models.CharField(max_length=50, default='fr', choices=[
        ('fr', 'Français'),
        ('en', 'English'),
        ('es', 'Español'),
        ('de', 'Deutsch')
    ])
    
    # Champs générés par l'IA
    universe_description = models.TextField()
    image = models.CharField(max_length=255, blank=True, null=True)
    story_act_1 = models.TextField()
    story_act_2 = models.TextField()
    story_act_3 = models.TextField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_concepts')

    def __str__(self):
        return f"{self.game_genre} - {self.visual_atmosphere}"

class Character(models.Model):
    game = models.ForeignKey(GameConcept, related_name='characters', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    character_class = models.CharField(max_length=100)
    narrative_role = models.CharField(max_length=200)
    background = models.TextField()
    gameplay_description = models.TextField()
    # prompt = models.TextField()
    image = models.ImageField(upload_to='characters/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.character_class}"

class Location(models.Model):
    game = models.ForeignKey(GameConcept, related_name='locations', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    significance = models.TextField()

    def __str__(self):
        return self.name

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(GameConcept, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'game')  # Empêche les doublons de favoris
