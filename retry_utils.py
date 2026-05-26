import time
import random
import asyncio
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)


class RetryError(Exception):
    def __init__(self, message: str, attempts: int, last_exception: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal config
            if config is None:
                config = RetryConfig()
            
            last_exception = None
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts:
                        error_msg = str(last_exception) if last_exception and str(last_exception) else type(last_exception).__name__ if last_exception else "未知错误"
                        logger.error(f"函数 {func.__name__} 在 {attempt} 次尝试后失败: {error_msg}")
                        raise RetryError(
                            f"函数 {func.__name__} 在 {config.max_attempts} 次尝试后失败",
                            config.max_attempts,
                            last_exception
                        )
                    
                    delay = _calculate_delay(attempt, config)
                    # 使用debug级别减少日志噪音，只在最终失败时输出error
                    error_msg = str(e) if str(e) else type(e).__name__
                    logger.debug(
                        f"函数 {func.__name__} 第 {attempt} 次尝试失败: {error_msg}. "
                        f"{delay:.2f}秒后重试..."
                    )
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    time.sleep(delay)
            
            raise RetryError(
                f"函数 {func.__name__} 在 {config.max_attempts} 次尝试后失败",
                config.max_attempts,
                last_exception
            )
        
        return wrapper
    return decorator


def _calculate_delay(attempt: int, config: RetryConfig) -> float:
    delay = config.base_delay * (config.exponential_base ** (attempt - 1))
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        delay = delay * (0.5 + random.random() * 0.5)
    
    return delay


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'
    
    def __enter__(self):
        if self.state == 'open':
            if self._should_attempt_reset():
                self.state = 'half-open'
                logger.info("熔断器进入半开状态，尝试恢复")
            else:
                raise CircuitBreakerError("熔断器处于开启状态，拒绝请求")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, self.expected_exception):
            self._on_failure()
        else:
            self._on_success()
        return False
    
    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(
                f"熔断器开启：失败次数 {self.failure_count} "
                f"达到阈值 {self.failure_threshold}"
            )
    
    def _on_success(self):
        self.failure_count = 0
        self.last_failure_time = None
        if self.state == 'half-open':
            self.state = 'closed'
            logger.info("熔断器已恢复到关闭状态")
    
    def get_state(self) -> str:
        return self.state
    
    def get_failure_count(self) -> int:
        return self.failure_count


class CircuitBreakerError(Exception):
    pass


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception
):
    def decorator(func: Callable) -> Callable:
        cb = CircuitBreaker(failure_threshold, recovery_timeout, expected_exception)
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                with cb:
                    return func(*args, **kwargs)
            except CircuitBreakerError:
                logger.error(f"函数 {func.__name__} 被熔断器拒绝")
                raise
            except Exception as e:
                raise
        
        wrapper.circuit_breaker = cb
        return wrapper
    
    return decorator


# 异步版本的重试机制
def async_retry_with_backoff(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            nonlocal config
            if config is None:
                config = RetryConfig()
            
            last_exception = None
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts:
                        error_msg = str(last_exception) if last_exception and str(last_exception) else type(last_exception).__name__ if last_exception else "未知错误"
                        logger.error(f"异步函数 {func.__name__} 在 {attempt} 次尝试后失败: {error_msg}")
                        raise RetryError(
                            f"异步函数 {func.__name__} 在 {config.max_attempts} 次尝试后失败",
                            config.max_attempts,
                            last_exception
                        )
                    
                    delay = _calculate_delay(attempt, config)
                    # 使用debug级别减少日志噪音，只在最终失败时输出error
                    error_msg = str(e) if str(e) else type(e).__name__
                    logger.debug(
                        f"异步函数 {func.__name__} 第 {attempt} 次尝试失败: {error_msg}. "
                        f"{delay:.2f}秒后重试..."
                    )
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    await asyncio.sleep(delay)
            
            raise RetryError(
                f"异步函数 {func.__name__} 在 {config.max_attempts} 次尝试后失败",
                config.max_attempts,
                last_exception
            )
        
        return wrapper
    return decorator


# 异步版本的熔断器
class AsyncCircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        async with self._lock:
            if self.state == 'open':
                if self._should_attempt_reset():
                    self.state = 'half-open'
                    logger.info("异步熔断器进入半开状态，尝试恢复")
                else:
                    raise CircuitBreakerError("异步熔断器处于开启状态，拒绝请求")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._lock:
            if exc_type is not None and issubclass(exc_type, self.expected_exception):
                await self._on_failure()
            else:
                await self._on_success()
        return False
    
    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    async def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(
                f"异步熔断器开启：失败次数 {self.failure_count} "
                f"达到阈值 {self.failure_threshold}"
            )
    
    async def _on_success(self):
        self.failure_count = 0
        self.last_failure_time = None
        if self.state == 'half-open':
            self.state = 'closed'
            logger.info("异步熔断器已恢复到关闭状态")
    
    def get_state(self) -> str:
        return self.state
    
    def get_failure_count(self) -> int:
        return self.failure_count


def async_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception
):
    def decorator(func: Callable) -> Callable:
        cb = AsyncCircuitBreaker(failure_threshold, recovery_timeout, expected_exception)
        
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                async with cb:
                    return await func(*args, **kwargs)
            except CircuitBreakerError:
                logger.error(f"异步函数 {func.__name__} 被熔断器拒绝")
                raise
            except Exception as e:
                raise
        
        wrapper.circuit_breaker = cb
        return wrapper
    
    return decorator

