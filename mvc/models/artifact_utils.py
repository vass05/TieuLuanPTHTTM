"""Checksums that survive Git's text line-ending normalization."""
import hashlib
from pathlib import Path


def artifact_digest(path):
    path = Path(path)
    content = (path.read_text(encoding='utf-8').encode('utf-8')
               if path.suffix in ['.py','.json'] else path.read_bytes())
    return hashlib.sha256(content).hexdigest()
