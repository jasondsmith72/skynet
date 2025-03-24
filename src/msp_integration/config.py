"""
Configuration management for MSP integration module.

This module handles loading, validation, and access to configuration settings
for MSP platform integration.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union

import yaml

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Exception raised for configuration errors."""
    pass


class MSPConfiguration:
    """Configuration manager for MSP integration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file (YAML)
        """
        self.config_path = config_path or 'config.yaml'
        self.config = {}
        self._loaded = False
    
    def load(self, config_path: Optional[str] = None) -> bool:
        """Load configuration from file.
        
        Args:
            config_path: Optional path to configuration file
            
        Returns:
            bool: True if configuration was loaded successfully
            
        Raises:
            ConfigurationError: If configuration file is invalid
        """
        if config_path:
            self.config_path = config_path
            
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Configuration file not found: {self.config_path}")
                return False
                
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
                
            # Validate configuration
            self._validate()
            
            self._loaded = True
            logger.info(f"Configuration loaded from {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")
    
    def _validate(self):
        """Validate the loaded configuration.
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Check if configuration is a dictionary
        if not isinstance(self.config, dict):
            raise ConfigurationError("Configuration must be a dictionary")
            
        # Check for required sections
        required_sections = ['platforms']
        for section in required_sections:
            if section not in self.config:
                raise ConfigurationError(f"Missing required section: {section}")
                
        # Validate platform configurations
        platforms = self.config.get('platforms', {})
        if not isinstance(platforms, dict):
            raise ConfigurationError("'platforms' section must be a dictionary")
            
        # Validate each platform configuration
        for platform, settings in platforms.items():
            self._validate_platform(platform, settings)
    
    def _validate_platform(self, platform: str, settings: Dict[str, Any]):
        """Validate configuration for a specific platform.
        
        Args:
            platform: Platform name
            settings: Platform settings
            
        Raises:
            ConfigurationError: If platform configuration is invalid
        """
        if not isinstance(settings, dict):
            raise ConfigurationError(f"Settings for platform '{platform}' must be a dictionary")
            
        # Validate based on platform type
        if platform == 'connectwise':
            required_fields = ['url', 'company_id', 'public_key', 'private_key', 'client_id']
            for field in required_fields:
                if field not in settings:
                    raise ConfigurationError(f"Missing required field '{field}' for ConnectWise platform")
                    
        elif platform == 'datto':
            required_fields = ['url', 'api_key']
            for field in required_fields:
                if field not in settings:
                    raise ConfigurationError(f"Missing required field '{field}' for Datto platform")
        
        # Add validation for other platforms as needed
    
    def save(self, config_path: Optional[str] = None) -> bool:
        """Save current configuration to file.
        
        Args:
            config_path: Optional path to save configuration to
            
        Returns:
            bool: True if configuration was saved successfully
        """
        save_path = config_path or self.config_path
        
        try:
            with open(save_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
                
            logger.info(f"Configuration saved to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {str(e)}")
            return False
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get a configuration value by path.
        
        Args:
            path: Dot-separated path to configuration value
            default: Default value if path not found
            
        Returns:
            Any: Configuration value or default
        """
        if not self._loaded:
            logger.warning("Attempting to access configuration before loading")
            return default
            
        parts = path.split('.')
        value = self.config
        
        for part in parts:
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
            
        return value
    
    def set(self, path: str, value: Any) -> bool:
        """Set a configuration value by path.
        
        Args:
            path: Dot-separated path to configuration value
            value: Value to set
            
        Returns:
            bool: True if value was set successfully
        """
        parts = path.split('.')
        config = self.config
        
        # Navigate to the parent of the target node
        for i, part in enumerate(parts[:-1]):
            if part not in config:
                config[part] = {}
            elif not isinstance(config[part], dict):
                logger.error(f"Cannot set '{path}': '{'.'.join(parts[:i+1])}' is not a dictionary")
                return False
                
            config = config[part]
            
        # Set the value
        config[parts[-1]] = value
        return True
    
    def get_platform_config(self, platform: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific platform.
        
        Args:
            platform: Platform name
            
        Returns:
            Optional[Dict[str, Any]]: Platform configuration or None
        """
        return self.get(f"platforms.{platform}")
    
    @property
    def platforms(self) -> List[str]:
        """Get list of configured platforms.
        
        Returns:
            List[str]: List of platform names
        """
        platforms = self.get("platforms", {})
        return list(platforms.keys())
    
    def has_platform(self, platform: str) -> bool:
        """Check if a platform is configured.
        
        Args:
            platform: Platform name
            
        Returns:
            bool: True if platform is configured
        """
        return platform in self.platforms


# Global configuration instance
config = MSPConfiguration()
