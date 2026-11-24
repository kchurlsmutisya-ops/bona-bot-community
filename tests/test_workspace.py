import tempfile
import unittest
from pathlib import Path

from bona_bot.workspace import Workspace, WorkspaceError


class WorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.workspace = Workspace(self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_reads_only_a_selected_utf8_file_inside_workspace(self) -> None:
        selected = self.root / "example.py"
        selected.write_bytes(b"print('hello')\n")

        relative_path, text = self.workspace.read_selected_file(selected)

        self.assertEqual(relative_path, "example.py")
        self.assertEqual(text, "print('hello')\n")

    def test_rejects_paths_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            with self.assertRaises(WorkspaceError):
                self.workspace.read_selected_file(Path(outside) / "secret.txt")

    def test_rejects_oversized_selected_file(self) -> None:
        selected = self.root / "large.txt"
        selected.write_bytes(b"x" * (64 * 1024 + 1))

        with self.assertRaisesRegex(WorkspaceError, "64 KiB"):
            self.workspace.read_selected_file(selected)

    def test_save_creates_new_file_but_never_overwrites(self) -> None:
        created = self.workspace.save_new_file("draft.py", "print('safe')\n")
        self.assertEqual(created, "draft.py")
        self.assertEqual((self.root / "draft.py").read_text(encoding="utf-8"), "print('safe')\n")

        with self.assertRaisesRegex(WorkspaceError, "already exists"):
            self.workspace.save_new_file("draft.py", "different content")

    def test_rejects_nonexistent_destination_folder(self) -> None:
        with self.assertRaises(WorkspaceError):
            self.workspace.save_new_file("missing/draft.py", "content")


if __name__ == "__main__":
    unittest.main()
