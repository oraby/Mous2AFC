from report import analysis
from report.evdaccum.evdutils import plotSides, GroupBy
from report.evdaccum.reactiontime import _reactionTimeDist
from report.evdaccum.decisiontime import _EWDTimeDist
from report.utils import grpBySess
from definitions import (MinSamplingType, MatrixState, ExperimentType,
                         BrainRegion)
from report.clr import adjustColorLightness, BrainRegion as BrainRegionClr
import imgkit
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import PIL
from functools import partial

def optoReactionTime(df, save_figs, quantile, save_prefix, **kargs):
  STIMULUS_TIME_MIN = 2
  df_reaction_time = df[df.ST.notnull() &
                        (df.MinSample < 0.75) &
                        (df.GUI_StimulusTime >= STIMULUS_TIME_MIN)]
  applyFn = partial(_partialApplyFn, is_rt=True, quantile=quantile,
                    save_figs=save_figs, save_prefix=save_prefix, **kargs)
  loop_kargs = dict(by_start_state=True, by_dur=True,
                    by_brain_region=True
                    )
  _loopOptoDF(df=df_reaction_time, applyFn=applyFn, name="All Animals",
              **loop_kargs)
  # for animal_name, animal_df in df_reaction_time.groupby("Name"):
  #   _loopOptoDF(df=animal_df, applyFn=applyFn, name=animal_name, **loop_kargs)
  return df_reaction_time

def optoFixedTime(df, save_figs, save_prefix, **kargs):
  df = df[(df.GUI_StimulusTime <= 1) |
          # In the past protocols, RewardAfterMinSampling stopped any further
          # stimulus. TODO: Get the data of that change and filter on it instead.
          ((df.GUI_RewardAfterMinSampling == 1) & (df.ST.round(1) == 1))]
  df = df[df.GUI_StimAfterPokeOut == 0]
  df = df[((df.MinSample >= 0.9) & (df.GUI_MinSampleType == MinSamplingType.AutoIncr) & (df.GUI_MinSampleMax == 1)) |
          ((df.GUI_MinSampleMin == 1) & (df.GUI_MinSampleType == MinSamplingType.FixMin))]
  df = df.copy()
  df.loc[df.GUI_OptoEndState1 == MatrixState.WaitCenterPortOut,
         "GUI_OptoEndState1"] = MatrixState.CenterPortRewardDelivery
  assert np.sum(df.MinSample > 1) < 10
  df = df[df.MinSample <= 1]

  applyFn = partial(_partialApplyFn, is_rt=False,
                    save_figs=save_figs, save_prefix=save_prefix, **kargs)
  _loopOptoDF(df=df, applyFn=applyFn, name=f"All Animals", combine_df=True)
  for animal_name, animal_df in df.groupby("Name"):
    _loopOptoDF(df=animal_df, applyFn=applyFn, name=animal_name,
                combine_df=True)
  return df

def _combFixedTime(df):
  df = df.copy()
  df.loc[(df.GUI_OptoStartState1 == MatrixState.stimulus_delivery) &
          (df.GUI_OptoEndState1 == MatrixState.CenterPortRewardDelivery) &
          (df.GUI_OptoMaxTime > 1),
          "GUI_OptoMaxTime"] = 1
  return df

def _partialApplyFn(is_rt, df, save_figs, save_prefix, combined_df=False,
                    quantile=None, **kargs):
  # df_null = df[df.ChoiceCorrect.isnull()]
  # df = df[df.ChoiceCorrect.notnull()]
  df_opto  = df[df.OptoEnabled == 1]
  if not len(df_opto):
    print(f"Skipping {kargs} as it has no opto trials")
    return

  _optoBrainRegionReactionTime(df=df, quantile=quantile, **kargs)
  return
  name = kargs["name"]
  if combined_df:
    kargs["name"] = f"{name} (Combined)"
  ROWS, COLS = (5 if is_rt else 5), 2
  fig, axs = plt.subplots(ROWS, COLS)
  fig.set_size_inches(COLS*analysis.SAVE_FIG_SIZE[0],
                      ROWS*analysis.SAVE_FIG_SIZE[1])
  _optoBrainRegionPerf(df=df, is_rt=is_rt, **kargs, axs=[axs[0]])
  _optoBrainRegionMovementTime(df=df, is_rt=is_rt, **kargs, axs=[axs[2]])
  # TODO: Re-enable this part
  # _optoBrainRegionEWD(df=df, is_rt=is_rt, **kargs, axs=[axs[3]])
  if is_rt:
    print("Calling Opto _optoBrainRegionReactionTime")
    _optoBrainRegionReactionTime(df=df, hist_axs=axs[-1], quantile=quantile,
                                 **kargs, axs=[axs[1]])
  else:
    print("Calling Opto _optoBrainRegionFixedTime")
    _optoBrainRegionFixedTime(df=df, **kargs, hist_axs=axs[-1], axs=[axs[1]])

  DF_IMG_FP = "out.png"
  _dumpOptoDFAsImage(df_opto=df_opto.copy(), fp=DF_IMG_FP)
  img = plt.imread(DF_IMG_FP)
  # I can't get this part to work properly
  img_height = img.shape[1]*0.1/fig.dpi
  ax_img = axs[-1][0].inset_axes([-0.2, -1.5, 2.5, img_height])
  ax_img.imshow(img)
  ax_img.imshow(img)
  ax_img.axis("off")
  if save_figs:
    comb_str = "_comb" if combined_df else ""
    br = kargs["brain_region_str"]
    prefix = f"{save_prefix }/{name}/{br}/"
    # save_postfix = kargs["save_postfix"]
    save_short_name = "rt" if is_rt else "dt"
    save_postfix = (f"{br}_{save_short_name}_{kargs['exp_type_str']}_"
                    f"{kargs['brain_region_str']}_{kargs['start_state_str']}_"
                    f"S_{kargs['opto_offset']}_dur_{kargs['opto_dur']}_{name}")
                  # f"{start_state_str}_S_{opto_offset}_dur_{opto_dur}{save_suffix}")
    analysis.savePlot(prefix + save_postfix + comb_str)
    plt.close()
  else:
    plt.show()

