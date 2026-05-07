from abc import ABC, abstractmethod
from typing import Any, Dict
import json
import os
from datetime import datetime

class BaseSkill(ABC):
    """
    Abstract Base Class for all Agent Skills.
    Enforces standardized execution and data persistence.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    @abstractmethod
    async def execute(self, target: str, **kwargs) -> Dict[str, Any]:
        """Core execution logic to be implemented by skills."""
        pass
    
    def save_data(self, data: Any, subfolder: str = "raw", prefix: str = ""):
        """Persists data to the local filesystem."""
        filename = f"{prefix}{self.name}_{self.run_id}.json"
        
        # Resolve absolute path relative to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        directory = os.path.join(base_dir, "data", subfolder)
        
        os.makedirs(directory, exist_ok=True)
        filepath = os.path.join(directory, filename)
        
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=4, default=str)
            print(f"--- [Skill: {self.name}] Data saved to: {filepath} ---")
        except Exception as e:
            print(f"!!! [Skill: {self.name}] Failed to save data: {e} !!!")
        
        return filepath
