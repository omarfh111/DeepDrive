

import re
from typing import Tuple, Set, List
import os


class ContentValidator:
    def __init__(self, bad_words_file: str = None):
        """
        Initialize validator with optional bad words file.
        
        Args:
            bad_words_file: Path to text file with one bad word per line
        """
        self.bad_words = self._load_bad_words(bad_words_file)
        self.ai_patterns = self._compile_ai_patterns()
    
    def _load_bad_words(self, filepath: str = None) -> Set[str]:
        """Load bad words from file, or use defaults if file not provided."""
        default_words = {
            'fuck', 'shit', 'bitch', 'asshole', 'cunt', 'whore',
            'damn', 'hell', 'piss', 'bastard', 'slut', 'dick'
        }
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    words = {line.strip().lower() for line in f if line.strip()}
                return words if words else default_words
            except FileNotFoundError:
                print(f"Warning: {filepath} not found. Using default word list.")
                return default_words
        
        return default_words
    
    def _compile_ai_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns that detect AI-generated content."""
        patterns = [
            # Common AI phrases
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
            
            # Generic AI hedging patterns
            r'\bit\'s worth noting that\b',
            r'\bit\'s important to (note|remember|consider) that\b',
            r'\bhowever, it\'s (worth|important)\b',
            r'\bin conclusion,?\s+(it\'s clear|we can see)\b',
            
            # Numbered lists that are too structured (common in AI)
            r'^\s*\d+\.\s+.+\n\s*\d+\.\s+.+\n\s*\d+\.',
            
            # Overly formal academic tone
            r'\bfurthermore\b.*\bmoreover\b',
            r'\bnevertheless\b.*\bnotwithstanding\b',
        ]
        
        return [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns]
    
    def contains_bad_words(self, text: str) -> Tuple[bool, List[str]]:
        """Check for profanity and return found words."""
        text_lower = text.lower()
        found_words = []
        
        for word in self.bad_words:
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, text_lower):
                found_words.append(word)
        
        return len(found_words) > 0, found_words
    
    def detect_ai_content(self, text: str) -> Tuple[bool, List[str]]:
        """Detect if content appears to be AI-generated."""
        detected_patterns = []
        
        for pattern in self.ai_patterns:
            if pattern.search(text):
                detected_patterns.append(pattern.pattern)
        
        # Additional heuristic: too many formal transitions
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
        
        # Character repetition (6+ characters)
        if re.search(r'(.)\1{5,}', text):
            return True
        
        # Repeated sequences (3+ times)
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
        
        # Too many vowel-less words (more lenient - only words longer than 3 chars)
        vowel_less = sum(1 for w in words if len(w) > 3 and not re.search(r'[aeiou]', w.lower()))
        vowel_less_ratio = vowel_less / len(words) if words else 0
        # Only flag if there are at least 5 vowel-less words AND ratio is high
        if vowel_less >= 5 and vowel_less_ratio > 0.5:
            return True
        
        # Words with too many consonants (more lenient - 7+ consonants in words 8+ chars)
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
        
        # URLs (excessive linking)
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
        
        # 1. Check for profanity
        has_profanity, found_words = self.contains_bad_words(text)
        if has_profanity:
            return False, "Please remove inappropriate language from your review."
        
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
        
        # Must have enough words
        if len(words) < 5:
            return False, "Review is too short. Please write at least a few words."
        
        # Check for sentence structure
        if not re.search(r"[a-zA-Z]{3,}\s+[a-zA-Z]{3,}", text):
            return False, "Your review must contain readable sentences."
        
        # Too many short words
        short_words = sum(1 for w in words if len(w) <= 2)
        if short_words > len(words) * 0.6:
            return False, "Review does not contain meaningful content."
        
        return True, ""


# Singleton instance for use in Django forms
_validator_instance = None

def get_validator(bad_words_file: str = None) -> ContentValidator:
    """Get or create singleton validator instance."""
    global _validator_instance
    if _validator_instance is None:
        # Look for bad_words.txt in the same directory as this file
        if bad_words_file is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            default_path = os.path.join(current_dir, 'bad_words.txt')
            if os.path.exists(default_path):
                bad_words_file = default_path
        
        _validator_instance = ContentValidator(bad_words_file)
    return _validator_instance


def validate_content(text: str, is_title: bool = False) -> Tuple[bool, str]:
    """
    Convenience function for Django form validation.
    
    Args:
        text: Text to validate
        is_title: Whether this is a title (less strict) or full content
    
    Returns:
        (is_valid, error_message)
    """
    validator = get_validator()
    return validator.validate_content(text, is_title)