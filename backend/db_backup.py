import os
import shutil
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_FILE = os.path.join(os.path.dirname(__file__), 'ncc_database.db')
BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'backups')

def backup_database():
    if not os.path.exists(DB_FILE):
        logger.error(f"Database file not found at {DB_FILE}")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'ncc_db_{timestamp}.db')
    
    try:
        shutil.copy2(DB_FILE, backup_file)
        logger.info(f"Database backed up successfully to {backup_file}")
    except Exception as e:
        logger.error(f"Backup failed: {e}")

if __name__ == '__main__':
    backup_database()
