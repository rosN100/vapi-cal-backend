import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # Cal.com API Configuration
    cal_api_key: str = os.getenv("CAL_API_KEY", "")
    cal_base_url: str = os.getenv("CAL_BASE_URL", "https://api.cal.com/v2")
    cal_username: str = os.getenv("CAL_USERNAME", "")
    cal_event_type_slug: str = os.getenv("CAL_EVENT_TYPE_SLUG", "build3-demo")
    
    # Calendar Configuration
    default_time_range_days: int = int(os.getenv("DEFAULT_TIME_RANGE_DAYS", "7"))
    default_slot_duration_minutes: int = int(os.getenv("DEFAULT_SLOT_DURATION_MINUTES", "30"))
    
    # Server Configuration
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    def validate(self) -> bool:
        """Validate that required environment variables are set"""
        required_vars = [
            self.cal_api_key,
            self.cal_username,
            self.cal_event_type_slug
        ]
        return all(required_vars)

# Global settings instance
settings = Settings() 