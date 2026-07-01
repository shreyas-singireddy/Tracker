import time
import unittest
from unittest.mock import patch

from app.utils.performance import SimpleCache, analytics_cache, batch_read, dashboard_cache, timed


class TestTimedDecorator(unittest.TestCase):
    def test_fast_function_logs_debug(self):
        with (
            patch("app.utils.performance.logger.debug") as mock_debug,
            patch("app.utils.performance.logger.warning") as mock_warning,
        ):

            @timed(threshold=0.1)
            def fast():
                return 42

            result = fast()
            self.assertEqual(result, 42)
            mock_debug.assert_called_once()
            mock_warning.assert_not_called()

    def test_slow_function_logs_warning(self):
        with patch("app.utils.performance.logger.warning") as mock_warning:

            @timed(threshold=0.001)
            def slow():
                time.sleep(0.01)
                return "done"

            result = slow()
            self.assertEqual(result, "done")
            mock_warning.assert_called_once()


class TestBatchReadDecorator(unittest.TestCase):
    def test_returns_small_list(self):
        with patch("app.utils.performance.logger.debug") as mock_debug:

            @batch_read
            def get_few():
                return [1, 2, 3]

            self.assertEqual(get_few(), [1, 2, 3])
            mock_debug.assert_not_called()

    def test_returns_large_list_logs_batch(self):
        with patch("app.utils.performance.logger.debug") as mock_debug:

            @batch_read
            def get_many():
                return list(range(20))

            result = get_many()
            self.assertEqual(len(result), 20)
            mock_debug.assert_called_once()

    def test_returns_non_list(self):
        with patch("app.utils.performance.logger.debug") as mock_debug:

            @batch_read
            def get_str():
                return "hello"

            self.assertEqual(get_str(), "hello")
            mock_debug.assert_not_called()


class TestSimpleCache(unittest.TestCase):
    def setUp(self):
        self.cache = SimpleCache(default_ttl=60)

    def test_set_and_get(self):
        self.cache.set("key1", "value1")
        self.assertEqual(self.cache.get("key1"), "value1")

    def test_get_missing_key(self):
        self.assertIsNone(self.cache.get("nonexistent"))

    def test_get_expired_key(self):
        self.cache.set("key2", "value2", ttl=-1)
        self.assertIsNone(self.cache.get("key2"))

    def test_clear(self):
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        self.cache.clear()
        self.assertIsNone(self.cache.get("a"))
        self.assertIsNone(self.cache.get("b"))

    def test_invalidate(self):
        self.cache.set("x", "y")
        self.cache.invalidate("x")
        self.assertIsNone(self.cache.get("x"))

    def test_invalidate_nonexistent(self):
        self.cache.invalidate("missing")
        self.assertIsNone(self.cache.get("missing"))

    def test_custom_ttl(self):
        self.cache.set("short", "lives", ttl=-1)
        self.assertIsNone(self.cache.get("short"))

    def test_default_ttl_used(self):
        self.cache.default_ttl = -1
        self.cache.set("immediate", "expire")
        self.assertIsNone(self.cache.get("immediate"))


class TestGlobalCacheInstances(unittest.TestCase):
    def test_analytics_cache_exists(self):
        self.assertIsInstance(analytics_cache, SimpleCache)
        self.assertEqual(analytics_cache.default_ttl, 300)

    def test_dashboard_cache_exists(self):
        self.assertIsInstance(dashboard_cache, SimpleCache)
        self.assertEqual(dashboard_cache.default_ttl, 60)


if __name__ == "__main__":
    unittest.main()