def _loopOptoDF(df, applyFn, name, by_exp_type=True,
                by_brain_region=True, by_start_state=True,
                by_start_delay=True, by_dur=True, combine_df=False):
  if combine_df:
    comb_df = _combFixedTime(df)
  cols = []
  if by_exp_type:
    cols.append("GUI_ExperimentType")
  if by_start_state:
    cols.append("GUI_OptoStartState1")
  if by_start_delay:
    cols.append("GUI_OptoStartDelay")
  if by_dur:
    cols.append("GUI_OptoMaxTime")
  if by_brain_region:
    cols.append("GUI_OptoBrainRegion")
  for df_info, sub_df in df.groupby(cols):
    gen_comb = False
    if combine_df:
      cond = comb_df.index == comb_df.index # Start with all True
      for col_name, col_val in zip(cols, df_info):
        cond &= comb_df[col_name] == col_val
      comb_sub_df = comb_df[cond]
      if len(sub_df) != len(comb_sub_df):
        gen_comb = True
    idx = 0
    def dfInfo(flag, flag_default, conv=None):
      nonlocal idx
      if flag:
        val = df_info[idx]
        idx += 1
        return conv(val) if conv is not None else val
      else:
        return flag_default
    exp_type     = dfInfo(by_exp_type,     "All Experiments", ExperimentType)
    start_state  = dfInfo(by_start_state,  "Any Start-State", MatrixState)
    opto_offset  = dfInfo(by_start_delay,  "All Opto Start-Offsets")
    opto_dur     = dfInfo(by_dur,          "All Opto Durations")
    brain_region = dfInfo(by_brain_region, "All Brain-Regions", BrainRegion)
    applyFn(df=sub_df, name=name, exp_type_str=exp_type,
            brain_region_str=brain_region, start_state_str=start_state,
            opto_offset=opto_offset, opto_dur=opto_dur)
    if gen_comb:
      print("Generating combined")
      applyFn(df=comb_sub_df, name=name, exp_type_str=exp_type,
              brain_region_str=brain_region, start_state_str=start_state,
              opto_offset=opto_offset, opto_dur=opto_dur, combined_df=True)
    elif combine_df:
      print("Not generating combined")
    else:
      print("Not asked to generate combined")

def _dfSplitFn(df_cntrl, df_opto):
  # print("df_opto.calcDecisionTime.notnull().sum():", df_opto.calcDecisionTime.notnull().sum())
  # display(df_opto.ST)
  if df_opto.ST.notnull().sum() < 50:
    return [(df_cntrl, "-"),], [(df_opto, "--"),]
  def split(_df):
    q = 1 #_df.ST.quantile(quantile)
    print("Quantile:", q)
    return _df[_df.ST <= q], _df[_df.ST > q]
  lower_cntrl, upper_cntrl = split(df_cntrl)
  lower_opto, upper_opto = split(df_opto)
  print("Opto len:", len(df_opto))
  print("lower len:", len(lower_opto), "- Upper len:", len(upper_opto))
  return [(lower_cntrl, "-"),  (upper_cntrl, "-")], \
         [(lower_opto,  "--"), (upper_opto, "dotted")]

def _optoBrainRegionPerf(df, is_rt, **kargs):
  col_friendly_name = f"{'RT' if is_rt else 'DT'} Performance"
  dfSplitFn = _dfSplitFn if is_rt else None
  kargs = kargs.copy()
  brain_regions = df.GUI_OptoBrainRegion.unique()
  if len(brain_regions) == 1:
    plot_all_clr = BrainRegionClr[str(BrainRegion(brain_regions[0]))]
  else:
    plot_all_clr = None
  return _optoBrainRegionTime(df, col_df_name="ChoiceCorrect",
                              col_friendly_name=col_friendly_name,
                              y_label="Correct Ratio", plot_only_all=True,
                              plot_all_clr=plot_all_clr, dfSplitFn=dfSplitFn,
                              **kargs)

