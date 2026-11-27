"""Tính checksum cho các tệp mô hình và mã suy luận đã xuất."""
import hashlib
from pathlib import Path


def artifact_digest(path):
    # Python chuẩn hóa kiểu xuống dòng khi đọc tệp văn bản để Git trên Windows và Linux cho cùng mã băm.
    path = Path(path)
    content = (path.read_text(encoding='utf-8').encode('utf-8')
               if path.suffix in ['.py','.json'] else path.read_bytes())
    return hashlib.sha256(content).hexdigest()
