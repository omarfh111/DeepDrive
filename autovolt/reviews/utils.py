"""
LLM-powered sentiment analyzer using OpenAI API.
Supports sentiment analysis in ANY language with better accuracy than pre-trained models.
Works with car reviews in English, French, Arabic, Tunisian dialect, and all other languages.
"""

import logging
from functools import lru_cache
from typing import Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai library not available. LLM sentiment analysis will be disabled.")


@lru_cache(maxsize=1)
def get_openai_client():
    """Initialize OpenAI client once and cache it."""
    if not OPENAI_AVAILABLE:
        return None
    
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        logger.warning("OPENAI_API_KEY not configured. Sentiment analysis will use fallback.")
        return None
    
    try:
        client = OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized for sentiment analysis")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return None


def analyze_comment_sentiment(text: str) -> Dict[str, any]:
    """
    Analyze the sentiment of a comment using OpenAI LLM.
    
    Supports ALL languages including:
    - English, French, Spanish, German, etc.
    - Arabic (all dialects: Tunisian, Egyptian, Moroccan, etc.)
    - Transliterated Arabic (Arabizi/Franco-Arabic)
    - Mixed languages
    
    Args:
        text (str): The comment/review text to analyze (any language)
        
    Returns:
        dict: {
            'sentiment': str,  # 'Positive', 'Negative', or 'Neutral'
            'confidence': float,  # 0.0 to 1.0
            'explanation': str  # Brief reason for the sentiment
        }
    """
    client = get_openai_client()
    
    # Fallback if OpenAI not available
    if client is None:
        logger.warning("OpenAI client not available, using fallback sentiment")
        return _fallback_sentiment_analysis(text)
    
    try:
        # Truncate if too long
        max_length = 4000
        if len(text) > max_length:
            text = text[:max_length]
        
        # Call OpenAI with optimized prompt
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cost-effective
            messages=[
                {
                    "role": "system",
                    "content": """You are a sentiment analysis expert for car reviews. Analyze the sentiment of text in ANY language.

Your task:
- Determine if the review is Positive, Negative, or Neutral
- Provide a confidence score (0.0 to 1.0)
- Give a brief explanation

Guidelines:
- Positive: User is happy, satisfied, recommends the car
- Negative: User is unhappy, dissatisfied, has complaints
- Neutral: Mixed feelings, factual statements, or unclear sentiment
- Consider cultural expressions and dialects (e.g., Tunisian "barcha behi" = very good)
- Understand sarcasm and context
- Handle mixed languages naturally

Respond with JSON only:
{
    "sentiment": "Positive|Negative|Neutral",
    "confidence": 0.0-1.0,
    "explanation": "brief reason in English"
}"""
                },
                {
                    "role": "user",
                    "content": f"Analyze the sentiment of this car review:\n\n{text}"
                }
            ],
            temperature=0.3,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        import json
        result = json.loads(response.choices[0].message.content.strip())
        
        sentiment = result.get("sentiment", "Neutral")
        confidence = result.get("confidence", 0.5)
        explanation = result.get("explanation", "Unable to determine sentiment")
        
        # Validate sentiment value
        if sentiment not in ["Positive", "Negative", "Neutral"]:
            sentiment = "Neutral"
        
        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, float(confidence)))
        
        logger.info(f"Sentiment analyzed: {sentiment} ({confidence:.2f}) - {text[:50]}...")
        
        return {
            'sentiment': sentiment,
            'confidence': round(confidence, 4),
            'explanation': explanation
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse sentiment JSON: {e}")
        return _fallback_sentiment_analysis(text)
    except Exception as e:
        logger.error(f"Error analyzing sentiment with OpenAI: {e}")
        return _fallback_sentiment_analysis(text)


def _fallback_sentiment_analysis(text: str) -> Dict[str, any]:
    """
    Simple fallback sentiment analysis using keyword matching.
    Used when OpenAI API is not available.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        dict: Sentiment result with lower confidence
    """
    text_lower = text.lower()
    
    # Positive keywords (multiple languages)
    positive_keywords = [
        'good', 'great', 'excellent', 'amazing', 'love', 'best', 'perfect', 'wonderful',
        'bon', 'bien', 'excellent', 'super', 'génial', 'parfait',  # French
        'behi', 'barcha behi', 'metfasel', 'rabi yebarek',  # Tunisian
        'جيد', 'ممتاز', 'رائع', 'جميل'  # Arabic
    ]
    
    # Negative keywords (multiple languages)
    negative_keywords = [
        'bad', 'terrible', 'awful', 'worst', 'hate', 'horrible', 'poor', 'disappointed',
        'mauvais', 'terrible', 'nul', 'horrible',  # French
        'khayeb', 'wase5', 'moch behi', '5ayba',  # Tunisian
        'سيء', 'فظيع', 'سيئ', 'مش حلو'  # Arabic
    ]
    
    positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
    negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
    
    if positive_count > negative_count and positive_count > 0:
        return {
            'sentiment': 'Positive',
            'confidence': 0.6,
            'explanation': 'Fallback analysis detected positive keywords'
        }
    elif negative_count > positive_count and negative_count > 0:
        return {
            'sentiment': 'Negative',
            'confidence': 0.6,
            'explanation': 'Fallback analysis detected negative keywords'
        }
    else:
        return {
            'sentiment': 'Neutral',
            'confidence': 0.5,
            'explanation': 'Fallback analysis - unable to determine clear sentiment'
        }


def analyze_review_sentiment_detailed(text: str) -> Dict[str, any]:
    """
    Enhanced sentiment analysis with additional insights for car reviews.
    
    Args:
        text (str): The review text to analyze
        
    Returns:
        dict: {
            'sentiment': str,
            'confidence': float,
            'explanation': str,
            'aspects': dict  # Sentiment about specific aspects (performance, comfort, etc.)
        }
    """
    client = get_openai_client()
    
    if client is None:
        basic_result = analyze_comment_sentiment(text)
        basic_result['aspects'] = {}
        return basic_result
    
    try:
        max_length = 4000
        if len(text) > max_length:
            text = text[:max_length]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a car review sentiment analyzer. Analyze both overall sentiment and specific aspects.

Analyze sentiment for these aspects:
- Performance (engine, speed, handling)
- Comfort (seats, ride quality, space)
- Design (appearance, interior, style)
- Value (price, features, worth)
- Reliability (quality, durability, issues)

Respond with JSON only:
{
    "sentiment": "Positive|Negative|Neutral",
    "confidence": 0.0-1.0,
    "explanation": "brief reason",
    "aspects": {
        "performance": "Positive|Negative|Neutral|Not Mentioned",
        "comfort": "Positive|Negative|Neutral|Not Mentioned",
        "design": "Positive|Negative|Neutral|Not Mentioned",
        "value": "Positive|Negative|Neutral|Not Mentioned",
        "reliability": "Positive|Negative|Neutral|Not Mentioned"
    }
}"""
                },
                {
                    "role": "user",
                    "content": f"Analyze this car review:\n\n{text}"
                }
            ],
            temperature=0.3,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(response.choices[0].message.content.strip())
        
        # Validate and clean result
        sentiment = result.get("sentiment", "Neutral")
        if sentiment not in ["Positive", "Negative", "Neutral"]:
            sentiment = "Neutral"
        
        confidence = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
        
        return {
            'sentiment': sentiment,
            'confidence': round(confidence, 4),
            'explanation': result.get("explanation", ""),
            'aspects': result.get("aspects", {})
        }
        
    except Exception as e:
        logger.error(f"Error in detailed sentiment analysis: {e}")
        basic_result = analyze_comment_sentiment(text)
        basic_result['aspects'] = {}
        return basic_result


# Convenience function for quick sentiment check
def is_positive_review(text: str, threshold: float = 0.6) -> bool:
    """
    Quick check if a review is positive.
    
    Args:
        text (str): Review text
        threshold (float): Confidence threshold (default 0.6)
        
    Returns:
        bool: True if review is positive with confidence above threshold
    """
    result = analyze_comment_sentiment(text)
    return result['sentiment'] == 'Positive' and result['confidence'] >= threshold


def is_negative_review(text: str, threshold: float = 0.6) -> bool:
    """
    Quick check if a review is negative.
    
    Args:
        text (str): Review text
        threshold (float): Confidence threshold (default 0.6)
        
    Returns:
        bool: True if review is negative with confidence above threshold
    """
    result = analyze_comment_sentiment(text)
    return result['sentiment'] == 'Negative' and result['confidence'] >= threshold