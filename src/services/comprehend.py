"""Amazon Comprehend service for text moderation."""

import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any

from src.config import settings
from src.utils.errors import TextModerationError, CoffeeException


class ComprehendService:
    """Service for Amazon Comprehend text analysis."""
    
    def __init__(self) -> None:
        """Initialize Comprehend service."""
        self.client = boto3.client("comprehend", region_name=settings.aws_region)
    
    def is_text_appropriate(self, text: str) -> bool:
        """Check if text is appropriate using sentiment analysis and toxicity detection."""
        try:
            # First, use sentiment analysis
            sentiment_response = self.client.detect_sentiment(
                Text=text,
                LanguageCode="en"
            )
            
            sentiment = sentiment_response.get("Sentiment", "NEUTRAL")
            sentiment_scores = sentiment_response.get("SentimentScore", {})
            
            # Check for overwhelmingly negative sentiment
            negative_score = sentiment_scores.get("Negative", 0)
            
            # If very negative sentiment, consider inappropriate
            if sentiment == "NEGATIVE" and negative_score > 0.8:
                return False
            
            # Use PII detection to catch potential personal attacks
            pii_response = self.client.detect_pii_entities(
                Text=text,
                LanguageCode="en"
            )
            
            # Check for excessive personal information (potential doxxing)
            pii_entities = pii_response.get("Entities", [])
            sensitive_types = ["EMAIL", "PHONE", "SSN", "ADDRESS"]
            
            sensitive_count = sum(1 for entity in pii_entities 
                                if entity.get("Type") in sensitive_types)
            
            if sensitive_count > 2:  # Too much personal info
                return False
            
            # Additional check: Look for potential toxicity using key phrase detection
            keyphrases_response = self.client.detect_key_phrases(
                Text=text,
                LanguageCode="en"
            )
            
            keyphrases = keyphrases_response.get("KeyPhrases", [])
            
            # Simple toxic keyword detection
            toxic_indicators = [
                "hate", "stupid", "idiot", "ugly", "disgusting", 
                "worthless", "pathetic", "loser", "trash"
            ]
            
            for phrase in keyphrases:
                phrase_text = phrase.get("Text", "").lower()
                if any(toxic_word in phrase_text for toxic_word in toxic_indicators):
                    return False
            
            return True
            
        except ClientError as e:
            # If Comprehend fails, err on the side of caution
            raise CoffeeException(f"Text moderation failed: {e}")
    
    def get_text_analysis(self, text: str) -> Dict[str, Any]:
        """Get detailed text analysis for debugging purposes."""
        try:
            sentiment_response = self.client.detect_sentiment(
                Text=text,
                LanguageCode="en"
            )
            
            keyphrases_response = self.client.detect_key_phrases(
                Text=text,
                LanguageCode="en"
            )
            
            return {
                "sentiment": sentiment_response.get("Sentiment"),
                "sentiment_scores": sentiment_response.get("SentimentScore", {}),
                "key_phrases": [kp.get("Text") for kp in keyphrases_response.get("KeyPhrases", [])]
            }
            
        except ClientError as e:
            raise CoffeeException(f"Text analysis failed: {e}")
    
    def moderate_comment(self, comment: str) -> None:
        """Moderate a comment and raise exception if inappropriate."""
        if not self.is_text_appropriate(comment):
            raise TextModerationError()