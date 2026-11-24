from pathlib import Path


MAX_CONTEXT_BYTES = 64 * 1024
MAX_OUTPUT_BYTES = 1024 * 1024


class WorkspaceError(ValueError):
    """A selected path or file operation is not allowed."""


class Workspace:
    def __init__(self, root: str | Path):
        try:
            resolved_root = Path(root).expanduser().resolve(strict=True)
        except OSError as exc:
            raise WorkspaceError("The workspace folder could not be opened.") from exc
        if not resolved_root.is_dir():
            raise WorkspaceError("The workspace path is not a directory.")
        self.root = resolved_root

    def _resolve(self, path: str | Path, *, strict: bool) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate
        try:
            resolved = candidate.resolve(strict=strict)
            resolved.relative_to(self.root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise WorkspaceError("Choose a path inside the selected workspace.") from exc
        return resolved

    def read_selected_file(self, path: str | Path) -> tuple[str, str]:
        target = self._resolve(path, strict=True)
        if not target.is_file():
            raise WorkspaceError("The selected path is not a regular file.")
        try:
            with target.open("rb") as source:
                contents = source.read(MAX_CONTEXT_BYTES + 1)
            if len(contents) > MAX_CONTEXT_BYTES:
                raise WorkspaceError("Selected files must be 64 KiB or smaller.")
            text = contents.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceError("The selected file is not UTF-8 text.") from exc
        except OSError as exc:
            raise WorkspaceError("The selected file could not be read.") from exc
        return target.relative_to(self.root).as_posix(), text

    def save_new_file(self, path: str | Path, text: str) -> str:
        target = self._resolve(path, strict=False)
        if not target.name or target.name in {".", ".."}:
            raise WorkspaceError("Choose a file name inside the selected workspace.")
        try:
            target.parent.resolve(strict=True).relative_to(self.root)
        except (OSError, ValueError) as exc:
            raise WorkspaceError("The destination folder must exist inside the workspace.") from exc

        try:
            payload = text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise WorkspaceError("The response contains text that cannot be saved as UTF-8.") from exc
        if len(payload) > MAX_OUTPUT_BYTES:
            raise WorkspaceError("Responses must be 1 MiB or smaller to save.")
        try:
            with target.open("x", encoding="utf-8", newline="\n") as output:
                output.write(text)
        except FileExistsError as exc:
            raise WorkspaceError("That file already exists; choose a new name.") from exc
        except OSError as exc:
            raise WorkspaceError("The response file could not be created.") from exc
        return target.relative_to(self.root).as_posix()