def _optoBrainRegionFixedTime(df, hist_axs, **kargs):
  df_cntrl = df[df.OptoEnabled == 0]
  df_opto  = df[df.OptoEnabled == 1]
  _EWDTimeDist(ax=hist_axs[0], df=df_cntrl, num_bins_per_sec=10,
               animal_name="Control", df_plot_quantile=False,
               plot_decision_time=True)
  _EWDTimeDist(ax=hist_axs[1], df=df_opto, num_bins_per_sec=10,
               animal_name="Opto", df_plot_quantile=False,
               plot_decision_time=True)
  return _optoBrainRegionTime(df, col_df_name="calcDecisionTime",
                              col_friendly_name="Decision Time",
                              y_label="Decision Time (s)", **kargs)


def _optoBrainRegionReactionTime(df, quantile, **kargs):
  df = df.copy()
  df = df[df.calcStimulusTime.notnull()]
  # df.loc[df.calcStimulusTime > df.GUI_StimulusTime, "calcStimulusTime"] = \
  #                                                            df.GUI_StimulusTime
  df = df[df.calcStimulusTime < df.GUI_StimulusTime - 0.1]
  df_cntrl = df[df.OptoEnabled == 0]
  df_opto  = df[df.OptoEnabled == 1]
  opto_start = df.GUI_OptoStartDelay.unique()
  opto_end = (df.GUI_OptoStartDelay + df.GUI_OptoMaxTime).unique()
  assert len(opto_start) == 1, "Found opto start: " + str(opto_start)
  assert len(opto_end) == 1, "Found opto end: " + str(opto_end)
  opto_start = opto_start[0]
  opto_end = opto_end[0]
  opto_lapse = opto_end # + 0.15
  ##
  def axMarkOptoRegion(ax):
    # ax.axvline(opto_end, color="black", linestyle="--", alpha=0.3,
    #            label="Opto End")
    ax.axvspan(opto_start, opto_end, alpha=0.5, color='yellow',
               label="Opto Inhibition")
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    # ax.spines['bottom'].set_visible(False)
    # ax.spines['left'].set_visible(False)
  num_bins_per_sec = 10
  max_st = df.calcStimulusTime.max()
  max_bin = int(np.ceil(max_st*num_bins_per_sec))
  # bins = np.linspace(0, max_bin/num_bins_per_sec, max_bin+1)
  # print("bins:", bins)
  # num_hist_bins = int(np.ceil(max_st*num_bins_per_sec))
  # ax.hist(df_cntrl.calcStimulusTime, bins
  ##
  br = f"{kargs['brain_region_str']}"
  print("Brain region:", br)
  ROOT_DIR = fr"C:\Users\hatem\OneDrive - Floating Reality\analysis\Opto Poster Plots 0.3s\{br}"
  from pathlib import Path
  if Path(ROOT_DIR).parent.exists():
    Path(ROOT_DIR).mkdir(parents=True, exist_ok=True)
  # opto_color = BrainRegionClr[br]

  animals_names = df_cntrl.Name.unique()
  ##
  # for animal_name in animals_names:
  #   ex_df_cntrl = df[df.Name == animal_name]
  #   fig, ax = plt.subplots()
  #   fig.set_size_inches(analysis.SAVE_FIG_SIZE[0], analysis.SAVE_FIG_SIZE[1])
  #   _reactionTimeDist(ax=ax, df=ex_df_cntrl, animal_name="",
  #                     df_plot_quantile_li=[], num_bins_per_sec=10,
  #                     plot_earlywithdrawal=False)
  #   plt.savefig(f"{ROOT_DIR}/rt_hist_{animal_name}.pdf", dpi=300,
  #               bbox_inches='tight')
  #   plt.show()
  # return

  def getKDEFn(df_col):
    from scipy.stats import gaussian_kde
    kde = gaussian_kde(df_col)
    kde.covariance_factor = lambda : .05
    kde._compute_covariance()
    return kde

  from scipy.stats import sem
  def plotMeanSEM(ax, x, ys, color, label):
    y = np.nanmean(ys, axis=0)
    y_sem = sem(ys, axis=0, nan_policy="omit")
    ax.plot(x, y, color=color, label=label)
    ax.fill_between(x, y-y_sem, y+y_sem, color=color, alpha=0.2)

  def getBrainRegionColorAndLabel(br):
    if isinstance(br, str) and br.split(" ", 1)[0] == "Control":
      sec_br = br.split(" ")
      sec_br = "" if len(sec_br) == 1 else f" {BrainRegion(float(sec_br[1]))}"
      return "black", f"Control{sec_br}"
    else:
      br = BrainRegion(br)
      return BrainRegionClr[str(br)], f"Opto {br}"

  def plotBins(ax, used_x_bins, processFn):
    regions_ys = processFn(used_x_bins)
    for br, ys in regions_ys.items():
      color, label = getBrainRegionColorAndLabel(br)
      plotMeanSEM(ax, used_x_bins, ys, color=color, label=label)

  def processCDF(animals_src_dict):
    regions_ys = {}
    for animal_name in animals_names:
      cdf_dict = animals_src_dict[animal_name]
      for br, ys in cdf_dict.items():
        arr_ys = regions_ys.get(br, [])
        arr_ys.append(ys)
        regions_ys[br] = arr_ys
    return regions_ys

  fig, ax = plt.subplots(); axMarkOptoRegion(ax)
  fig.set_size_inches(analysis.SAVE_FIG_SIZE[0], analysis.SAVE_FIG_SIZE[1])
  animals_kde = {}
  for animal_name in animals_names:
    controlKDE = getKDEFn(
                        df_cntrl[df_cntrl.Name == animal_name].calcStimulusTime)
    animals_kde[animal_name] = {"Control":controlKDE}
    for br, br_df in df_opto[df_opto.Name == animal_name].groupby(
                                                         "GUI_OptoBrainRegion"):
      optoKDE = getKDEFn(br_df.calcStimulusTime)
      animals_kde[animal_name][br] = optoKDE
  def processXbins(used_x_bins):
    regions_ys = {}
    for animal_name, dict_KDEs in animals_kde.items():
      for br, kde in dict_KDEs.items():
        ys = kde(used_x_bins)
        total_count = ys.max() # Treat it as a histogram
        ys = ys/total_count
        arr = regions_ys.get(br, [])
        arr.append(ys)
        regions_ys[br] = arr
    return regions_ys
  x_bins = np.linspace(0, max_bin/num_bins_per_sec, 1000)
  plotBins(ax, x_bins, processFn=processXbins)
  ax.set_xlabel("Time (s)")
  ax.set_ylabel("Normalized Probability")
  plt.savefig(f"{ROOT_DIR}/total_hist.pdf", dpi=300, bbox_inches='tight')
  plt.show()

  orig_ax = ax
  fig, ax = plt.subplots(); axMarkOptoRegion(ax)
  fig.set_size_inches(analysis.SAVE_FIG_SIZE[0]/3, analysis.SAVE_FIG_SIZE[1])
  # x_bins = x_bins[x_bins < opto_lapse + 1]
  plotBins(ax, x_bins, processFn=processXbins)
  # ax.set_ylabel("Percentage of Trials Performed")
  # ax.set_xlabel("Reaction Time (s)")
  # early_cntrl = df_cntrl[df_cntrl.calcStimulusTime < opto_lapse].calcStimulusTime
  # early_opto =  df_opto[  df_opto.calcStimulusTime < opto_lapse].calcStimulusTime
  # ax.axvline(opto_end, color="black", linestyle="--", alpha=0.3)
  # ax.axvspan(opto_start, opto_lapse, alpha=0.5, color='yellow',
  #            label="Opto End")
  # cntrl_ys, opto_ys = processXbins(x_bins)
  # plotMeanSEM(ax, x_bins, cntrl_ys, color="black", label="Control")
  # plotMeanSEM(ax, x_bins, opto_ys, color=opto_color, label=f"Opto {br}")
  ax.set_xlim(0, opto_lapse + 0.1)
  ax.set_ylim(*orig_ax.get_ylim())
  ax.set_xlabel("Time (s)")
  ax.set_ylabel("Normalized Probability")
  plt.savefig(f"{ROOT_DIR}/early_hist.pdf", dpi=300, bbox_inches='tight')
  plt.show()


  fig, ax = plt.subplots(); axMarkOptoRegion(ax)
  fig.set_size_inches(analysis.SAVE_FIG_SIZE[0], analysis.SAVE_FIG_SIZE[1])
  # x_bins = x_bins[x_bins < opto_lapse + 1]
  plotBins(ax, x_bins, processFn=processXbins)
  ax.set_xlim(opto_end - 0.1, 3)
  ax.set_ylim(*orig_ax.get_ylim())
  ax.set_xlabel("Time (s)")
  ax.set_ylabel("Normalized Probability")
  plt.savefig(f"{ROOT_DIR}/late_hist.pdf", dpi=300, bbox_inches='tight')
  plt.show()

  df_late_cntrl = df_cntrl[df_cntrl.calcStimulusTime > opto_lapse]
  df_late_opto =  df_opto[  df_opto.calcStimulusTime > opto_lapse]
  ##
  fig, ax = plt.subplots(); axMarkOptoRegion(ax)
  fig.set_size_inches(analysis.SAVE_FIG_SIZE[0], analysis.SAVE_FIG_SIZE[1])
  def cumCounts(col_data, bins, total_count):
    counts, _ = np.histogram(col_data, bins=bins)
    y = np.cumsum(counts)
    offset = total_count - y[-1]
    y += offset
    y = 100*y/total_count # (total_count - len(col_data)zzzzz
    # y += (1-len(col_data)/total_count)*100
    return y
  animals_cdf = {}
  used_x_bins = np.linspace(0, max_bin/num_bins_per_sec, 1000)
  for animal_name in animals_names:
    total_count = len(df_cntrl[df_cntrl.Name == animal_name])
    control_st = cumCounts(df_cntrl[df_cntrl.Name == animal_name].calcStimulusTime,
                           bins=used_x_bins, total_count=total_count)
    animals_cdf[animal_name] = {"Control":control_st}
    animal_opto = df_opto[df_opto.Name == animal_name]
    for br, br_df in animal_opto.groupby("GUI_OptoBrainRegion"):
      total_count = len(df_opto[(df_opto.Name == animal_name) &
                                (df_opto.GUI_OptoBrainRegion == br)])
      animals_cdf[animal_name][br] = cumCounts(br_df.calcStimulusTime,
                                               bins=used_x_bins,
                                               total_count=total_count)
  # used_x_bins = x_bins[x_bins > opto_lapse]
  xs_plot = (used_x_bins[:-1] + used_x_bins[1:])/2
  regions_ys = processCDF(animals_src_dict=animals_cdf)
  for br, ys in regions_ys.items():
    color, label = getBrainRegionColorAndLabel(br)
    plotMeanSEM(ax, xs_plot, ys, color=color, label=label)
  ax.set_title("Decision Probability")
  ax.set_xlabel("Time (s)")
  ax.set_ylabel("Percentage of Cumulative Trials Performed")
  ax.set_xlim(opto_end - 0.1, 3)
  ax.set_ylim(0, 100)
  plt.savefig(f"{ROOT_DIR}/late_decision_probability.pdf", dpi=300,
              bbox_inches='tight')
  plt.show()


  ##
  def calcDecisionProb(df, cutoff):
    return 100*len(df[df.calcStimulusTime <= cutoff])/len(df)

  def calcChoicePerformance(df, cutoff):
    df = df[df.calcStimulusTime <= cutoff]
    return 100*len(df[df.ChoiceCorrect == 1])/len(df)

  def plotEarlyProb(metricFn, metric_name, y_label):
    fig, ax = plt.subplots()
    fig.set_size_inches(analysis.SAVE_FIG_SIZE[0]/2, analysis.SAVE_FIG_SIZE[1])
    animals_prob = {}
    for animal_name in animals_names:
      animal_df = df[df.Name == animal_name]
      animals_prob[animal_name] = {}
      for br, region_df in animal_df.groupby("GUI_OptoBrainRegion"):
        region_cntrl = region_df[region_df.OptoEnabled == 0]
        cntrl_perf = metricFn(region_cntrl, opto_lapse)
        region_opto = region_df[region_df.OptoEnabled == 1]
        opto_perf = metricFn(region_opto, opto_lapse)
        animals_prob[animal_name][br] = (cntrl_perf, opto_perf)

    br_perf = {}
    for animal_name, animal_br_perf in animals_prob.items():
      for br, (cntrl_perf, opto_perf) in animal_br_perf.items():
        color, label = getBrainRegionColorAndLabel(br)
        ax.plot([0, 1], [cntrl_perf, opto_perf], color=color, alpha=0.1)
        if br not in br_perf:
          br_perf[br] = []
        br_perf[br].append((cntrl_perf, opto_perf))
    offset = 0
    for br, zipped_perf in br_perf.items():
      zipped_perf = np.array(zipped_perf)
      cntrl_perf = zipped_perf[:, 0]
      opto_perf = zipped_perf[:, 1]
      color, label = getBrainRegionColorAndLabel(br)
      cntrl_mean = np.mean(cntrl_perf)
      cntrl_sem = sem(cntrl_perf)
      opto_mean = np.mean(opto_perf)
      opto_sem = sem(opto_perf)
      ax.errorbar([0 + offset, 1 + offset], [cntrl_mean, opto_mean], [cntrl_sem, opto_sem],
                  color=color, alpha=1, label=label)
      offset = 0.01
    ax.set_xticks([0, 1], ["Control", "Opto"])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    # ax.spines['bottom'].set_visible(False)
    ax.set_xlim(-0.2, 1.2)
    ax.set_title(f"Early {metric_name}")
    ax.set_ylabel(y_label)
    plt.savefig(f"{ROOT_DIR}/early_{metric_name}.pdf", dpi=300,
                bbox_inches='tight')
    plt.show()

  plotEarlyProb(calcDecisionProb, "Decision Probability", "Percentage of Trials Performed")
  plotEarlyProb(calcChoicePerformance, "Performance", "Decision Performance")

  ##
  fig, ax = plt.subplots(); axMarkOptoRegion(ax)
  fig.set_size_inches(analysis.SAVE_FIG_SIZE[0], analysis.SAVE_FIG_SIZE[1])
  animal_perf_counts = {}
  def processPerfBins(used_x_bins):
    regions_ys = {}
    for animal_name, perf_counts_dict in animal_perf_counts.items():
      for br, ys in perf_counts_dict.items():
        # ys_total = totalKDE(used_x_bins)
        # ys_corr = corrKDE(used_x_bins)
        # ys_total[ys_total == 0] = 1 # avoid division by zero
        # ys = 100*ys_corr/ys_total
        # ys[ys > 100] = 100 # avoid values > 100%
        #total_count = ys.max() # Treat it as a histogram
        #ys = ys/total_count
        def movingAvg(x, w):
          return np.convolve(x, np.ones(w), 'same') / w
        ys = movingAvg(ys, w=4)
        arr = regions_ys.get(br, [])
        arr.append(ys)
        regions_ys[br] = arr
    return regions_ys
  def calcPerHistogram(sub_df, bins, _print=False):
    counts_total, _ = np.histogram(sub_df.calcStimulusTime, bins=bins)
    counts_corr, _ = np.histogram(
                  sub_df[sub_df.ChoiceCorrect == 1].calcStimulusTime, bins=bins)
    if _print:
      print("counts_total:", counts_total)
    counts_total[counts_total == 0] = 1 # avoid division by zero
    return 100*counts_corr/counts_total

  num_bins_per_sec = 4
  max_st = df.calcStimulusTime.max()
  max_bin = int(np.ceil(max_st*num_bins_per_sec))
  bins = np.linspace(0, max_bin/num_bins_per_sec, max_bin+1)
  print("Bins:", bins)
  # num_hist_bins = int(np.ceil(max_st*num_bins_per_sec))
  for animal_name in animals_names:
    animal_cntrl_df = df_cntrl[df_cntrl.Name == animal_name]
    # animal_cntrl_df = animal_cntrl_df[
    #                               animal_cntrl_df.calcStimulusTime > opto_lapse]
    # controlKDETotal = getKDEFn(animal_cntrl_df.calcStimulusTime)
    # controlKDECorr = getKDEFn(
    #        animal_cntrl_df[animal_cntrl_df.ChoiceCorrect == 1].calcStimulusTime)
    # print("Animal:", animal_name)
    cntrl_perf = calcPerHistogram(animal_cntrl_df, bins=bins, _print=True)
    # print("cntrl_perf:", cntrl_perf)
    animal_perf_counts[animal_name] = {"Control":cntrl_perf}
    df_animal_opto = df_opto[df_opto.Name == animal_name]
    # df_animal_opto = df_animal_opto[df_animal_opto.calcStimulusTime >
    #                                  opto_lapse]
    for br, br_df in df_animal_opto.groupby("GUI_OptoBrainRegion"):
      # optoKDETotal = getKDEFn(br_df.calcStimulusTime)
      # optoKDECorr = getKDEFn(br_df[br_df.ChoiceCorrect == 1].calcStimulusTime)
      opto_perf = calcPerHistogram(br_df, bins=bins)
      animal_perf_counts[animal_name][br] = opto_perf
  # used_x_bins = np.linspace(opto_lapse, max_bin/num_bins_per_sec, 1000)
  bins = (bins[:-1] + bins[1:])/2
  plotBins(ax, bins, processFn=processPerfBins)
  ax.set_title("Decision Performance")
  ax.set_xlim(opto_end - 0.1, 3)
  ax.set_xlabel("Reaction Time (s)")
  ax.set_ylim(50, 100)
  ax.set_ylabel("Percentage of Correct Choices")
  plt.savefig(f"{ROOT_DIR}/late_decision_performance.pdf", dpi=300,
               bbox_inches='tight')
  plt.show()
  # cntrl_bins, cntrl_y = cumCounts(late_cntrl, len(late_cntrl))
  # opto_bins,  opto_y  = cumCounts(late_opto,    len(late_cntrl))
  # ax.plot(cntrl_bins, cntrl_y, label="Control", color="black")
  # br = BrainRegion(br)
  # # print("Brain region:", str(br), "Color:", BrainRegionClr[str(br)])
  # color = BrainRegionClr[str(br)]
  # ax.plot(opto_bins,  opto_y,  label=f"Opto {br}", color=opto_color)



