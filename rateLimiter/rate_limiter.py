import time


class RateLimiter:
    def __init__(self, max_requests, duration):
        self.max_requests = max_requests
        self.duration = duration
        self.timestamps = []

    def is_allowed_for_request_length(self, request_length):
        current_time = time.time()

        # 移除过期的时间戳
        self.timestamps = [ts for ts in self.timestamps if ts >= current_time - self.duration]

        # 检查请求数是否超过限制
        if len(self.timestamps) + request_length < self.max_requests:
            self.timestamps.append(current_time)
            return True
        else:
            return False

    def is_allowed(self):
        current_time = time.time()

        # 移除过期的时间戳
        self.timestamps = [ts for ts in self.timestamps if ts >= current_time - self.duration]

        # 检查请求数是否超过限制
        if len(self.timestamps) < self.max_requests:
            self.timestamps.append(current_time)
            return True
        else:
            return False
