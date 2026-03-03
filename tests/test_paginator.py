"""Tests for paginator."""

import unittest

from paginator import paginate


class TestPaginate(unittest.TestCase):
    def test_single_page(self):
        def fetch(continuation_token=None):
            return ([1, 2, 3], None)

        result = paginate(fetch)
        self.assertEqual(result, [1, 2, 3])

    def test_multiple_pages(self):
        pages = [
            ([1, 2], "token1"),
            ([3, 4], "token2"),
            ([5], None),
        ]
        call_count = 0

        def fetch(continuation_token=None):
            nonlocal call_count
            page = pages[call_count]
            call_count += 1
            return page

        result = paginate(fetch)
        self.assertEqual(result, [1, 2, 3, 4, 5])
        self.assertEqual(call_count, 3)

    def test_max_pages(self):
        def fetch(continuation_token=None):
            return ([1], "next")

        result = paginate(fetch, max_pages=3)
        self.assertEqual(result, [1, 1, 1])


if __name__ == "__main__":
    unittest.main()
