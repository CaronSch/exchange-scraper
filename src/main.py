import yaml
import logging
from pathlib import Path

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
            
        with open(self.config_path) as f:
            return yaml.safe_load(f)

def main():
    """Main entry point for the application."""
    try:
        config = Config()
        logging.basicConfig(
            level=config.config["logging"]["level"],
            filename=config.config["logging"]["file"],
            format=config.config["logging"]["format"],
            datefmt=config.config["logging"]["datefmt"]
        )
        logging.info("Application started")

        logging.info("Application finished")
        
    except Exception as e:
        logging.error(f"Error starting application: {e}")
        raise

if __name__ == "__main__":
    main()