def _optoBrainRegionReactionTime2(df, quantile, hist_axs, **kargs):
  df_cntrl = df[df.OptoEnabled == 0]
  df_opto  = df[df.OptoEnabled == 1]
  start_delay = df_opto.GUI_OptoStartDelay.unique()
  opto_dur = df_opto.GUI_OptoMaxTime.unique()
  assert len(start_delay) == 1; assert len(opto_dur) == 1
  start_delay = start_delay[0]; opto_dur = opto_dur[0]
  _reactionTimeDist(ax=hist_axs[0], df=df_cntrl, animal_name="",
                    df_plot_quantile_li=[], num_bins_per_sec=10,
                    plot_earlywithdrawal=True)
  _reactionTimeDist(ax=hist_axs[1], df=df_opto, animal_name="",
                    df_plot_quantile_li=[], num_bins_per_sec=10,
                    plot_earlywithdrawal=True)
  [hax.set_xlim(0, 4) for hax in hist_axs]
  ###cutoff = start_delay + opto_dur + 0.2
  ###if np.sum(df_opto.ST > cutoff) not in  (0, len(df_opto)) and \
  ###   np.sum(df_cntrl.ST > cutoff) not in (0, len(df_cntrl)):
  ###  print("Cut off:", cutoff)
  ###  ###
  ###  from scipy.stats import gaussian_kde
  ###  max_y = 0
  ###  for is_less in [True, False]:
  ###    # if is_less:
  ###    if True:
  ###      ax = hist_axs[0]
  ###      ax.axvline(cutoff, linestyle="dashed")
  ###    # else:
  ###      # ax = hist_axs[1]
  ###    all_xs = np.linspace(df.ST.min(), df.ST.max(), 10000)
  ###    for _df, clr in [(df_opto, 'r'), (df_cntrl, 'k')]:
  ###      xs = all_xs.copy()
  ###      BANDWIDTH = 0.2
  ###      density = gaussian_kde(_df.ST)
  ###      density.covariance_factor = lambda : BANDWIDTH
  ###      density._compute_covariance()
  ###      y_data = density(xs)
  ###      # y_data *= counts.max() / y_data.max() # Find a good scaling point
  ###      y_data /= y_data.max() # Normalize to 1
  ###      y_data /= y_data.sum() # Divide by max value
  ###      max_y = max(max_y, max(y_data))
  ###      keep = xs <= cutoff if is_less else cutoff < xs
  ###      xs = xs[keep]
  ###      y_data = y_data[keep]
  ###      ax.plot(xs, y_data, color=clr)
  ###  ax.set_xlim(left=0, right=4)
  ###  hist_axs[0].set_ylim(bottom=0, top=max_y*1.1)
    ###
    # _reactionTimeDist(ax=hist_axs[0], df=df_cntrl[df_cntrl.ST <= cutoff], num_bins_per_sec=10, animal_name="")
    # _reactionTimeDist(ax=hist_axs[0], df=df_opto[df_opto.ST <= cutoff], num_bins_per_sec=10, animal_name="")
    # hist_axs[0].set_xlim(left=0, right=cutoff + 0.1), hist_axs[0].set_ylim(bottom=0)
    # _reactionTimeDist(ax=hist_axs[1], df=df_cntrl[df_cntrl.ST > cutoff], num_bins_per_sec=10, animal_name="")
    # _reactionTimeDist(ax=hist_axs[1], df=df_opto[df_opto.ST > cutoff], num_bins_per_sec=10, animal_name="")
    # hist_axs[1].set_xlim(left=cutoff - 1, right=4), hist_axs[1].set_ylim(bottom=0)

  col_friendly_name = "RT (Shadlen)"
  fig_title = _genFigTitle(name=kargs["name"],
                           col_friendly_name=col_friendly_name,
                           exp_type_str=kargs["exp_type_str"],
                           brain_region_str=kargs["brain_region_str"],
                           start_state_str=kargs["start_state_str"],
                           opto_offset=kargs["opto_offset"],
                           opto_dur=kargs["opto_dur"])
  hist_axs[0].set_title(f"Control {fig_title}", fontsize=12)
  hist_axs[1].set_title(f"Opto {fig_title}", fontsize=12)
  return _optoBrainRegionTime(df, col_df_name="ST",
                              col_friendly_name=col_friendly_name,
                              y_label="Reaction Time (s)",
                              plot_only_all=True, dfSplitFn=_dfSplitFn,
                              **kargs)

