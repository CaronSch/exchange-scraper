import pytest
from pathlib import Path
from src.main import Config

def test_config_loading(tmp_path):
    # Create a temporary config file
    config_content = """
    app:
      name: "Test App"
      version: "1.0.0"
    logging:
      level: "INFO"
      file: "test.log"
    """
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text(config_content)
    
    # Test config loading
    config = Config(str(config_path))
    assert config.config["app"]["name"] == "Test App"
    assert config.config["app"]["version"] == "1.0.0"

def test_missing_config():
    with pytest.raises(FileNotFoundError):
        Config("nonexistent_config.yaml")