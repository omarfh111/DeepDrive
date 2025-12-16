# reviews/models.py
from django.db import models
from django.conf import settings                        # ✅ use the swapped user model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from django.db.models import Avg, Count, Q


class Review(models.Model):
    user = models.ForeignKey(                           # ✅ point to AUTH_USER_MODEL
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Utilisateur"
    )
    titre = models.CharField(max_length=200, verbose_name="Titre")
    note = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        verbose_name="Note",
        help_text="Note entre 0 et 5"
    )
    description = models.TextField(verbose_name="Description")
    image = models.ImageField(upload_to='reviews/%Y/%m/%d/', verbose_name="Image")
    date_review = models.DateField(auto_now_add=True, verbose_name="DateReview")
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="date_joined")
    is_approved = models.BooleanField(default=True, verbose_name="Approuvé")

    class Meta:
        ordering = ['-date_joined']
        verbose_name = "Avis"
        verbose_name_plural = "Avis"

    def __str__(self):
        # your custom user has no username field → show email or full name
        display = self.user.email or f"{self.user.first_name} {self.user.last_name}".strip()
        return f"{self.titre} - {display} ({self.note}⭐)"

    def get_absolute_url(self):
        return reverse('reviews:detail', kwargs={'pk': self.pk})

    @property
    def star_rating(self):
        full = int(self.note)
        half = 1 if (self.note - full) >= 0.5 else 0
        empty = 5 - full - half
        return {'full': full, 'half': half, 'empty': empty}

    @property
    def id_Review(self):
        return self.id
    def get_sentiment_score(self):
        """
        Calculate average sentiment score from approved comments
        Returns: float between -1 (negative) and 1 (positive), or None if no comments
        """
        approved_comments = self.commentaires.filter(is_approved=True)
        
        if not approved_comments.exists():
            return None
        
        # Map sentiment labels to scores
        sentiment_map = {
            'Positive': 1,
            'Neutral': 0,
            'Negative': -1
        }
        
        scores = []
        for comment in approved_comments:
            if comment.sentiment_label in sentiment_map:
                # Weight by confidence
                weighted_score = sentiment_map[comment.sentiment_label] * comment.sentiment_confidence
                scores.append(weighted_score)
        
        if not scores:
            return None
        
        return sum(scores) / len(scores)   
    
    def get_sentiment_stats(self):
        """
        Returns counts of positive, neutral, and negative comments
        """
        approved_comments = self.commentaires.filter(is_approved=True)
        
        return {
            'positive': approved_comments.filter(sentiment_label='Positive').count(),
            'neutral': approved_comments.filter(sentiment_label='Neutral').count(),
            'negative': approved_comments.filter(sentiment_label='Negative').count(),
            'total': approved_comments.count()
        }
    @property
    def sentiment_percentage(self):
        """
        Returns positive sentiment percentage for display
        """
        stats = self.get_sentiment_stats()
        if stats['total'] == 0:
            return None
        return round((stats['positive'] / stats['total']) * 100, 1)


class Commentaire(models.Model):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='commentaires',
        verbose_name="Avis"
    )
    user = models.ForeignKey(                           # ✅ point to AUTH_USER_MODEL
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='commentaires',
        verbose_name="Utilisateur"
    )
    commentaire = models.TextField(verbose_name="Commentaire")
    date_commentaire = models.DateTimeField(auto_now_add=True, verbose_name="DateCommentaire")
    is_approved = models.BooleanField(default=True, verbose_name="Approuvé")

    sentiment_label = models.CharField(
        max_length=20,
        choices=[
            ('Positive', 'Positive'),
            ('Neutral', 'Neutral'),
            ('Negative', 'Negative'),
        ],
        null=True,
        blank=True,
        verbose_name="Sentiment"
    )
    sentiment_confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Sentiment Confidence",
        help_text="Confidence score from 0 to 1"
    )
    sentiment_analyzed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Sentiment Analyzed At"
    )

    class Meta:
        ordering = ['date_commentaire']
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"

    def __str__(self):
        display = self.user.email or f"{self.user.first_name} {self.user.last_name}".strip()
        return f"Commentaire de {display} sur {self.review.titre}"

    def get_absolute_url(self):
        return self.review.get_absolute_url()

    @property
    def id_Commentaire(self):
        return self.id
    def analyze_sentiment(self):
        """
        Analyze the sentiment of this comment using the Twitter-RoBERTa model
        """
        from .utils import analyze_comment_sentiment
        from django.utils import timezone
        
        result = analyze_comment_sentiment(self.commentaire)
        
        self.sentiment_label = result['sentiment']
        self.sentiment_confidence = result['confidence']
        self.sentiment_analyzed_at = timezone.now()
        self.save(update_fields=['sentiment_label', 'sentiment_confidence', 'sentiment_analyzed_at'])
        
        return result
