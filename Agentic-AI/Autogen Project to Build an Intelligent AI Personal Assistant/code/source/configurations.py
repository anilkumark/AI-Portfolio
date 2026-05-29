"""
Configuration settings for Personal Assistant API.
"""
import os

# Load environment variables from .env file


class Config:
    """Configuration class for the Personal Assistant API."""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = 'enter-api-key'
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TEMPERATURE: float = 1

    # TAVILY
    TAVILY_SEARCH_KEY: str = "enter tavily-key"
    MAX_RESULTS : int = 5
    
    # Slack Configuration
    SLACK_BOT_TOKEN: str = "xo-bot-token"
    SLACK_SIGNING_SECRET: str = "signing-secret"
    
    # Google API Configuration
    GOOGLE_CREDENTIALS_FILE: str = "credentials.json"
    GOOGLE_TOKEN_FILE: str = "token.json"
    GOOGLE_SCOPES: list = [
    'https://www.googleapis.com/auth/calendar',
    'https://mail.google.com/']


    # Timezone Configuration
    DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")
    
    # Weather API Configuration
    OPEN_METEO_URL: str = "https://api.open-meteo.com/v1/forecast"
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org/search"
    
    


# Initialize and validate configuration
config = Config()
