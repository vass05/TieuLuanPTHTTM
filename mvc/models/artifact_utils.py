"""Tính checksum cho các tệp mô hình và mã suy luận đã xuất."""
import hashlib
from pathlib import Path


def artifact_digest(path):
    path = Path(path)
    # Đọc Python và JSON dưới dạng văn bản để chuẩn hóa xuống dòng giữa Windows và Linux.
    # Với trọng số và các tệp khác, tính SHA-256 trên byte gốc.
    content = (path.read_text(encoding='utf-8').encode('utf-8')
               if path.suffix in ['.py','.json'] else path.read_bytes())
    return hashlib.sha256(content).hexdigest()
