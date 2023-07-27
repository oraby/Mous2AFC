import inspect
from report.utils import grpBySess
from report.definitions import BrainRegion, MatrixState

class ChainedGrpBy:
  def __init__(self, df, descr=None):
    if not isinstance(df, (tuple, list)):
      self._df_tups = df
      self.descr = ((),)[0]
    else:
      self._df_tups = tuple(df)
      self.descr = descr

  def __len__(self):
    return len(self._df_tups)

  def __iter__(self):
    return ChainedGrpBy.Iterator(self)

  class Iterator:
    def __init__(self, outer):
      self._outer = outer
      self._idx = -1

    def __next__(self):
      self._idx += 1
      if self._idx == len(self._outer._df_tups):
        raise StopIteration
      # will return info, df
      key, val = self._outer._df_tups[self._idx]
      if len(key) == 1: key = key[0]
      return key, val


  def toDF(self):
    if len(self._df_tups) == 1: # It's a dataframe
      # print(self._df_tups)
      return self._df_tups[0][1]
    else:
        print(self._df_tups)
        raise Exception(f"Too many dataframes")


  def _processBy(self, processFn, descr_str):
    #TODO: This pattern is probably over complicated, find a simpler solution
    res_list = []
    df_info = None # Will be changed down
    def addGrpByTupFn(grp_key, grp_df):
      final_key = *df_info, grp_key
      res_list.append((final_key, grp_df))

    if not isinstance(self._df_tups, tuple):
      df_info = ((),)[0]
      processFn(self._df_tups, addGrpByTupFn)
    else:
      for _df_info, sub_df in self._df_tups:
        df_info = _df_info
        processFn(sub_df, addGrpByTupFn)

    new_descr = *self.descr, descr_str
    return ChainedGrpBy(df=res_list, descr=new_descr)

  # def _by(self, grpbyCriteriaFn, infoConvertFn, descr_str):
  #   def processComb(_df, addGrpByTupFn):
  #     for grpby_info, grpby_df in _df.groupby(grpbyCriteriaFn(_df)):
  #       addGrpByTupFn(infoConvertFn(grpby_info), grpby_df)
  #   return self._processBy(processComb, descr_str)

  def bySess(self):
    def processComb(_df, addGrpByTupFn):
      for grpby_info, grpby_df in _df.groupby(["Name", "Date", "SessionNum"]):
        date = grpby_info[1].strftime(r"%y-%m-%d")
        info = f"{grpby_info[0]} - {date} /{grpby_info[2]}"
        addGrpByTupFn(info, grpby_df)
    return self._processBy(processComb, descr_str="Session")

  def byBrainRegion(self):
    def processComb(_df, addGrpByTupFn):
      for grpby_info, grpby_df in _df.groupby(["GUI_OptoBrainRegion"]):
        addGrpByTupFn(BrainRegion(grpby_info), grpby_df)
    return self._processBy(processComb, descr_str="BrainRegion")

  # def byState(self):
  #   def processComb(_df, addGrpByTupFn):
  #     for grpby_info, grpby_df in _df.groupby(["GUI_OptoStartState1"]):
  #       addGrpByTupFn(MatrixState(grpby_info), grpby_df)
  #   return self._processBy(processComb, descr_str="StartState")

  def byOptoConfig(self):
    # We need to call splitByOptoTiming() to get us the results
    def processComb(_df, addGrpByTupFn):
      for config_tup, grpby_df in splitByOptoTiming(_df):
        info = (MatrixState(config_tup[0]), config_tup[1], config_tup[2])
        addGrpByTupFn(info, grpby_df)
    return self._processBy(processComb, "OptoConfig")

  def byOptoTrials(self):
    def processComb(_df, addGrpByTupFn):
      for is_opto_enabled, grpby_df in _df.groupby(["OptoEnabled"]):
        grpby_info = "Opto" if is_opto_enabled == True else "Control"
        addGrpByTupFn(grpby_info, grpby_df)
    return self._processBy(processComb, descr_str="OptoTrials")

  def byAnimal(self):
    def processComb(_df, addGrpByTupFn):
      for grpby_info, grpby_df in _df.groupby(["Name"]):
        addGrpByTupFn(grpby_info, grpby_df)
    return self._processBy(processComb, descr_str="Animal")


  def filter(self, filterFn, *fnArgs):
    new_list = []
    info_sig = inspect.signature(filterFn).parameters.get("df_info", None)
    if info_sig and info_sig.kind == inspect.Parameter.KEYWORD_ONLY:
      wrapFn = filterFn
    else:
      def wrapFn(_df, *args, df_info=None): # df_info is ignored
        return filterFn(_df, *args)

    def processDf(_df_info, _df):
      if len(_df_info) == 1: _df_info = _df_info[0]
      if wrapFn(_df, *fnArgs, df_info=_df_info):
        new_list.append((_df_info, _df))

    if not isinstance(self._df_tups, tuple):
      empty_tup = ((),)[0]
      processDf(empty_tup, self._df_tups)
    else:
      for df_info, sub_df in self._df_tups:
        processDf(df_info, sub_df)
    return ChainedGrpBy(df=new_list, descr=self.descr)


