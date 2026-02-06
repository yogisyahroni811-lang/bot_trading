"""
Resilient LLM Call Wrapper with Retry Logic and Circuit Breaker.

This module provides production-ready error handling for all LLM API calls:
- Exponential backoff retry logic
- Circuit breaker pattern to prevent cascading failures
- Timeout handling
- Comprehensive error logging
"""

import asyncio
import time
from typing import Optional, Callable, Any
from datetime import datetime, timedelta
import logging

# Configure structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation to prevent cascading LLM failures.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, block all requests
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self, 
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            success_threshold: Consecutive successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Raises:
            Exception: If circuit is OPEN or function fails
        """
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                logger.info("Circuit Breaker: HALF_OPEN - Testing recovery")
            else:
                raise Exception(
                    f"Circuit Breaker OPEN: LLM calls blocked. "
                    f"Retry after {self.recovery_timeout}s from last failure."
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Async version of circuit breaker call."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                logger.info("Circuit Breaker: HALF_OPEN - Testing recovery")
            else:
                raise Exception(
                    f"Circuit Breaker OPEN: LLM calls blocked. "
                    f"Retry after {self.recovery_timeout}s from last failure."
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "CLOSED"
                self.success_count = 0
                logger.info("Circuit Breaker: CLOSED - Service recovered")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self.success_count = 0
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(
                f"Circuit Breaker: OPEN after {self.failure_count} failures. "
                f"Blocking LLM calls for {self.recovery_timeout}s"
            )


# Global circuit breaker instance
llm_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=2
)


async def call_llm_with_retry(
    llm_func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    timeout: float = 30.0,
    **kwargs
) -> Any:
    """
    Call LLM with exponential backoff retry logic and circuit breaker.
    
    Args:
        llm_func: Async LLM function to call (e.g., llm.ainvoke)
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        timeout: Timeout for each LLM call (seconds)
        *args, **kwargs: Arguments to pass to llm_func
        
    Returns:
        LLM response object
        
    Raises:
        Exception: If all retries exhausted or circuit breaker is OPEN
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            # Wrap LLM call with timeout
            async def llm_call_with_timeout():
                return await asyncio.wait_for(
                    llm_func(*args, **kwargs),
                    timeout=timeout
                )
            
            # Execute through circuit breaker
            result = await llm_circuit_breaker.call_async(llm_call_with_timeout)
            
            if attempt > 0:
                logger.info(f"LLM call succeeded on attempt {attempt + 1}")
            
            return result
            
        except asyncio.TimeoutError as e:
            last_exception = e
            logger.warning(
                f"LLM call timeout after {timeout}s (attempt {attempt + 1}/{max_retries + 1})"
            )
            
        except Exception as e:
            last_exception = e
            logger.warning(
                f"LLM call failed: {type(e).__name__}: {str(e)} "
                f"(attempt {attempt + 1}/{max_retries + 1})"
            )
        
        # Don't sleep after last attempt
        if attempt < max_retries:
            # Exponential backoff with jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            # Add random jitter (±20%)
            import random
            jitter = delay * 0.2 * (random.random() - 0.5) * 2
            sleep_time = delay + jitter
            
            logger.info(f"Retrying in {sleep_time:.2f}s...")
            await asyncio.sleep(sleep_time)
    
    # All retries exhausted
    error_msg = f"LLM call failed after {max_retries + 1} attempts: {str(last_exception)}"
    logger.error(error_msg)
    raise Exception(error_msg)


def get_circuit_breaker_status() -> dict:
    """
    Get current circuit breaker status for monitoring.
    
    Returns:
        Dictionary with circuit breaker metrics
    """
    return {
        "state": llm_circuit_breaker.state,
        "failure_count": llm_circuit_breaker.failure_count,
        "success_count": llm_circuit_breaker.success_count,
        "last_failure_time": llm_circuit_breaker.last_failure_time.isoformat() 
            if llm_circuit_breaker.last_failure_time else None
    }


def reset_circuit_breaker():
    """
    Manually reset circuit breaker (for testing or emergency recovery).
    USE WITH CAUTION in production.
    """
    global llm_circuit_breaker
    llm_circuit_breaker.state = "CLOSED"
    llm_circuit_breaker.failure_count = 0
    llm_circuit_breaker.success_count = 0
    llm_circuit_breaker.last_failure_time = None
    logger.warning("Circuit Breaker manually reset to CLOSED state")
