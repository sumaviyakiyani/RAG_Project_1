from pathlib import Path

import pytest

from evals import run_eval
from tests.conftest import make_pdf


@pytest.mark.parametrize(
    "dataset, raises",
    [
        ([], False),
        ([{"id": "bad", "answerable": False, "question": None}], True),
    ],
)
def test_run_config_closes_temporary_chroma_store(dataset, raises, tmp_path, monkeypatch):
    corpus_file = tmp_path / "source.pdf"
    corpus_file.write_bytes(make_pdf(["Vector store cleanup regression fixture."]))

    original_build_services = run_eval.build_services

    def build_hash_services(settings):
        return original_build_services(settings.model_copy(update={"embedding_backend": "hash"}))

    monkeypatch.setattr(run_eval, "build_services", build_hash_services)

    real_temporary_directory = run_eval.tempfile.TemporaryDirectory
    temp_paths = []
    index_files_present_at_cleanup = []

    class TrackedTemporaryDirectory:
        def __init__(self, *args, **kwargs):
            self._manager = real_temporary_directory(*args, **kwargs)
            self.name = self._manager.name
            temp_paths.append(Path(self.name))

        def __enter__(self):
            return self._manager.__enter__()

        def __exit__(self, exc_type, exc_value, traceback):
            index_files_present_at_cleanup.append(
                any(Path(self.name).rglob("data_level0.bin")))
            return self._manager.__exit__(exc_type, exc_value, traceback)

    monkeypatch.setattr(run_eval.tempfile, "TemporaryDirectory", TrackedTemporaryDirectory)

    config = {
        "chunk_size": 500,
        "chunk_overlap": 50,
        "top_k": 5,
        "embedding_model": "unused-by-hash-embedder",
    }

    if raises:
        with pytest.raises(AttributeError):
            run_eval.run_config(config, dataset, [corpus_file], skip_llm=True)
    else:
        run_eval.run_config(config, dataset, [corpus_file], skip_llm=True)

    assert index_files_present_at_cleanup == [True]
    assert len(temp_paths) == 1
    assert not temp_paths[0].exists()
