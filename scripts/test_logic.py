import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from logic import (
    adjacent_log_returns,
    canon_number,
    forward_log_return,
    nearest_rank,
    release_return,
    release_wednesday,
    weekly_changes,
)


class CanonTests(unittest.TestCase):
    def test_prices_and_stocks(self):
        self.assertEqual(canon_number(25.56), "25.56")
        self.assertEqual(canon_number(25.51), "25.51")
        self.assertEqual(canon_number(86.91), "86.91")
        self.assertEqual(canon_number(2.773), "2.773")
        self.assertEqual(canon_number(338764.0), "338764")
        self.assertEqual(canon_number(91.4), "91.4")


class AlignmentTests(unittest.TestCase):
    def test_wednesday_is_five_days_after_friday(self):
        friday = date(2024, 1, 5)
        self.assertEqual(friday.weekday(), 4)
        wednesday = release_wednesday(friday)
        self.assertEqual(wednesday, date(2024, 1, 10))
        self.assertEqual(wednesday.weekday(), 2)

    def test_gap_over_five_days_is_dropped(self):
        rows = [
            (date(2024, 1, 2), 70.0),
            (date(2024, 1, 10), 77.0),
        ]
        self.assertEqual(adjacent_log_returns(rows), [])

    def test_weekly_change_requires_seven_days(self):
        rows = [
            (date(2024, 1, 5), 100.0),
            (date(2024, 1, 12), 110.0),
            (date(2024, 1, 26), 90.0),
        ]
        changes = weekly_changes(rows)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["change"], 10.0)

    def test_missing_wednesday_is_skipped(self):
        prices = [
            (date(2024, 1, 8), 70.0),
            (date(2024, 1, 9), 71.0),
            (date(2024, 1, 11), 72.0),
        ]
        self.assertIsNone(release_return(prices, date(2024, 1, 5)))

    def test_release_return_uses_prior_print(self):
        prices = [
            (date(2024, 1, 9), 70.0),
            (date(2024, 1, 10), 71.4),
        ]
        result = release_return(prices, date(2024, 1, 5))
        self.assertIsNotNone(result)
        self.assertEqual(result["release"], date(2024, 1, 10))
        self.assertAlmostEqual(result["log_return"], __import__("math").log(71.4 / 70.0))

    def test_forward_five_prints(self):
        rows = [(date(2024, 1, d), 100.0 + d) for d in range(2, 12)]
        value = forward_log_return(rows, date(2024, 1, 2), 5)
        self.assertAlmostEqual(value, __import__("math").log(107 / 102))

    def test_nearest_rank_90(self):
        values = list(range(1, 11))
        self.assertEqual(nearest_rank(values, 0.9), 9)


if __name__ == "__main__":
    unittest.main()
