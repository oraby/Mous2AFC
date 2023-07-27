import os
from pathlib import Path

def getFilesWithExt(top_dir, files_ext):
  matches = []
  for root, dirnames, filenames in os.walk(str(top_dir)):
    for _dir in dirnames:
      matches += getFilesWithExt(_dir, files_ext)
    for filename in filenames:
      full_path = os.path.join(root, filename)
      if full_path.endswith(files_ext):
        matches.append(Path(os.path.join(root, filename)))
  return matches