def _optoBrainRegionMovementTime(df, is_rt, **kargs):
  col_friendly_name = f"{'RT' if is_rt else 'DT'} Movement Time"
  kargs = kargs.copy()
  return _optoBrainRegionTime(df, col_df_name="calcMovementTime",
                              col_friendly_name=col_friendly_name,
                              y_label="Movement Time (s)",
                              **kargs)

def _optoBrainRegionEWD(df, is_rt, **kargs):
  col_friendly_name = f"{'RT' if is_rt else 'DT'} Early-Withdrawal"
  kargs = kargs.copy()
  brain_regions = df.GUI_OptoBrainRegion.unique()
  if len(brain_regions) == 1:
    plot_all_clr = BrainRegionClr[str(BrainRegion(brain_regions[0]))]
  else:
    plot_all_clr = None
  axs = _optoBrainRegionTime(df, col_df_name="EarlyWithdrawal",
                            col_friendly_name=col_friendly_name,
                            y_label=f"EWD Ratio ({plot_all_clr})",
                            plot_only_all=True,
                            plot_all_clr=plot_all_clr, keep_unfiltered=True,
                            **kargs)
  sec_axs = [ax.twinx() for ax in axs[0]]
  df = df[df.EarlyWithdrawal == True]
  kargs["axs"] = [sec_axs]
  _optoBrainRegionTime(df, col_df_name="calcStimulusTime",
                       col_friendly_name=col_friendly_name,
                       y_label="EWD Sampling Time (Sec) - (Gray)",
                       plot_only_all=True,
                       plot_all_clr="gray", keep_unfiltered=True,
                       **kargs)
  return axs

