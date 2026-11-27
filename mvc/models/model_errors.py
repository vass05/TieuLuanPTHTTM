"""Các ngoại lệ nghiệp vụ được controller chuyển thành phản hồi HTTP."""


class ModelUnavailableError(RuntimeError):
    """Mô hình hoặc nguồn dữ liệu cần cho yêu cầu hiện chưa sẵn sàng."""
    pass


class TaskConflictError(RuntimeError):
    """Yêu cầu xung đột với trạng thái hiện tại của lượt xử lý hoặc hội thoại."""
    pass
