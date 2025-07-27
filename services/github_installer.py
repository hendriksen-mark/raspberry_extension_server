import shutil
import tempfile
import zipfile
import subprocess
import requests
from pathlib import Path
from typing import Any
import logging

import configManager
import logManager

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config
logger: logging.Logger = logManager.logger.get_logger(__name__)

class GitHubInstaller:
    """
    Pure Python implementation for updating the server from GitHub releases.
    """
    
    def __init__(self):
        self.server_path = Path(configManager.serverConfig.runningDir)
        self.temp_dir = None
        
    def install_updates(self, state: str, branch: str) -> bool:
        """
        Install updates from GitHub based on the state.
        
        Args:
            state: The update state ("allreadytoinstall" or "anyreadytoinstall")
            branch: The branch to download from
        Returns:
            bool: True if installation was successful, False otherwise
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                self.temp_dir = Path(temp_dir)
                # Set state to transferring while downloading
                serverConfig["config"]["swupdate2"]["state"] = "transferring"
                if state == "allreadytoinstall":
                    logger.info("Installing server + UI update")
                    if not self._install_server_update(branch):
                        return False
                else:
                    logger.info("Installing UI update only")
                # Set state to installing after download/transfer
                serverConfig["config"]["swupdate2"]["state"] = "transferring"
                # Always install UI update
                if not self._install_ui_update():
                    return False
            logger.info("Update installation completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error during update installation: {e}")
            return False
    
    def _install_server_update(self, branch: str) -> bool:
        """Install server update from GitHub."""
        try:
            # Download server archive
            server_url = f"https://github.com/hendriksen-mark/raspberry_extension_server/archive/{branch}.zip"
            server_zip_path = self.temp_dir / "server.zip"
            
            logger.info(f"Downloading server update from {server_url}")
            if not self._download_file(server_url, server_zip_path):
                return False
            
            serverConfig["config"]["swupdate2"]["state"] = "installing"
            
            # Extract archive
            extract_dir = self.temp_dir / "server_extract"
            if not self._extract_zip(server_zip_path, extract_dir):
                return False
            
            server_zip_path.unlink()  # Remove zip file
            
            # Find the extracted directory
            extracted_dirs = list(extract_dir.glob("raspberry_extension_server-*"))
            if not extracted_dirs:
                logger.error("Could not find extracted server directory")
                return False
            
            server_source = extracted_dirs[0]
            
            # Update pip and install requirements
            if not self._update_python_dependencies(server_source / "requirements.txt"):
                return False
            
            # Copy server files
            files_to_copy = [
                "flaskUI",
                "ServerObjects", 
                "services",
                "configManager",
                "api.py"
            ]
            
            for item in files_to_copy:
                source = server_source / item
                dest = self.server_path / item
                
                if source.exists():
                    if source.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(source, dest)
                    else:
                        shutil.copy2(source, dest)
                    logger.debug(f"Copied {item} to server directory")
                else:
                    logger.warning(f"Source file/directory not found: {source}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error installing server update: {e}")
            return False
    
    def _install_ui_update(self) -> bool:
        """Install UI update from GitHub releases."""
        try:
            # Download UI archive
            ui_url = "https://github.com/hendriksen-mark/raspberry_extension_server_ui/releases/latest/download/raspberry_extension_server_ui-release.zip"
            ui_zip_path = self.temp_dir / "serverUI.zip"
            
            logger.info(f"Downloading UI update from {ui_url}")
            if not self._download_file(ui_url, ui_zip_path):
                return False
            
            serverConfig["config"]["swupdate2"]["state"] = "installing"
            
            # Extract UI archive
            ui_extract_dir = self.temp_dir / "raspberry_extension_server_ui"
            ui_extract_dir.mkdir(exist_ok=True)
            
            if not self._extract_zip(ui_zip_path, ui_extract_dir):
                return False
            
            ui_zip_path.unlink()  # Remove zip file
            
            # Copy UI files
            ui_source = ui_extract_dir / "dist"
            if not ui_source.exists():
                logger.error("UI dist directory not found in extracted archive")
                return False
            
            # Copy index.html
            index_source = ui_source / "index.html"
            index_dest = self.server_path / "flaskUI" / "templates" / "index.html"
            if index_source.exists():
                shutil.copy2(index_source, index_dest)
                logger.debug("Copied UI index.html")
            
            # Copy assets (merge instead of replace to preserve existing server assets)
            assets_source = ui_source / "assets"
            assets_dest = self.server_path / "flaskUI" / "assets"
            if assets_source.exists():
                # Ensure destination directory exists
                assets_dest.mkdir(parents=True, exist_ok=True)
                
                # Copy only the files from the UI update, preserving existing assets
                for item in assets_source.iterdir():
                    dest_item = assets_dest / item.name
                    if item.is_dir():
                        if dest_item.exists():
                            shutil.rmtree(dest_item)
                        shutil.copytree(item, dest_item)
                    else:
                        shutil.copy2(item, dest_item)
                
                logger.debug("Merged UI assets with existing assets")
            
            return True
            
        except Exception as e:
            logger.error(f"Error installing UI update: {e}")
            return False
    
    def _download_file(self, url: str, dest_path: Path) -> bool:
        """Download a file from URL to destination path."""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.debug(f"Downloaded {url} to {dest_path}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error downloading {url}: {e}")
            return False
    
    def _extract_zip(self, zip_path: Path, extract_to: Path) -> bool:
        """Extract a zip file to the specified directory."""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            
            logger.debug(f"Extracted {zip_path} to {extract_to}")
            return True
            
        except zipfile.BadZipFile as e:
            logger.error(f"Error extracting {zip_path}: {e}")
            return False
    
    def _update_python_dependencies(self, requirements_path: Path) -> bool:
        """Update pip and install requirements."""
        try:
            # Update pip
            subprocess.run([
                "python3", "-m", "pip", "install", "--upgrade", "pip", "--break-system-packages"
            ], check=True, capture_output=True, text=True)
            
            # Install requirements
            if requirements_path.exists():
                subprocess.run([
                    "pip3", "install", "-r", str(requirements_path), 
                    "--no-cache-dir", "--break-system-packages"
                ], check=True, capture_output=True, text=True)
                
                logger.debug("Updated Python dependencies")
            else:
                logger.warning(f"Requirements file not found: {requirements_path}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error updating Python dependencies: {e}")
            return False
    

def install_github_updates(state: str, branch: str) -> bool:
    """
    Install updates from GitHub.
    
    Args:
        state: The update state ("allreadytoinstall" or "anyreadytoinstall")
        branch: The branch to download from
        
    Returns:
        bool: True if installation was successful, False otherwise
    """
    installer = GitHubInstaller()
    return installer.install_updates(state, branch)
