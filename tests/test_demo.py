"""python -m unittest discover tests   (needs duckdb)"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = tempfile.mkdtemp()
os.environ["WAREHOUSE_DIR"] = TMP
sys.path.insert(0, str(ROOT / "loaders"))
sys.path.insert(0, str(ROOT / "demo"))

import make_demo  # noqa: E402
import title_candidates  # noqa: E402
from gsc_load import month_windows  # noqa: E402
from datetime import date  # noqa: E402


class WarehouseDemo(unittest.TestCase):
    def test_expected_ctr_interpolates(self):
        self.assertAlmostEqual(title_candidates.expected_ctr(1.5), (0.2795 + 0.1525) / 2)
        self.assertEqual(title_candidates.expected_ctr(14), 0.0258)

    def test_month_windows_cover_range(self):
        w = list(month_windows(date(2026, 1, 15), date(2026, 3, 2)))
        self.assertEqual(w[0], (date(2026, 1, 15), date(2026, 1, 31)))
        self.assertEqual(w[-1], (date(2026, 3, 1), date(2026, 3, 2)))

    def test_demo_picks_the_underperformers(self):
        picks = make_demo.main()
        pages = {p["page"].rsplit("/", 1)[1] for p in picks}
        for weak in ("fsa-vs-hsa", "dependent-care-fsa", "lpfsa"):
            self.assertIn(weak, pages)
        self.assertTrue(all(p["ctr"] < p["expected_ctr"] for p in picks))

    def test_reload_is_idempotent(self):
        make_demo.main()
        from schema import connect
        con = connect(read_only=True)
        n1 = con.execute("select count(*) from gsc_page_query").fetchone()[0]
        con.close()
        make_demo.main()
        con = connect(read_only=True)
        n2 = con.execute("select count(*) from gsc_page_query").fetchone()[0]
        con.close()
        self.assertEqual(n1, n2)


if __name__ == "__main__":
    unittest.main()
