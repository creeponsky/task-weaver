from dataclasses import dataclass
from typing import Optional

@dataclass
class LibraryConfig:
    """Configuration class for workflow_manager"""
    
    debug: bool = False
    api_base_url: str = "https://api.example.com"
    api_timeout: int = 30
    
    @classmethod
    def create_default(cls) -> "LibraryConfig":
        """Create a default configuration instance"""
        return cls()

# Global config instance
config = LibraryConfig.create_default()
