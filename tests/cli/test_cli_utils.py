from pathlib import Path
import pytest
from click.exceptions import BadParameter
from bigquery_etl.cli.utils import is_valid_dir, is_valid_file, is_authenticated


TEST_DIR = Path(__file__).parent.parent


class TestUtils:
    def test_is_valid_dir(self):
        with pytest.raises(BadParameter):
            assert is_valid_dir(None, None, "invalid")
        with pytest.raises(BadParameter):
            assert is_valid_dir(None, None, str(TEST_DIR / "data" / "dags.yaml"))
        assert is_valid_dir(None, None, str(TEST_DIR)) == str(TEST_DIR)

    def test_is_valid_file(self):
        with pytest.raises(BadParameter):
            assert is_valid_file(None, None, "invalid")
        with pytest.raises(BadParameter):
            assert is_valid_file(None, None, str(TEST_DIR))
        assert is_valid_file(None, None, str(TEST_DIR / "data" / "dags.yaml")) == str(
            TEST_DIR / "data" / "dags.yaml"
        )

    def test_is_authenticated(self):
        assert is_authenticated("non-existing-project") is False
