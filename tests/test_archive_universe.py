import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from trendbot.archive_universe import (
    ArchiveCatalog,
    catalog_from_keys,
    parse_listing_page,
    parse_prefix_page,
)


class ArchiveUniverseTests(unittest.TestCase):
    def test_listing_parser_preserves_continuation(self):
        xml = b"""<?xml version='1.0' encoding='UTF-8'?>
        <ListBucketResult xmlns='http://s3.amazonaws.com/doc/2006-03-01/'>
          <IsTruncated>true</IsTruncated>
          <Contents><Key>first</Key></Contents>
          <Contents><Key>second</Key></Contents>
          <NextContinuationToken>next-token</NextContinuationToken>
        </ListBucketResult>"""
        keys, token = parse_listing_page(xml)
        self.assertEqual(keys, ["first", "second"])
        self.assertEqual(token, "next-token")

    def test_catalog_keeps_delisted_symbol_history(self):
        prefix = "data/futures/um/monthly/klines"
        keys = [
            f"{prefix}/BTCUSDT/1d/BTCUSDT-1d-2024-01.zip",
            f"{prefix}/OLDUSDT/1d/OLDUSDT-1d-2021-01.zip",
            f"{prefix}/OLDUSDT/1d/OLDUSDT-1d-2021-02.zip",
            f"{prefix}/OLDUSDT/4h/OLDUSDT-4h-2021-02.zip",
            "irrelevant/file.zip",
        ]
        catalog = catalog_from_keys(keys)
        self.assertEqual(catalog.symbols, ("BTCUSDT", "OLDUSDT"))
        selected = catalog.select(date(2021, 1, 1), date(2021, 12, 31))
        self.assertEqual({entry.symbol for entry in selected}, {"OLDUSDT"})

    def test_prefix_parser_returns_symbol_directories(self):
        xml = b"""<ListBucketResult xmlns='http://s3.amazonaws.com/doc/2006-03-01/'>
          <IsTruncated>false</IsTruncated>
          <CommonPrefixes><Prefix>data/klines/BTCUSDT/</Prefix></CommonPrefixes>
          <CommonPrefixes><Prefix>data/klines/OLDUSDT/</Prefix></CommonPrefixes>
        </ListBucketResult>"""
        prefixes, token = parse_prefix_page(xml)
        self.assertEqual(prefixes, ["data/klines/BTCUSDT/", "data/klines/OLDUSDT/"])
        self.assertIsNone(token)

    def test_catalog_round_trip_is_reproducible(self):
        key = "data/futures/um/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2024-01.zip"
        catalog = catalog_from_keys([key])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            catalog.write(path)
            loaded = ArchiveCatalog.read(path)
        self.assertEqual(catalog, loaded)
        self.assertEqual(json.loads(path.read_text()) if path.exists() else None, None)


if __name__ == "__main__":
    unittest.main()
