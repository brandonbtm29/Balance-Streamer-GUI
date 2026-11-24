"""Where the app keeps its data when no environment variable says otherwise."""

import os

from balance_streamer import paths


def test_uses_its_own_syncthing_folder(tmp_path):
    new = tmp_path / "SyncThing" / "Balance Streamer Application"
    new.mkdir(parents=True)
    (tmp_path / "SyncThing" / "UAkron Playground" / "Balance Streamer Application").mkdir(parents=True)
    assert paths.default_data_dir(str(tmp_path)) == str(new)


def test_keeps_the_old_shared_folder_until_the_new_one_arrives(tmp_path):
    old = tmp_path / "SyncThing" / "UAkron Playground" / "Balance Streamer Application"
    old.mkdir(parents=True)
    assert paths.default_data_dir(str(tmp_path)) == str(old)


def test_a_computer_without_the_syncthing_folder_uses_documents(tmp_path):
    (tmp_path / "SyncThing").mkdir()  # Syncthing, but not this app's folder (yet)
    expected = tmp_path / "Documents" / "Balance Streamer"
    assert paths.default_data_dir(str(tmp_path)) == str(expected)


def test_documents_folder(tmp_path):
    assert paths.documents_folder(str(tmp_path)) == os.path.join(str(tmp_path), "Documents")
    assert os.path.isabs(paths.documents_folder())  # this computer's own (on Windows, from the registry)


def test_settings_show_the_data_folder_and_the_syncthing_note(window):
    settings = window.settings_tab
    assert settings.lbl_data_folder.text() == paths.DATA_DIR
    assert "Syncthing" in settings.lbl_data_note.text()
