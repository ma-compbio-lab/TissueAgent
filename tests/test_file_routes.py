"""Regression tests for file API path boundaries and bounded uploads."""

from __future__ import annotations

import os
import sys
import asyncio
from pathlib import Path
from tempfile import SpooledTemporaryFile

import pytest
from fastapi import HTTPException, UploadFile

os.environ.setdefault("OPENAI_API_KEY", "dummy")
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from server.routes import files  # noqa: E402
from server.session_manager import session  # noqa: E402


@pytest.fixture
def file_api(tmp_path, monkeypatch):
    """Point file route handlers at an isolated temporary workspace."""
    workspace = tmp_path / "workspace"
    project = workspace / "project"
    library = workspace / "library"
    for path in (project / "uploads", project / "outputs", library / "datasets", library / "files"):
        path.mkdir(parents=True)

    monkeypatch.setattr(files, "ACTIVE_PROJECT_DIR", project)
    monkeypatch.setattr(files, "LIBRARY_DIR", library)
    monkeypatch.setattr(files, "DATASET_DIR", library / "datasets")
    monkeypatch.setattr(files, "LIBRARY_FILES_DIR", library / "files")
    monkeypatch.setattr(session, "project_id", "test-project")
    monkeypatch.setattr(session, "pending_images", [])
    monkeypatch.setattr(session, "uploaded_pdfs", [])

    return workspace, project, library


def _upload(filename: str, data: bytes, target: str = "project"):
    """Run the upload handler with a multipart-style file object."""
    file = SpooledTemporaryFile()
    file.write(data)
    file.seek(0)
    upload = UploadFile(file=file, filename=filename)
    return asyncio.run(files.upload_files([upload], target=target))


@pytest.mark.parametrize(
    "filename",
    ["../escape.csv", "/tmp/escape.csv", "sub/file.csv", "sub\\file.csv", ".", "bad\nname.csv"],
)
def test_upload_rejects_unsafe_names(file_api, filename):
    """Multipart filenames cannot select a directory or contain control characters."""
    workspace, project, _ = file_api
    with pytest.raises(HTTPException) as exc:
        _upload(filename, b"data")
    assert exc.value.status_code == 400
    assert not (project / "uploads" / "escape.csv").exists()
    assert not (workspace / "escape.csv").exists()


def test_upload_streams_and_removes_oversize_partial_file(file_api, monkeypatch):
    """Over-limit uploads receive 413 and leave no partial file behind."""
    _, project, _ = file_api
    monkeypatch.setenv("TISSUEAGENT_MAX_UPLOAD_BYTES", "5")
    with pytest.raises(HTTPException) as exc:
        _upload("large.csv", b"123456")
    assert exc.value.status_code == 413
    assert not (project / "uploads" / "large.csv").exists()

    result = _upload("small.csv", b"12345")
    assert result.files[0].name == "small.csv"
    assert (project / "uploads" / "small.csv").read_bytes() == b"12345"


def test_upload_never_follows_dangling_symlink(file_api):
    """A dangling destination symlink is treated as occupied."""
    workspace, project, _ = file_api
    (project / "uploads" / "link.csv").symlink_to(workspace / "secret.csv")
    result = _upload("link.csv", b"safe")
    assert result.files[0].name == "link.csv"
    assert not (workspace / "secret.csv").exists()
    assert (project / "uploads" / "link_1.csv").read_bytes() == b"safe"


def test_library_upload_stays_in_library(file_api):
    """Library uploads use the same filename checks and streaming writer."""
    _, _, library = file_api
    result = _upload("reference.csv", b"gene,count\nA,1", target="library")
    assert result.files[0].category == "dataset"
    assert (library / "datasets" / "reference.csv").read_bytes() == b"gene,count\nA,1"

    with pytest.raises(HTTPException) as exc:
        _upload("../escape.csv", b"data", target="library")
    assert exc.value.status_code == 400


def test_file_scope_rejects_workspace_and_internal_paths(file_api):
    """Only library/project files can be browsed, downloaded, or deleted."""
    _, project, _ = file_api
    (project / ".chat.json").write_text("private")
    (project / "outputs" / "result.txt").write_text("public")

    for handler, args in (
        (files.browse_files, ("all",)),
        (files.download_file, ("project/.chat.json", "all")),
        (files.delete_file, ("project", "all")),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(handler(*args))
        assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        asyncio.run(files.download_file(".chat.json", scope="project"))
    assert exc.value.status_code == 403
    response = asyncio.run(files.download_file("outputs/result.txt", scope="project"))
    assert Path(response.path) == project / "outputs" / "result.txt"

    (project / "outputs" / "chat-link.json").symlink_to(project / ".chat.json")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(files.download_file("outputs/chat-link.json", scope="project"))
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        files._resolve_scoped_path("project", "outputs/../.chat.json", "test-project")
    assert exc.value.status_code == 400


def test_delete_can_remove_scoped_subdirectory_but_not_root(file_api):
    """Scoped directories can be removed without exposing the workspace root."""
    _, project, library = file_api
    nested = project / "outputs" / "scratch"
    nested.mkdir()
    (nested / "result.txt").write_text("data")

    result = asyncio.run(files.delete_file("outputs/scratch", scope="project"))
    assert result["status"] == "deleted"
    assert not nested.exists()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(files.delete_file(".", scope="library"))
    assert exc.value.status_code == 400
    assert library.exists()
