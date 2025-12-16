"""
Enhanced content validator with improved AI-powered toxicity detection.
Uses OpenAI API with a more flexible, uncapped approach to content moderation.
"""

import re
from typing import Tuple, List, Optional
import logging
from functools import lru_cache
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai library not available. AI-powered toxicity detection will be disabled.")


@lru_cache(maxsize=1)
def get_openai_client():
    """Initialize OpenAI client once and cache it."""
    if not OPENAI_AVAILABLE:
        return None
    
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        logger.warning("OPENAI_API_KEY not configured in settings. Toxicity detection will be disabled.")
        return None
    
    try:
        client = OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return None


class ContentValidator:
    def __init__(self, toxicity_threshold: float = 0.75):
        """
        Initialize validator with AI-powered toxicity detection using OpenAI.
        
        Args:
            toxicity_threshold: Threshold (0.0-1.0) for considering content toxic.
                               Default 0.75 means 75% confidence required.
                               Balanced to catch profanity while avoiding false positives on opinions.
        """
        self.toxicity_threshold = toxicity_threshold
        self.ai_patterns = self._compile_ai_patterns()
        self._openai_client = None
    
    def _compile_ai_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns that detect AI-generated content."""
        patterns = [
            r'\bas an ai\b',
            r'\bi am an ai\b',
            r'\bi\'m an ai\b',
            r'\bas a language model\b',
            r'\bas an ai language model\b',
            r'\bi don\'t have personal (opinions|experiences|feelings)\b',
            r'\bi cannot (feel|experience|have opinions)\b',
            r'\bmy knowledge cutoff\b',
            r'\bmy training data\b',
            r'\bi was trained\b',
            r'\bi\'m just (an ai|a machine|a program)\b',
            r'\bi don\'t have the ability to\b',
            r'\bas an artificial intelligence\b',
        ]
        return [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns]
    
    def _get_openai_client(self):
        """Get the OpenAI client, loading it if needed."""
        if self._openai_client is None:
            self._openai_client = get_openai_client()
        return self._openai_client
    
    def detect_toxicity(self, text: str) -> Tuple[bool, Optional[dict]]:
        """
        Detect toxic content using OpenAI API with improved, context-aware approach.
        Only flags severely offensive content, not negative opinions.
        
        Args:
            text: Text to analyze (can be in any language)
            
        Returns:
            (is_toxic, toxicity_details)
        """
        client = self._get_openai_client()
        
        if client is None:
            logger.warning("OpenAI client not available, skipping toxicity check")
            return False, None
        
        try:
            # Truncate text if too long
            max_length = 4000
            if len(text) > max_length:
                text = text[:max_length]
            
            # IMPROVED: More nuanced prompt that distinguishes opinions from abuse
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a content moderator for a car review platform that handles reviews in ANY language worldwide, including Tunisian Arabic dialect, French, English, and others.

CRITICAL DISTINCTION:
- NEGATIVE OPINIONS about cars are ALLOWED and should NOT be flagged (e.g., "ugly", "bad", "terrible", "piece of junk", "waste of money")
- VULGAR/OFFENSIVE language and crude sexual references should ALWAYS be flagged, regardless of context

FLAG these violations:
1. Vulgar profanity and crude language (sexual organs, explicit terms, scatological terms)
2. Direct insults, slurs, or profanity attacking PEOPLE (racist, sexist, homophobic slurs)
3. Explicit sexual content or crude sexual references
4. Threats of violence or harm
5. Severe harassment targeting individuals or groups

IMPORTANT: Be especially vigilant with Arabic/Tunisian dialect profanity. These are NOT acceptable even as car opinions.

TUNISIAN ARABIC PROFANITY TO FLAG:
- "zeb" / "zebi" (vulgar sexual term) ✗ FLAG
- "kahba" (offensive slur) ✗ FLAG
- "nayek" (vulgar sexual term) ✗ FLAG
- "zokomk" (crude sexual reference) ✗ FLAG
- "yazebi" (vulgar expression) ✗ FLAG
- "kos" / "kous" (vulgar term) ✗ FLAG
- "sharmouta" (offensive slur) ✗ FLAG
- "khra" / "khara" / "kharya" (vulgar profanity) ✗ FLAG
- "nikek" / "nik" (vulgar sexual term) ✗ FLAG
- "3ayr" / "ayr" (vulgar term) ✗ FLAG
- "kasrou" (vulgar insult) ✗ FLAG
- Any crude sexual references in dialect ✗ FLAG
- Any vulgar profanity in Arabic/Tunisian dialect ✗ FLAG
- "miboun" (bad/ugly) ✗ FLAG
- "sorm / sormek" (vulgar sexual term) ✗ FLAG
- "shit" (vulgar profanity) ✗ FLAG


DO NOT FLAG (negative car opinions only):
- "mahich mzeyna" (not good) ✓ ALLOW
- "khayba" (bad) ✓ ALLOW
- "ma3jebtech" (didn't like it) ✓ ALLOW
- "this car is crap/garbage" ✓ ALLOW (opinion about car)
- "ugly piece of junk" ✓ ALLOW (car opinion)

EXAMPLES:
- "mahich mzeyna lkarhba" ✓ ALLOW (just saying car is not good)
- "karhba zebi" ✗ FLAG (contains vulgar term "zebi")
- "sa7bi karhab ki zeb" ✗ FLAG (contains vulgar comparison)
- "this car sucks" ✓ ALLOW (mild frustration)
- "bara nayek ya kahba" ✗ FLAG (vulgar sexual term + slur)

Flag ANY use of vulgar sexual terms or crude language, even if mixed with car opinions.

Respond with JSON:
{
    "is_toxic": true/false,
    "confidence": 0.0-1.0,
    "category": "personal_attack|hate_speech|threat|harassment|sexual_harassment|null",
    "reason": "brief explanation",
    "detected_issues": ["specific offensive phrase"]
}

If not toxic, set is_toxic to false and category to null."""
                    },
                    {
                        "role": "user",
                        "content": f"Moderate this car review:\n\n{text}"
                    }
                ],
                temperature=0.2,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            response_text = response.choices[0].message.content.strip()
            
            import json
            try:
                result = json.loads(response_text)
                is_toxic = result.get("is_toxic", False)
                confidence = result.get("confidence", 1.0 if is_toxic else 0.0)
                
                # Apply threshold - higher threshold to reduce false positives
                if is_toxic and confidence >= self.toxicity_threshold:
                    toxicity_details = {
                        'max_score': confidence,
                        'category': result.get("category", "inappropriate_content"),
                        'scores': {'toxicity': confidence},
                        'reason': result.get('reason', 'Detected inappropriate content'),
                        'detected_words': result.get('detected_issues', [])
                    }
                    return True, toxicity_details
                else:
                    return False, None
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI JSON response: {e}\nResponse: {response_text}")
                return False, None
            
        except Exception as e:
            logger.error(f"Error detecting toxicity with OpenAI: {e}")
            return False, None
    
    def detect_ai_content(self, text: str) -> Tuple[bool, List[str]]:
        """Detect if content appears to be AI-generated."""
        detected_patterns = []
        
        for pattern in self.ai_patterns:
            if pattern.search(text):
                detected_patterns.append(pattern.pattern)
        
        # Heuristic: too many formal transitions
        formal_words = len(re.findall(
            r'\b(furthermore|moreover|additionally|consequently|'
            r'nevertheless|nonetheless|notwithstanding)\b',
            text, re.IGNORECASE
        ))
        
        if formal_words >= 3:
            detected_patterns.append("Excessive formal transitions")
        
        return len(detected_patterns) > 0, detected_patterns
    
    def looks_like_gibberish(self, text: str) -> bool:
        """Detect meaningless text patterns."""
        words = re.findall(r"[a-zA-Z']+", text)
        if not words:
            return True
        
        # Character repetition
        if re.search(r'(.)\1{5,}', text):
            return True
        
        # Repeated sequences
        if re.search(r'(.{2,4})\1{3,}', text):
            return True
        
        # Keyboard mashing
        keyboard_patterns = [
            r'asdf', r'qwer', r'zxcv', r'jkl', r'asd', 
            r'sdf', r'dfg', r'fgh', r'ghj', r'hjk'
        ]
        for pattern in keyboard_patterns:
            if pattern in text.lower():
                return True
        
        # Too many vowel-less words
        vowel_less = sum(1 for w in words if len(w) > 3 and not re.search(r'[aeiou]', w.lower()))
        vowel_less_ratio = vowel_less / len(words) if words else 0
        if vowel_less >= 5 and vowel_less_ratio > 0.5:
            return True
        
        # Words with too many consonants
        noisy_words = sum(
            1 for w in words 
            if len(w) >= 8 and re.search(r'[^aeiou]{7,}', w.lower())
        )
        if noisy_words >= 2:
            return True
        
        return False
    
    def detect_spam(self, text: str) -> Tuple[bool, str]:
        """Detect common spam patterns."""
        text_lower = text.lower()
        
        # URLs
        url_count = len(re.findall(r'https?://|www\.', text_lower))
        if url_count >= 2:
            return True, "Too many URLs detected"
        
        # Email addresses
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            return True, "Email addresses not allowed"
        
        # Phone numbers
        if re.search(r'(\d{3}[-.]?\d{3}[-.]?\d{4}|\(\d{3}\)\s*\d{3}[-.]?\d{4})', text):
            return True, "Phone numbers not allowed"
        
        # All caps spam
        if len(text) > 20:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.7:
                return True, "Excessive capitalization"
        
        # Repeated punctuation
        if re.search(r'[!?]{4,}', text):
            return True, "Excessive punctuation"
        
        # Promotional keywords
        spam_keywords = [
            r'click here', r'buy now', r'limited time', r'act now',
            r'free money', r'earn \$\$\$', r'work from home',
            r'lose weight fast', r'miracle cure'
        ]
        for keyword in spam_keywords:
            if re.search(keyword, text_lower):
                return True, f"Spam keyword detected"
        
        return False, ""
    
    def validate_content(self, text: str, is_title: bool = False) -> Tuple[bool, str]:
        """
        Main validation method.
        
        Returns:
            (is_valid, error_message)
        """
        if not text or not text.strip():
            return False, "Please write a review."
        
        text = text.strip()
        
        # 1. Check for toxicity using OpenAI API
        is_toxic, toxicity_details = self.detect_toxicity(text)
        if is_toxic:
            category = toxicity_details.get('category', 'inappropriate content') if toxicity_details else 'inappropriate content'
            detected_words = toxicity_details.get('detected_words', []) if toxicity_details else []
            
            # Build error message
            if detected_words and len(detected_words) > 0:
                words_display = detected_words[:3]
                words_text = ', '.join([f'"{word}"' for word in words_display])
                if len(detected_words) > 3:
                    words_text += f' and {len(detected_words) - 3} more'
                return False, f"Your review contains inappropriate language. Please remove: {words_text}"
            else:
                reason = toxicity_details.get('reason', 'inappropriate content detected')
                return False, f"Your review contains inappropriate content: {reason}. Please revise."
        
        # 2. Check for AI-generated content
        is_ai, ai_patterns = self.detect_ai_content(text)
        if is_ai:
            return False, "Content appears to be AI-generated. Please write in your own words."
        
        # 3. Check for spam
        is_spam, spam_msg = self.detect_spam(text)
        if is_spam:
            return False, f"Spam detected: {spam_msg}"
        
        # 4. Check for gibberish
        if self.looks_like_gibberish(text):
            return False, "Your review contains gibberish or meaningless text."
        
        # Title-specific validation
        if is_title:
            if len(text) > 100:
                return False, "Title is too long (max 100 characters)."
            if len(text) < 3:
                return False, "Title is too short (min 3 characters)."
            return True, ""
        
        # Full review validation
        words = re.findall(r"[a-zA-Z']+", text)
        
        if len(words) < 5:
            return False, "Review is too short. Please write at least a few words."
        
        # Check for sentence structure (more lenient for non-English)
        if not re.search(r"[a-zA-Z]{3,}\s+[a-zA-Z]{3,}", text) and not re.search(r"[\u0600-\u06FF]{3,}\s+[\u0600-\u06FF]{3,}", text):
            if not re.search(r"[\u4e00-\u9fff]{2,}", text):
                return False, "Your review must contain readable sentences."
        
        # Too many short words
        short_words = sum(1 for w in words if len(w) <= 2)
        if short_words > len(words) * 0.6:
            return False, "Review does not contain meaningful content."
        
        return True, ""


_validator_instance = None

def get_validator(toxicity_threshold: float = 0.75) -> ContentValidator:
    """Get or create singleton validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ContentValidator(toxicity_threshold=toxicity_threshold)
    return _validator_instance


def validate_content(text: str, is_title: bool = False) -> Tuple[bool, str]:
    """Convenience function for Django form validation."""
    validator = get_validator()
    return validator.validate_content(text, is_title)