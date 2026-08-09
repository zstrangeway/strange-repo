import unittest
from unittest.mock import patch

from gary_api import main


class MainTests(unittest.TestCase):
    def test_starts_uvicorn_with_the_app(self):
        with patch("uvicorn.run") as run:
            main()

        run.assert_called_once_with(
            "gary_api.app:app", host="127.0.0.1", port=8000, reload=True
        )


if __name__ == "__main__":
    unittest.main()
