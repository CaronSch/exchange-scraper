import time
from functools import wraps
from typing import Callable

class RateLimiter:
    def __init__(self, calls_per_second: int):
        self.calls_per_second = calls_per_second
        self.last_call_time = 0

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Calculate time to wait
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time
            time_to_wait = max(0, (1.0 / self.calls_per_second) - time_since_last_call)
            
            # Sleep if needed
            if time_to_wait > 0:
                time.sleep(time_to_wait)
            
            # Update last call time and execute function
            self.last_call_time = time.time()
            return func(*args, **kwargs)
        return wrapper 