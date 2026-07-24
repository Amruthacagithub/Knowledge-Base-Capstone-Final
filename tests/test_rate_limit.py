from backend.services.rate_limit import SlidingWindowRateLimiter


def test_sliding_window_limits_and_recovers_after_window():
    limiter = SlidingWindowRateLimiter()

    assert limiter.check("user", 2, window_seconds=60, now=0).allowed
    assert limiter.check("user", 2, window_seconds=60, now=1).allowed
    denied = limiter.check("user", 2, window_seconds=60, now=2)
    recovered = limiter.check("user", 2, window_seconds=60, now=61)

    assert denied.allowed is False
    assert denied.retry_after_seconds == 59
    assert recovered.allowed is True