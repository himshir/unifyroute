import yaml
import threading
import logging
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

# Global configuration store
config_lock = threading.Lock()
routing_config = {}

class ConfigReloader(FileSystemEventHandler):
    def __init__(self, filename):
        self.filename = filename

    def on_modified(self, event):
        if event.src_path.endswith(self.filename):
            logger.info("routing.yaml changed, reloading...")
            load_config(self.filename)

def load_config(filepath: str = "routing.yaml"):
    global routing_config
    if not os.path.exists(filepath):
        logger.warning(f"Config file {filepath} not found. Using empty config.")
        with config_lock:
            routing_config = {"tiers": {}}
        return

    try:
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)
            with config_lock:
                routing_config.clear()
                routing_config.update(data)
                logger.info(f"Loaded routing config with {len(routing_config.get('tiers', {}))} tiers.")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")

def get_routing_config() -> dict:
    with config_lock:
        return dict(routing_config)

def start_watchdog(filepath: str = "routing.yaml"):
    """Starts a watchdog observer to reload the config on file change."""
    load_config(filepath)
    directory = os.path.dirname(os.path.abspath(filepath))
    filename = os.path.basename(filepath)
    event_handler = ConfigReloader(filename)
    
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=False)
    observer.start()
    return observer