def splitToControlOpto(df):
  df_opto = df[df.OptoEnabled == 1]
  df_control = df[df.OptoEnabled == 0]
  return df_control, df_opto

def optoConfigStr(state, start, dur):
  dur = "Full" if dur == -1 else f"{dur}s"
  return f"{state} S={start}s, T={dur}"

def filterNonOptoSessions(df):
  # Turn opto trials with zero light-time into non-opto trials
  df.loc[(df.OptoEnabled == True) & (df.GUI_OptoMaxTime == 0),
         'OptoEnabled'] = False
  opto_sessions = df[df.OptoEnabled == True]
  opto_sessions = opto_sessions[['Date','SessionNum']].drop_duplicates()
  opto_sessions_tuples = [tuple(x) for x in opto_sessions.to_numpy()]
  # print("Opto sessions dates:", opto_sessions_tuples)
  # Filter on sessions matching Data/Session Num combination:
  # https://stackoverflow.com/a/53945974/11996983
  idx_bool = df[["Date", "SessionNum"]].apply(tuple, axis=1).isin(
                                                           opto_sessions_tuples)
  return df[idx_bool]

def grpByOptoConfig(df):
  opto_config_cols = ['GUI_OptoStartState1', 'GUI_OptoStartDelay',
                      'GUI_OptoMaxTime']
  return df.groupby(opto_config_cols)

def optoCOnfigsCounts(df):
  grp_by_opto = grpByOptoConfig(df).size()
  # grp_by_opto is currently a multi-index series, convert to single-index
  # dataframe
  df_grp_by_opto_count = grp_by_opto.to_frame("Count").reset_index()
  return df_grp_by_opto_count

def filterFewTrialsCombinations(df, *, config_min_num_trials, _second_df=None):
  if _second_df is None:
    _second_df = df
  df_opto_configs_counts = optoCOnfigsCounts(_second_df)
  df_opto_configs_counts = df_opto_configs_counts[
                  df_opto_configs_counts.Count > config_min_num_trials]
  opto_config_cols = list(df_opto_configs_counts.columns)
  opto_config_cols.remove("Count") # Remove the irrelevant count column
  # Use the trick here: https://stackoverflow.com/a/33282617/11996983
  i1 = df.set_index(opto_config_cols).index
  i2 = df_opto_configs_counts.set_index(opto_config_cols).index
  return df[i1.isin(i2)]

def filterNoOptoConfigs(df):
  df_opto = df[df.OptoEnabled == True]
  # Should we do it here by brain region and animal as well?
  # Use a workaround
  return filterFewTrialsCombinations(df, config_min_num_trials=0,
                                     _second_df=df_opto)

def splitByBinarySamplingTime(df):
  # Get all opto trials during sampling phase
  from report.definitions import MatrixState
  df_stim_delv = df[df.GUI_OptoStartState1 ==
                    int(MatrixState.stimulus_delivery)]
  # Filter for trials where opto was triggered after 0 second or was triggered
  # at zero second but didn't last the whole of sampling period. Here,
  # min-sampling should be the same as max allowed sampling.
  df_partial_sampling = \
         df_stim_delv[(df_stim_delv.GUI_OptoStartDelay > 0) |
                      ((df_stim_delv.GUI_OptoStartDelay == 0) &
                       (df_stim_delv.GUI_OptoMaxTime < df_stim_delv.MinSample))]
  # All the other trials that had opto throughout the whole epoch
  df_full_sampling = df[~df.index.isin(df_partial_sampling.index)]
  # if hasattr(builtins, "display"):
  #   print("Partial sampling df:")
  #   display(optoCOnfigsCounts(df_partial_sampling))
  #   print("Full Sampling df:")
  #   display(optoCOnfigsCounts(df_full_sampling))
  return df_full_sampling, df_partial_sampling

