from pathlib import Path
import unittest


class ProductBoundaryTests(unittest.TestCase):
    def test_runtime_source_has_no_sibling_bot_dependency(self):
        root = Path(__file__).resolve().parents[1]
        source = "\n".join(path.read_text(encoding="utf-8") for path in (root / "src").rglob("*.py"))
        forbidden = (
            "crypto-news-radar",
            "Flow-Squeeze-Bot",
            "PressureBot/data",
            "BreakerBot",
            "MockingBot-fixed",
        )
        for marker in forbidden:
            self.assertNotIn(marker, source, f"unexpected sibling dependency: {marker}")


if __name__ == "__main__":
    unittest.main()