def _optoBrainRegionTime(df, col_df_name, col_friendly_name, y_label,
                         name, exp_type_str, brain_region_str,
                         start_state_str, opto_offset, opto_dur,
                         # save_prefix, save_figs,
                         axs=None, plot_only_all=False, plot_all_clr=None,
                         keep_unfiltered=False, dfSplitFn=None):
  # df = df[df.ChoiceCorrect.notnull()]
  df_cntrl = df[df.OptoEnabled == 0]
  df_opto  = df[df.OptoEnabled == 1]
  if not len(df_opto):
    print(f"Skipping {brain_region_str} as it has no opto trials")
    return # We should have bailed out earlier already
  if dfSplitFn is not None:
    # TOOD: Check that the function only returned data from the opto df
    df_cntrl_li, df_opto_li = dfSplitFn(df_cntrl, df_opto)
    assert all([len(_df) for _df, ls in df_opto_li])
    assert all([len(_df) for _df, ls in df_cntrl_li])
  else:
    df_cntrl_li = [(df_cntrl, "-"),]
    df_opto_li =  [(df_opto, "--"),]
  print("len(df_opto_li):", len(df_opto_li))
  fig_title = _genFigTitle(name=name, col_friendly_name=col_friendly_name,
                           exp_type_str=exp_type_str,
                           brain_region_str=brain_region_str,
                           start_state_str=start_state_str,
                           opto_offset=opto_offset, opto_dur=opto_dur)
  return_axs = True
  for idx, (_df, ls) in enumerate([*df_cntrl_li, *df_opto_li]):
    if plot_all_clr and len(df_cntrl_li) > 1:
      _plot_all_clr = adjustColorLightness(plot_all_clr,
                                       0.6 + (1.4 - 0.6)*(idx%len(df_cntrl_li)))
    else:
      _plot_all_clr = plot_all_clr
    axs =  plotSides(_df, col_name=col_df_name,
                    friendly_col_name=col_friendly_name,
                    periods=3, animal_name=fig_title,
                    y_label=y_label, keep_unfiltered=keep_unfiltered,
                    quantile_top_bottom=None, grpby=GroupBy.Difficulty,
                    plot_vsDiff=True, plot_only_all=plot_only_all,
                    plot_all_clr=_plot_all_clr,
                    plot_hist=False, save_figs=False, save_prefix=None,
                    save_postfix=None,
                    legend_loc="upper right",
                    axs=axs, ls=ls, return_axs=return_axs)
  # return_axs = False
  for ax in axs[0]:
    ax.set_title(fig_title, fontsize=12)
  return axs

