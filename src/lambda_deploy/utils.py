import shutil
import tempfile
import contextlib


@contextlib.contextmanager
def TemporaryDirectory():
		temporary_dir = tempfile.mkdtemp()
		try:
				yield temporary_dir
		finally:
				shutil.rmtree(temporary_dir)