def splitByOptoTiming(df):
  df_full_sampling, df_partial_sampling = splitByBinarySamplingTime(df)
  grps_concat = []
  START_DELAY=0
  MAX_DUR=-1
  for grp_key, grp_df in df_full_sampling.groupby("GUI_OptoStartState1"):
    grp_key = (grp_key, START_DELAY, MAX_DUR,)
    grps_concat.append((grp_key, grp_df,))
  for grp_key, grp_df in grpByOptoConfig(df_partial_sampling):
    start_state, start_delay, max_dur = grp_key
    # if start_state == int(MatrixState.stimulus_delivery):
    #   unique_min_sample = grp_df.MinSample.unique()
    #   # if len(unique_min_sample) == 1 and unique_min_sample == 1:
    #   #   max_dur = MAX_DUR
    #   #   grp_key = (start_state, start_delay, max_dur)
    grps_concat.append((grp_key, grp_df,))
  # Sort by early, full, then late
  grps_concat = sorted(grps_concat,
                       key=lambda entry:(entry[0][0],entry[0][1],-entry[0][2]))
  return grps_concat

# def filterBadCntrlPerformanceSsns(df):
#   used_sessions = []
#   for ssn_info, ssn_df in grpBySess(df):
#     cntrl_df = ssn_df[ssn_df.OptoEnabled == 0]
#     if len(cntrl_df) == len(ssn_df): # No opto trials
#       continue
#     easy_trials = cntrl_df[cntrl_df.DV.abs()*100 == cntrl_df.Difficulty1]
#     l_easy = easy_trials[easy_trials.LeftRewarded == 1]
#     r_easy = easy_trials[easy_trials.LeftRewarded == 0]
#     if not len(l_easy) or not len(r_easy):
#       continue
#     if l_easy.ChoiceCorrect.mean() < 0.8 or r_easy.ChoiceCorrect.mean() < 0.8:
#       continue
#     used_sessions.append(ssn_df)
#   import pandas as pd
#   if len(used_sessions):
#     return pd.concat(used_sessions)
#   else:
#     return pd.DataFrame(columns=df.columns)

def commonOptoSectionFilter(df, *, by_session, by_animal):
  MIN_NUM_TRIALS_PER_STATE = 50
  MIN_NUM_TRIALS_PER_SESS = 20
  # df = filterBadCntrlPerformanceSsns(df)
  if by_session:
    assert by_animal
  min_choice_trials = MIN_NUM_TRIALS_PER_SESS if by_session \
                                              else MIN_NUM_TRIALS_PER_STATE
  control_trials, opto_trials = splitToControlOpto(df)
  # print(f"Control len: {len(control_trials)} - Opto len: {len(opto_trials)}")
  def expand(trials_df):
    trials_df = ChainedGrpBy(trials_df)
    if by_animal:
      trials_df = trials_df.byAnimal()
    if by_session:
      trials_df = trials_df.bySess()
    return trials_df
  control_trials = expand(control_trials)
  opto_trials = expand(opto_trials)

  def fltrMinChoiceTrials(df):
    # TODO: Take col name as arg and do len(df[df[df_col_name].notnull()])
    return len(df) >= min_choice_trials
  control_trials = control_trials.filter(fltrMinChoiceTrials)
  opto_trials =  opto_trials.filter(fltrMinChoiceTrials)

  def filterIfNotExist(df, src_info, *, df_info=None):
    return df_info in src_info
  len_opto_trials_before, len_cntrl_trials_before = len(opto_trials), len(control_trials)
  opto_info = set([grp_info for grp_info, _ in opto_trials])
  control_trials = control_trials.filter(filterIfNotExist, opto_info)
  control_info = set([grp_info for grp_info, _ in control_trials])
  opto_trials = opto_trials.filter(filterIfNotExist, control_info)
  if len(opto_trials) != len_opto_trials_before:
    print("---- Control trials:", len(control_trials), "- before:", len_cntrl_trials_before)
    print("---- Opto trials:", len(opto_trials), "- before:", len_opto_trials_before)
  # print("---- Opto trials:", len(opto_trials))

  return control_trials, opto_trials
