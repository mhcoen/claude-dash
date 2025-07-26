"""
Base provider adapter for LLM Cost Monitor
Defines the interface that all provider implementations must follow
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp
import logging

logger = logging.getLogger(__name__)


@dataclass
class UsageData:
    """Standardized usage data structure"""
    timestamp: datetime
    total_cost: float
    total_tokens: Optional[int] = None
    model_breakdown: Optional[Dict[str, Dict]] = None  # model -> {cost, tokens}
    api_key_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    

@dataclass
class ProviderConfig:
    """Provider configuration"""
    name: str
    display_name: str
    api_keys: List[str]
    poll_interval: int = 60  # seconds
    enabled: bool = True
    

class ProviderAdapter(ABC):
    """Abstract base class for provider adapters"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_poll_time: Optional[datetime] = None
        self._last_data: Optional[UsageData] = None
        
    async def initialize(self):
        """Initialize the provider adapter"""
        self.session = aiohttp.ClientSession()
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            
    @abstractmethod
    async def fetch_usage(self) -> UsageData:
        """
        Fetch current usage data from the provider
        Must be implemented by each provider
        """
        pass
        
    @abstractmethod
    async def validate_api_key(self, api_key: str) -> bool:
        """
        Validate if an API key is valid
        Must be implemented by each provider
        """
        pass
        
    @abstractmethod
    def get_headers(self, api_key: str) -> Dict[str, str]:
        """
        Get authorization headers for API requests
        Must be implemented by each provider
        """
        pass
        
    async def poll(self) -> Optional[UsageData]:
        """Poll the provider for usage data"""
        try:
            if not self.config.enabled or not self.config.api_keys:
                return None
                
            data = await self.fetch_usage()
            self._last_poll_time = datetime.utcnow()
            self._last_data = data
            return data
            
        except Exception as e:
            logger.error(f"Error polling {self.config.name}: {e}")
            return None
            
    def get_last_data(self) -> Optional[UsageData]:
        """Get the last fetched data"""
        return self._last_data
        
    def get_last_poll_time(self) -> Optional[datetime]:
        """Get the last poll timestamp"""
        return self._last_poll_time
        
    async def make_request(self, url: str, api_key: str, 
                          method: str = "GET", **kwargs) -> Dict:
        """Make an authenticated request to the provider API"""
        if not self.session:
            await self.initialize()
            
        headers = self.get_headers(api_key)
        headers.update(kwargs.get("headers", {}))
        
        async with self.session.request(
            method, url, headers=headers, **kwargs
        ) as response:
            response.raise_for_status()
            return await response.json()
            
    def calculate_cost_delta(self, new_data: UsageData) -> float:
        """Calculate cost change since last poll"""
        if not self._last_data:
            return 0.0
        return new_data.total_cost - self._last_data.total_cost