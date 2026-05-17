"""watchdog file watcher — rebuilds BM25 index when .md files change."""
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from . import retrieval

log = logging.getLogger(__name__)


class _KBHandler(FileSystemEventHandler):
    def __init__(self, knowledge_dir: Path):
        self._dir = knowledge_dir

    def _reindex(self):
        try:
            count = retrieval.init(self._dir)
            log.info(f"[consultant] KB reindexed: {count} sections")
        except Exception as e:
            log.error(f"[consultant] reindex failed: {e}")

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            self._reindex()

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            self._reindex()

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            self._reindex()


def start_watcher(knowledge_dir: str | Path) -> Observer:
    knowledge_dir = Path(knowledge_dir)
    handler = _KBHandler(knowledge_dir)
    observer = Observer()
    observer.schedule(handler, str(knowledge_dir), recursive=False)
    observer.start()
    log.info(f"[consultant] Watching {knowledge_dir} for changes")
    return observer
