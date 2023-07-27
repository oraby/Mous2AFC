from sys import argv
import click
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
import subprocess
import os
import pandas as pd
from pathlib import Path
import time
from .matreader.utils import getFilesWithExt
from .mat_reader_core import reduceTypes, MIN_DF_COLS_DROP, IMP_GUI_COLS

DEFAULT_DIR=r"C:\BpodUser\Data"
AGGREGATES_DIR=r"C:\BpodUser\Data\Aggregates"

def spawnProcess(animal_name, mat_files, savedir):
  # https://stackoverflow.com/a/39375937/11996983
  input_files = [el for _file in mat_files for el in ('-i', str(_file))]
  if not len(input_files):
    return
  pkl_file = Path(f"{savedir}/{animal_name}.pkl")
  append_df_arg = ["--append-df" if pkl_file.exists() else "--out",
                   str(pkl_file)]
  few_trials_file = Path(f"{savedir}/few_trials/{animal_name}.txt")
  if few_trials_file.exists():
    few_trials_load_arg = ["--few-trials-load", str(few_trials_file)]
  else:
    few_trials_load_arg = []
  # Add "echo" as first arg to see the ran command
  p = subprocess.Popen(args=["python", "toplevelrunner.py",
                            f"{Path(argv[0]).parent}{os.path.sep}mat_reader.py",
                             "--full-df",
                             "--few-trials-save", str(few_trials_file)] +\
                            input_files + append_df_arg + few_trials_load_arg,
                      shell=False)
  p.wait()

def concatDfs(savedir, savename, animals_names):
  filenames = [Path(f"{savedir}/{name}.pkl") for name in animals_names]
  filenames = list(filter(lambda f:f.exists(), filenames))
  all_df = []
  for file_path in filenames: # Should we used threadpool here?
      file_path = str(file_path)
      print("Loading", file_path, "dataframe")
      # We can easily run out of memory, try to reduce size once loaded
      def loadDF(file_path):
        df = reduceTypes(pd.read_pickle(file_path))
        cols_to_keep = list(filter(
          lambda col:col not in MIN_DF_COLS_DROP and
                     (not col.startswith("GUI_") or col in IMP_GUI_COLS),
          df.columns))
        # Hopefully copying would make the original disappear
        return df[cols_to_keep].copy()
      all_df.append(loadDF(file_path))

  # Suppress concat() warning and disable sort, we will sort later
  all_df = pd.concat(all_df, ignore_index=True, sort=False)
  # Should we try to reduce again?
  print("Reassigning dataframe types to reduce memory usage...")
  all_df = reduceTypes(all_df, debug=True)
  print("all_df.info:")
  all_df.info()
  all_df.sort_values(["Name","Date","SessionNum","TrialNumber"], inplace=True)
  all_df.reset_index(drop=True)
  output_path = Path(f"{savedir}/{savename}_{time.strftime('_%Y_%m_%d')}.pkl")
  print("Saving to a single dataframe:", output_path)
  all_df.to_pickle(output_path)

def batchConvert(dir_path, savedir, savename, only=[], exclude=[]):
  animal_to_files = {}
  skip_animals = ("Dummy", "Fake", "Home")
  for entry in getFilesWithExt(dir_path, "mat"):
    if str(entry.name).lower().startswith("temp") or \
       str(entry.parent.name) != "Session Data" or \
       str(entry.parent.parent.name) != "Mouse2AFC" or \
       str(entry.parent.parent.parent.name).startswith(skip_animals):
      continue
    if len(only) and not any(filter(lambda kw: kw in str(entry), only)):
      continue
    if any(filter(lambda kw: kw in str(entry), exclude)):
      continue
    animal_name = entry.parent.parent.parent.name
    li = animal_to_files.get(animal_name, [])
    li.append(entry)
    animal_to_files[animal_name] = li
  print(f"Found: {animal_to_files}")

  num_cpus = max(1, cpu_count() - 3)
  tp = ThreadPool(num_cpus)
  running_threads = []
  for animal_name, animals_files in animal_to_files.items():
    running_threads.append(
          tp.apply_async(spawnProcess, (animal_name, animals_files, savedir,)))

  active_theads = len(list(filter(lambda r:not r.ready(), running_threads)))
  done = len(running_threads) - active_theads
  while active_theads > 0:
    print(f"Finished subprocesses: {done}/{len(running_threads)}")
    time.sleep(0.5)
    active_theads = len(list(filter(lambda r:not r.ready(), running_threads)))
    done = len(running_threads) - active_theads
  print(f"Finished subprocesses: {done}/{len(running_threads)}")
  tp.close()
  tp.join()
  if len(animal_to_files) > 1:
    concatDfs(savedir, savename, list(animal_to_files.keys()))

@click.command()
@click.option('--dir', '-d', type=click.Path(exists=True), default=DEFAULT_DIR,
              help="The directory containing the sessions files")
@click.option('--savedir','-s', type=click.Path(exists=True),
              default=AGGREGATES_DIR,
              help="The directory containing the serialized data frames")
@click.option('--savename','-o', type=click.Path(), default="AllAnimals",
              help="The final dataframe name. This will only be created if "
                   "more than one animal was found.")
@click.option('--only', '-i', multiple=True,
              help="If specified, then only paths contains that string will be"+
                   "included")
@click.option('--exclude', '-x', multiple=True,
              help="Paths containing such string(s) will be excluded")
def main(dir, savedir, savename, only, exclude):
  #concatDfs()s
  if only is None: only = []
  if exclude is None: exclude = []
  batchConvert(dir, savedir, savename, only, exclude)

if __name__ == "__main__":
  main()