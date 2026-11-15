"""Where the app keeps its data when no environment variable says otherwise."""

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


def test_a_new_computer_gets_the_new_folder(tmp_path):
    expected = tmp_path / "SyncThing" / "Balance Streamer Application"
    assert paths.default_data_dir(str(tmp_path)) == str(expected)
