"""
Setup script for MSP integration module.
"""

import os
import shutil
import subprocess
import sys

def check_python_version():
    """Check if Python version is 3.7 or higher."""
    required_version = (3, 7)
    current_version = sys.version_info
    
    if current_version < required_version:
        print(f"ERROR: Python {required_version[0]}.{required_version[1]} or higher is required")
        print(f"Current version: {current_version[0]}.{current_version[1]}")
        return False
    
    return True


def check_pip():
    """Check if pip is installed."""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', '--version'], 
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: pip is not installed or not working correctly")
        return False


def install_requirements():
    """Install required packages."""
    requirements_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    'requirements-msp.txt')
    
    if not os.path.exists(requirements_path):
        print(f"ERROR: Could not find requirements file: {requirements_path}")
        return False
    
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_path])
        print("Required packages installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to install requirements: {e}")
        return False


def create_config_template():
    """Create a configuration template file."""
    config_dir = os.path.join(os.path.dirname(__file__), 'config')
    template_path = os.path.join(config_dir, 'config_template.yaml')
    
    os.makedirs(config_dir, exist_ok=True)
    
    with open(template_path, 'w') as f:
        f.write('''# MSP Integration Configuration

# Platform Connections
platforms:
  connectwise:
    url: "https://your-instance.connectwise.com"
    company_id: "your_company"
    public_key: "your_public_key"
    private_key: "your_private_key"
    client_id: "your_client_id"
    automate_url: "https://your-instance.automate.net"  # Optional for Automate integration

# Monitoring Settings
monitoring:
  scan_interval: 15  # minutes
  anomaly_threshold: 0.8  # 0.0 to 1.0, higher means fewer alerts
  auto_remediate: false  # Set to true for automated remediation

# Client Information
clients:
  - id: "client1"  # Client identifier in the platform
    name: "Client One"  # Display name
    enabled: true  # Set to false to disable monitoring
  - id: "client2"
    name: "Client Two"
    enabled: true

# Dashboard Settings
dashboard:
  update_interval: 5  # minutes
  port: 5000  # Web server port
  host: "0.0.0.0"  # Web server host (0.0.0.0 for all interfaces)
''')
    
    print(f"Configuration template created: {template_path}")
    return True


def create_init_script():
    """Create initialization script."""
    script_dir = os.path.join(os.path.dirname(__file__), 'scripts')
    script_path = os.path.join(script_dir, 'init_monitoring.py')
    
    os.makedirs(script_dir, exist_ok=True)
    
    with open(script_path, 'w') as f:
        f.write('''"""\nInitialization script for MSP monitoring.\n\nThis script helps set up the MSP integration module for first use.\nIt creates a configuration file and initializes the monitoring system.\n"""\n\nimport os\nimport sys\nimport shutil\nimport logging\nfrom pathlib import Path\n\n# Add project root to path to allow importing project modules\nsys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'../../../\')))\n\nfrom src.msp_integration.config import MSPConfiguration\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format=\'%(asctime)s - %(name)s - %(levelname)s - %(message)s\'\n)\n\nlogger = logging.getLogger(__name__)\n\n\ndef create_config():\n    """Create configuration file from template."""\n    # Get template path\n    template_path = os.path.join(\n        os.path.dirname(os.path.dirname(__file__)),\n        \'config\',\n        \'config_template.yaml\'\n    )\n    \n    if not os.path.exists(template_path):\n        logger.error(f"Template file not found: {template_path}")\n        return False\n    \n    # Determine config file location\n    config_path = \'config.yaml\'\n    \n    # Check if config already exists\n    if os.path.exists(config_path):\n        overwrite = input(f"Configuration file already exists: {config_path}. Overwrite? (y/n): ")\n        if overwrite.lower() != \'y\':\n            logger.info("Using existing configuration file")\n            return True\n    \n    # Copy template to config location\n    try:\n        shutil.copy(template_path, config_path)\n        logger.info(f"Created configuration file: {config_path}")\n        logger.info(f"Please edit {config_path} with your actual platform credentials")\n        return True\n    except Exception as e:\n        logger.error(f"Failed to create configuration file: {e}")\n        return False\n\n\ndef create_directories():\n    """Create necessary directories."""\n    directories = [\n        \'logs\',\n        \'models\'\n    ]\n    \n    for directory in directories:\n        os.makedirs(directory, exist_ok=True)\n        logger.info(f"Created directory: {directory}")\n    \n    return True\n\n\ndef main():\n    """Main function."""\n    print("=" * 60)\n    print("MSP Integration Initialization")\n    print("=" * 60)\n    \n    # Create directories\n    if not create_directories():\n        logger.error("Failed to create required directories")\n        return 1\n    \n    # Create configuration file\n    if not create_config():\n        logger.error("Failed to create configuration file")\n        return 1\n    \n    print("\\nInitialization complete!")\n    print("\\nNext steps:")\n    print("1. Edit config.yaml with your platform credentials")\n    print("2. Run the ConnectWise integration example:")\n    print("   python src/msp_integration/examples/connectwise_integration.py")\n    print("3. Or start the monitoring dashboard:")\n    print("   python src/msp_integration/examples/dashboard.py")\n    \n    return 0\n\n\nif __name__ == "__main__":\n    sys.exit(main())\n''')
    
    print(f"Initialization script created: {script_path}")
    return True


def setup():
    """Run the setup process."""
    print("=" * 60)
    print("MSP Integration Module Setup")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Check pip
    if not check_pip():
        return 1
    
    # Install requirements
    if not install_requirements():
        return 1
    
    # Create config template
    if not create_config_template():
        return 1
    
    # Create init script
    if not create_init_script():
        return 1
    
    print("\nSetup complete!")
    print("\nNext steps:")
    print("1. Initialize the MSP integration module:")
    print("   python -m src.msp_integration.scripts.init_monitoring")
    print("2. Edit the generated config.yaml with your platform credentials")
    print("3. Run the ConnectWise integration example:")
    print("   python -m src.msp_integration.examples.connectwise_integration")
    print("4. Or start the monitoring dashboard:")
    print("   python -m src.msp_integration.examples.dashboard")
    
    return 0


if __name__ == "__main__":
    sys.exit(setup())
