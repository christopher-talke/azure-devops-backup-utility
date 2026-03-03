"""Tests for backoff retry logic."""

import unittest

from ado_backup.backoff import retry


class TestRetry(unittest.TestCase):
    def test_success_first_try(self):
        result = retry(lambda: 42, max_retries=3, base_delay=0.01)
        self.assertEqual(result, 42)

    def test_retry_then_success(self):
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "ok"

        result = retry(flaky, max_retries=3, base_delay=0.01, retryable=(ValueError,))
        self.assertEqual(result, "ok")
        self.assertEqual(call_count, 3)

    def test_all_retries_exhausted(self):
        def always_fail():
            raise RuntimeError("always")

        with self.assertRaises(RuntimeError):
            retry(always_fail, max_retries=2, base_delay=0.01, retryable=(RuntimeError,))

    def test_non_retryable_exception(self):
        def raise_type_error():
            raise TypeError("not retryable")

        with self.assertRaises(TypeError):
            retry(raise_type_error, max_retries=3, base_delay=0.01, retryable=(ValueError,))


if __name__ == "__main__":
    unittest.main()