def _genFigTitle(name, col_friendly_name, exp_type_str, brain_region_str,
                 start_state_str, opto_offset, opto_dur):
  return (f"{name} {col_friendly_name} {exp_type_str} {brain_region_str} -"
          f" {start_state_str} S:{opto_offset} - Dur:{opto_dur}")

def _dumpOptoDFAsImage(df_opto, fp, avg_stimulus_time=False):
  stateStr = lambda i:f"{MatrixState(i)}"
  df_opto["OptoStartState"] = df_opto.GUI_OptoStartState1.apply(stateStr)
  df_opto["OptoEndState"] = df_opto.GUI_OptoEndState1.apply(stateStr)
  df_opto["MinSampleType"] = df_opto.GUI_MinSampleType.apply(
                                               lambda i:f"{MinSamplingType(i)}")
  df_opto["AvgMinS"] = df_opto.MinSample.apply(lambda ms:f"{ms:.1f}")
  if avg_stimulus_time:
    df_opto["AvgST"] = df_opto.ST.apply(lambda st:f"{st:.1f}")
  df_opto["Animals"] = df_opto.Name
  # df_opto["#Sess"] = f"{len(grpBySess(df_opto))}"
  df_opto["OptoStartDelay"] = df_opto.GUI_OptoStartDelay
  df_opto["MinS-Min"]       = df_opto.GUI_MinSampleMin
  df_opto["MinS-Max"]       = df_opto.GUI_MinSampleMax
  df_opto["StimulusTime"]   = df_opto.GUI_StimulusTime
  df_opto["OptoDur"]    = df_opto.GUI_OptoMaxTime

  cols = ["OptoStartState", "OptoStartDelay", "AvgMinS", "MinS-Min",
          "MinS-Max", "MinSampleType", "StimulusTime", "OptoEndState",
          "OptoDur", "Animals"]
  if avg_stimulus_time:
    cols.insert(3, "AvgST")
  html_df = {col:[] for col in cols}
  num_trials = []
  num_sess = []
  sapo = []
  for cols_vals, sub_df in df_opto.groupby(cols):
    [html_df[col].append(col_val) for col, col_val in zip(cols, cols_vals)]
    num_trials.append(len(sub_df))
    num_sess.append(len(grpBySess(sub_df)))
    sapo.append(f"{sub_df.GUI_StimAfterPokeOut.mean():.1f}")
  # Reorder the dictionary by creating the a new one
  cols.insert((4 if avg_stimulus_time else 3), "SAPO")
  html_df = {col:html_df.get(col) for col in cols}
  html_df["SAPO"] = sapo
  html_df["#Sess"] = num_sess
  html_df["#Trials"] = num_trials
  html_df = pd.DataFrame(html_df)
  html_df = html_df.sort_values(by="#Trials", ascending=False)
  html = html_df.to_html(index=False)
  if fp.endswith(".html"):
    with open(fp, 'w') as f:
      f.write(html)
      f.close()
  else:
    imgkit.from_string(html, fp)
  return len(html_df)

