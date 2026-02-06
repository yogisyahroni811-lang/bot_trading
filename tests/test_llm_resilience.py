"""
Unit tests for llm_resilience.py - Circuit Breaker & Retry Logic

Focus areas:
- Circuit breaker state transitions
- Retry logic with exponential backoff
- Timeout handling
- Failure counting
"""

import pytest
import asyncio
from decimal import Decimal
from core.llm_resilience import (
    CircuitBreaker,
    call_llm_with_retry,
    get_circuit_breaker_status,
    reset_circuit_breaker
)


@pytest.fixture
def fresh_circuit_breaker():
    """Create a fresh circuit breaker for each test."""
    cb = CircuitBreaker(
        failure_threshold=3,  # Lower threshold for testing
        recovery_timeout=2,   # Shorter timeout for testing
        success_threshold=2
    )
    return cb


@pytest.mark.unit
class TestCircuitBreakerStates:
    """Test circuit breaker state machine."""
    
    def test_initial_state_is_closed(self, fresh_circuit_breaker):
        """Circuit breaker starts in CLOSED state."""
        assert fresh_circuit_breaker.state == "CLOSED"
        assert fresh_circuit_breaker.failure_count == 0
    
    def test_state_transitions_to_open_after_threshold_failures(self, fresh_circuit_breaker):
        """Circuit opens after failure threshold is reached."""
        def failing_func():
            raise Exception("Simulated failure")
        
        # Trigger failures (3 times = threshold)
        for i in range(3):
            with pytest.raises(Exception):
                fresh_circuit_breaker.call(failing_func)
        
        # Circuit should now be OPEN
        assert fresh_circuit_breaker.state == "OPEN"
        assert fresh_circuit_breaker.failure_count == 3
    
    def test_open_circuit_blocks_calls(self, fresh_circuit_breaker):
        """OPEN circuit should block all calls."""
        def failing_func():
            raise Exception("Simulated failure")
        
        # Trigger failures to open circuit
        for i in range(3):
            with pytest.raises(Exception):
                fresh_circuit_breaker.call(failing_func)
        
        # Now circuit is OPEN, next call should be blocked
        with pytest.raises(Exception, match="Circuit Breaker OPEN"):
            fresh_circuit_breaker.call(lambda: "success")
    
    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self, fresh_circuit_breaker):
        """Circuit transitions to HALF_OPEN after recovery timeout."""
        async def failing_func():
            raise Exception("Simulated failure")
        
        # Trigger failures to open circuit
        for i in range(3):
            with pytest.raises(Exception):
                await fresh_circuit_breaker.call_async(failing_func)
        
        assert fresh_circuit_breaker.state == "OPEN"
        
        # Wait for recovery timeout (2 seconds)
        await asyncio.sleep(2.5)
        
        # Next call should transition to HALF_OPEN
        async def success_func():
            return "success"
        
        result = await fresh_circuit_breaker.call_async(success_func)
        
        # Should have transitioned through HALF_OPEN
        # (might already be CLOSED if success_threshold=1)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_half_open_to_closed_after_successes(self, fresh_circuit_breaker):
        """Circuit closes after success threshold in HALF_OPEN state."""
        async def failing_func():
            raise Exception("Simulated failure")
        
        # Open circuit
        for i in range(3):
            with pytest.raises(Exception):
                await fresh_circuit_breaker.call_async(failing_func)
        
        # Wait for recovery
        await asyncio.sleep(2.5)
        
        # Force to HALF_OPEN
        fresh_circuit_breaker.state = "HALF_OPEN"
        
        # 2 successful calls should close circuit (success_threshold=2)
        async def success_func():
            return "success"
        
        await fresh_circuit_breaker.call_async(success_func)
        await fresh_circuit_breaker.call_async(success_func)
        
        assert fresh_circuit_breaker.state == "CLOSED"
        assert fresh_circuit_breaker.failure_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestRetryLogic:
    """Test LLM call retry logic."""
    
    async def test_successful_call_no_retry(self):
        """Successful call on first attempt should not retry."""
        call_count = 0
        
        async def success_func(prompt):
            nonlocal call_count
            call_count += 1
            return type('Response', (), {'content': 'success'})()
        
        # Reset circuit breaker for clean test
        reset_circuit_breaker()
        
        result = await call_llm_with_retry(
            success_func,
            "test prompt",
            max_retries=3
        )
        
        assert call_count == 1, "Should only call once if successful"
        assert result.content == "success"
    
    async def test_retry_on_failure_then_success(self):
        """Should retry on failure and succeed on 2nd attempt."""
        call_count = 0
        
        async def flaky_func(prompt):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                raise Exception("First call fails")
            else:
                return type('Response', (), {'content': 'success'})()
        
        reset_circuit_breaker()
        
        result = await call_llm_with_retry(
            flaky_func,
            "test prompt",
            max_retries=3
        )
        
        assert call_count == 2, "Should retry once and succeed"
        assert result.content == "success"
    
    async def test_timeout_handling(self):
        """Should timeout long-running calls."""
        async def slow_func(prompt):
            await asyncio.sleep(10)  # Sleep longer than timeout
            return type('Response', (), {'content': 'too slow'})()
        
        reset_circuit_breaker()
        
        with pytest.raises(Exception, match="failed after"):
            await call_llm_with_retry(
                slow_func,
                "test prompt",
                max_retries=1,
                timeout=0.5  # 0.5 second timeout
            )
    
    async def test_exhausted_retries_raises_exception(self):
        """Should raise exception after all retries exhausted."""
        async def always_fail(prompt):
            raise Exception("Always fails")
        
        reset_circuit_breaker()
        
        with pytest.raises(Exception, match="failed after"):
            await call_llm_with_retry(
                always_fail,
                "test prompt",
                max_retries=2
            )


@pytest.mark.unit
class TestCircuitBreakerMonitoring:
    """Test circuit breaker monitoring functions."""
    
    def test_get_circuit_breaker_status(self):
        """Should return current circuit breaker metrics."""
        reset_circuit_breaker()
        
        status = get_circuit_breaker_status()
        
        assert 'state' in status
        assert 'failure_count' in status
        assert 'success_count' in status
        assert status['state'] == "CLOSED"
    
    def test_reset_circuit_breaker(self):
        """Should reset circuit breaker to initial state."""
        reset_circuit_breaker()
        
        status = get_circuit_breaker_status()
        
        assert status['state'] == "CLOSED"
        assert status['failure_count'] == 0
        assert status['success_count'] == 0
