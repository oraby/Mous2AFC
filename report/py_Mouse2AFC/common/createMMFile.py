import mmap
import os

def createMMFile(fpath, fsize):
  '''Opens or creates a memory mapped file fpath with size of fsize. '''
  # Create the communications file if it is not already there.
  exists = os.path.exists(fpath)
  f = open(fpath, "r+b" if exists else "w+b")
  if not exists: # Create buffer
    f.write(bytearray([0]*fsize))
    f.flush()
    f.seek(0)
  # memory-map the file, size 0 means whole file
  m = mmap.mmap(f.fileno(), 0)
  return m
