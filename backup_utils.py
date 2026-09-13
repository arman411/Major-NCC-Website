"""
backup_utils.py — Automated database backup and restore utilities.
Handles creating timestamped SQLite backups, cleanup of old backups,
and safe restoration with pre-restore emergency backup.
"""
import os
import shutil
import glob
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'backups')
DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'ncc_database.db')
DB_PATH_ALT = os.path.join(os.path.dirname(__file__), 'ncc_database.db')
MAX_BACKUPS = 7


def get_db_path():
    """Find the active database file."""
    if os.path.exists(DB_PATH):
        return DB_PATH
    if os.path.exists(DB_PATH_ALT):
        return DB_PATH_ALT
    return DB_PATH_ALT  # default location


def backup_database(label='auto'):
    """
    Create a timestamped backup of the SQLite database.
    Returns the path to the backup file, or None on failure.
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        logger.warning(f"Database not found at {db_path}, skipping backup.")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'ncc_backup_{label}_{timestamp}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        shutil.copy2(db_path, backup_path)
        size_kb = os.path.getsize(backup_path) // 1024
        logger.info(f"✅ Database backup created: {backup_filename} ({size_kb} KB)")
        cleanup_old_backups()
        return backup_path
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        return None


def cleanup_old_backups(keep=MAX_BACKUPS):
    """Remove old backups, keeping only the most recent `keep` files."""
    pattern = os.path.join(BACKUP_DIR, 'ncc_backup_*.db')
    backups = sorted(glob.glob(pattern))
    while len(backups) > keep:
        oldest = backups.pop(0)
        try:
            os.remove(oldest)
            logger.info(f"🗑️ Removed old backup: {os.path.basename(oldest)}")
        except Exception as e:
            logger.error(f"Failed to remove old backup {oldest}: {e}")


def list_backups():
    """
    List all available backups with metadata.
    Returns a list of dicts with filename, size_kb, created_at.
    """
    pattern = os.path.join(BACKUP_DIR, 'ncc_backup_*.db')
    backups = sorted(glob.glob(pattern), reverse=True)
    result = []
    for path in backups:
        stat = os.stat(path)
        result.append({
            'filename': os.path.basename(path),
            'path': path,
            'size_kb': stat.st_size // 1024,
            'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    return result


def restore_database(backup_path):
    """
    Restore the database from a backup file.
    Creates an emergency backup of current DB before restoring.
    Returns True on success, False on failure.
    """
    if not os.path.exists(backup_path):
        logger.error(f"Backup file not found: {backup_path}")
        return False
    
    # Create emergency backup of current DB first
    emergency = backup_database(label='pre-restore-emergency')
    if emergency:
        logger.info(f"Emergency backup created before restore: {emergency}")
    
    db_path = get_db_path()
    try:
        shutil.copy2(backup_path, db_path)
        logger.info(f"✅ Database restored from {os.path.basename(backup_path)}")
        return True
    except Exception as e:
        logger.error(f"❌ Restore failed: {e}")
        return False
