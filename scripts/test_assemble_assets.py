import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("assemble", Path(__file__).with_name("assemble-assets.py"))
assemble = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assemble)


def release(identifier, published, *names, **flags):
    return {
        "id": identifier,
        "published_at": published,
        "tag_name": f"release-{identifier}",
        "draft": False,
        "prerelease": False,
        "assets": [{"name": name} for name in names],
        **flags,
    }


class SelectionTests(unittest.TestCase):
    def test_newest_per_archive_and_deletion_fallback(self):
        older = release(1, "2026-01-01T00:00:00Z", "surge.tar.gz", "foo.tar.gz")
        newer = release(2, "2026-02-01T00:00:00Z", "surge.tar.gz")
        selected = assemble.select_archives([older, newer])
        self.assertEqual(selected["surge"][0], newer)
        self.assertEqual(selected["foo"][0], older)
        self.assertEqual(assemble.select_archives([older])["surge"][0], older)
        self.assertEqual(set(assemble.select_archives([newer])), {"surge"})

    def test_publication_date_wins_over_id_and_input_order(self):
        recent = release(1, "2026-02-01T00:00:00Z", "surge.tar.gz")
        old = release(2, "2026-01-01T00:00:00Z", "surge.tar.gz")
        self.assertEqual(assemble.select_archives([old, recent])["surge"][0], recent)

    def test_ignores_drafts_prereleases_and_other_attachments(self):
        self.assertEqual(assemble.select_archives([
            release(1, None, "surge.tar.gz", draft=True),
            release(2, "2026-02-01T00:00:00Z", "surge.tar.gz", prerelease=True),
            release(3, "2026-03-01T00:00:00Z", "figure.webp", "SHA256SUMS"),
        ]), {})

    def test_invalid_root(self):
        with self.assertRaises(ValueError):
            assemble.select_archives([release(1, "2026-01-01T00:00:00Z", "../surge.tar.gz")])


class ExtractionTests(unittest.TestCase):
    def test_preserves_directories_and_rejects_escaping_paths_and_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, kind in [
                ("pointmaps/example.json", tarfile.REGTYPE),
                ("../outside", tarfile.REGTYPE),
                ("/absolute", tarfile.REGTYPE),
                ("link", tarfile.SYMTYPE),
                ("hardlink", tarfile.LNKTYPE),
            ]:
                with self.subTest(name=name):
                    with tarfile.open(root / "test.tar.gz", "w:gz") as archive:
                        member = tarfile.TarInfo(name)
                        member.type = kind
                        member.size = 2 if kind == tarfile.REGTYPE else 0
                        member.linkname = "../outside" if kind != tarfile.REGTYPE else ""
                        archive.addfile(member, io.BytesIO(b"{}"))
                    if name == "pointmaps/example.json":
                        assemble.extract_archive(root / "test.tar.gz", root / "surge")
                        self.assertEqual((root / "surge" / name).read_text(), "{}")
                    else:
                        with self.assertRaises(ValueError):
                            assemble.extract_archive(root / "test.tar.gz", root / "surge")


if __name__ == "__main__":
    unittest.main()
