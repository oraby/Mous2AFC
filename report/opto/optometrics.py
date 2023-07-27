from enum import Enum, auto
from report.utils import grpBySess
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from report import analysis
from report.clr import BrainRegion as BRC, adjustColorLightness
from .optoutil import ChainedGrpBy, commonOptoSectionFilter
from report.definitions import BrainRegion, ExperimentType, MatrixState, MinSamplingType

_SECOND, _PERCENT = "Seconds", "%"

class MetricMode(Enum):
  Raw = auto()
  Gain = auto()

def processAnimalMetric(*, animal_name, opto_chain, df_col_name, display_name,
                        mode:MetricMode, unit, is_many_animals, save_figs,
                        save_prefix,):
  STEP=4
  BAR_WIDTH=1
  BAR_SEP=2
  data_metric = TTestDataMetric.Median if unit == _SECOND else \
                TTestDataMetric.Mean
  secs_std = unit == _SECOND and mode == MetricMode.Raw
  plot_actual_opto = display_name in ["Early-Withdrawal", "Bias"]
  used_sess_infos = set()
  used_sess_df_li = []
  Xs = []
  Ys = []
  Yerrs = []
  if secs_std:
    Ystds = [] # Std-deviation for single points
  pvals = []
  colors = []
  x_ticks_labels = []
  x_ticks_pos = []
  org_sort = []
  cur_x_pos = 0

  for opto_config, df in opto_chain.byOptoConfig():
    start_state, start_offset, dur = opto_config
    # Early/Late
    if not (start_state == MatrixState.stimulus_delivery and
            (start_offset == 0 and dur == 0.35) or
            (start_offset == 0.65 and (dur >= 0.35 or dur == -1))):
      continue
    # Full
    # if not (start_state == MatrixState.stimulus_delivery and
    #         start_offset == 0 and dur == -1):
    #   continue
    if (start_offset == 0.35 and dur == 1.0) or \
        (start_offset == 0.85 and dur == 1.0):
      print(f"Skipping partial sampling: {opto_config} with: {len(br_df)} "
            "trials.")
      continue

    last_start_state = None
    cur_x_pos += (STEP if cur_x_pos > 0 else BAR_WIDTH)
    print("********* Processing: ", start_state, start_offset, dur)

    for brain_region, br_df in ChainedGrpBy(df).byBrainRegion():
      # if brain_region not  in [BrainRegion.ALM_Bi, BrainRegion.V1_Bi]:
      #   continue
      region_color = BRC[brain_region]
      if last_start_state and start_state != last_start_state:
        print("Updating x-pos")
        cur_x_pos += STEP/2
      last_start_state = start_state
      print("_+_+_+_+_+_+ Processing: ", brain_region, "Cur x pos: ", cur_x_pos, "Color:", region_color)

      # pvals will be used later after the loop finishes
      animals_pval, sessions_pval, by_animal_sess_info, by_sess_sess_info = \
        twoTailedTTest(br_df, df_col_name=df_col_name, metric=data_metric,
                       plot_brain_region=brain_region,
                       plot_start_state=start_state,
                       plot_animal_name=None, plot_display_name=display_name)
      # Depending on the mode, yoi can think about this variable as if it will
      # either hold be single items for gains or hold tuples of two for opto and
      # controls in raw mode, but the list is flattened
      all_ys_means = []
      if secs_std: all_ys_std = []
      used_animals, used_sess, used_opto, used_cntrl = 0, 0, 0, 0
      for cur_animal, animal_df in ChainedGrpBy(br_df).byAnimal():
        # gainDistr(animal_df, df_col_name=df_col_name, plot=True,
        #           plot_brain_region=brain_region, plot_start_state=start_state,
        #           plot_animal_name=cur_animal, plot_display_name=display_name,
        #           save_fig=True, save_prefix=save_prefix)
        # fisherExactTest(animal_df, df_col_name=df_col_name,
        #           plot_brain_region=brain_region, plot_start_state=start_state,
        #           plot_animal_name=cur_animal, plot_display_name=display_name)
        y_pts_cntrl = []
        y_pts_opto = []
        if unit == _SECOND:
          y_pts_cntrl_sem = []
          y_pts_opto_sem = []
        for sess_info, sess_df in ChainedGrpBy(animal_df).bySess():
          control_trials, opto_trials = commonOptoSectionFilter(sess_df,
                                                                by_animal=True,
                                                                by_session=True)
          if not len(opto_trials):
            # print("Skipping")
            continue
          # else:
          #   print("***** Using")
          control_trials, opto_trials = control_trials.toDF(),opto_trials.toDF()
          control_trials = control_trials[control_trials[df_col_name].notnull()]
          opto_trials = opto_trials[opto_trials[df_col_name].notnull()]
          if not len(opto_trials): # TODO: SKip this bullshit
            continue

          if display_name == "Bias":
            cntrl_mean = _dominantBiasRatio(control_trials)
            opto_mean = _dominantBiasRatio(opto_trials)
            if any(np.isnan([cntrl_mean, opto_mean])):
              print("************ Found NaN Bias.. CHeck This")
              continue
          elif data_metric == TTestDataMetric.Mean:
            cntrl_mean = control_trials[df_col_name].mean()
          else:
            cntrl_mean = control_trials[df_col_name].median()
          # Since we divide by zero, we should avoid that and use the least
          # non-zero value
          if mode == MetricMode.Gain and cntrl_mean == 0:
            cntrl_mean = 1/len(control_trials)
          y_pts_cntrl.append(cntrl_mean)
          if display_name == "Bias":
            pass # It was already calculated above
          elif data_metric == TTestDataMetric.Mean:
            opto_mean = opto_trials[df_col_name].mean()
            ## Temp remove this
            # if df_col_name == "ChoiceCorrect" and animal_name == "All animals":
            #   _gain = 100*((opto_mean/cntrl_mean)-1)
            #   # print(f"Gain for {sess_info} {display_name}, {str(brain_region)}, {start_state} is: {_gain}")
            #   from opto.optopsych import optoPsychPlot
            #   _ax = optoPsychPlot(animal_name=f"{str(sess_info).replace('/','_')} - Gain: {_gain:.2f}%",
            #                       df=sess_df,
            #                       brain_region=brain_region, opto_config=opto_config,
            #                       by_animal=True, by_session=True,
            #                       combine_sides=False,
            #                       incld_grp_info_lgnd=False,
            #                       save_figs=False, save_prefix=None)
            #   from report.analysis import splitByDV
            #   scores = []
            #   for sub_df, clr in [(control_trials, 'k'), (opto_trials, 'r')]:
            #     df_by_dv = splitByDV(sub_df, combine_sides=False, periods=3)
            #     PsycY = [dv_df["ChoiceCorrect"].mean() * 100 for _, _, dv_df in df_by_dv]
            #     PsycX = [dv_single for dv_interval, dv_single, _ in df_by_dv]
            #     DVCount = [len(dv_df) for _, _, dv_df in df_by_dv]
            #     pts_count = np.sum(DVCount)
            #     weights = []
            #     for x, y, count in zip(PsycX, PsycY, DVCount):
            #       if count == 0:
            #         continue
            #       _ax.annotate(f"{y:.0f}% * Count: {count:,} = Weight: {y*count:.0f}",
            #                   (x+0.1, (100-y+5) if x < 0 else (y-5)), fontsize=10, c=clr)
            #       weights.append(y*count)
            #     score = np.nansum(weights)/pts_count
            #     _ax.annotate(f"Final weight: {[f'{w:.0f},' for w in weights]} = {np.nansum(weights):.0f}/Total Points: {pts_count} = {score:.2f}%",
            #                  (1.05, (40 if clr == 'k' else 60)), c=clr)
            #     scores.append(score)
            #   _ax.annotate(f"Gain = 100-(({scores[1]:.2f}/{scores[0]:.2f})-1) = {100*((scores[1]/scores[0])-1):.2f}%",
            #                (1.05, 25), c='b')
            #   # plt.show()
            #   psych_save = f"{brain_region}_s_{start_offset}_e_{dur}_gain_{_gain:.2f}_{str(sess_info).replace('/','Sess_')}"
            #   if _gain > -1:
            #     analysis.savePlot(save_prefix + f"/positive_gain/" + psych_save)
            #   else:
            #     analysis.savePlot(save_prefix + f"/negative_gain/" + psych_save)
            #   plt.close()
            # ##
          else:
            opto_mean = opto_trials[df_col_name].median()
          y_pts_opto.append(opto_mean)
          if secs_std:
            y_pts_cntrl_sem.append(control_trials[df_col_name].sem())
            y_pts_opto_sem.append(opto_trials[df_col_name].sem())
          used_opto += len(opto_trials)
          used_cntrl += len(control_trials)
          used_sess += 1
          # used_sess_infos |= by_animal_sess_info
          used_sess_df_li += [opto_trials, control_trials]
          used_sess_infos.add((animal_df.Name.unique()[0],
                               *[i.strip() for i in sess_info.split("-", 1)],
                               display_name, str(brain_region), start_state))
        if not len(y_pts_opto): # used_sess is for all animals, don't use it
          continue
        used_animals += 1
        # I'm sorry about the 15 next lines, this should be improved
        def rslv(pts):
          # if is_many_animals:
          #   return [np.asarray(pt).mean() for pt in pts]
          # else:
            return list(np.concatenate(pts))
        if mode == MetricMode.Raw:
          # TODO: There is a bug here
          final_y_pts = rslv([y_pts_cntrl, y_pts_opto])
        else:
          if not plot_actual_opto:
            gain = 100*((np.asarray(y_pts_opto)/np.asarray(y_pts_cntrl))-1)
          else:
            gain = 100*np.asarray(y_pts_opto)
          final_y_pts = rslv([gain])
        all_ys_means += final_y_pts
        if secs_std:
          all_ys_std += rslv([y_pts_cntrl_sem, y_pts_opto_sem])

      if not len(all_ys_means):
        continue
      all_ys_means = np.array(all_ys_means)
      all_ys_errs = stats.sem(all_ys_means) if len(all_ys_means) > 1 else 0
      if secs_std: all_ys_std = np.array(all_ys_std)

      Ys += (all_ys_means,)
      Yerrs += (all_ys_errs,)
      if secs_std: Ystds += (all_ys_std,)
      Xs.append(cur_x_pos)
      pvals.append(sessions_pval)
      cur_x_pos += BAR_WIDTH*BAR_SEP

      # if start_offset == 0 and dur == 0.35: # IF it's an early state
      #   state_clr = adjustColorLightness(region_color, 1.4)
      # elif start_offset == 0.65 and dur == 1: # If it's a late state
      #   state_clr = adjustColorLightness(region_color, 0.6)
      # else:
      #   state_clr = region_color
      state_clr = region_color

      if mode == MetricMode.Raw:
        colors += [adjustColorLightness(state_clr, 1.2),
                   adjustColorLightness(state_clr, 0.8)]
        Xs.append(cur_x_pos)
        cur_x_pos += BAR_WIDTH*BAR_SEP # Add one extra for the second column
      else:
        assert mode == MetricMode.Gain
        colors += [state_clr]
      # Should write, e.g: V1Bi - Stimulus_deliver (305 C/135 Opto trials)
      if start_offset == 0.3 and dur in [0.3, 0.6]:
        st_type = "RT"
      else:
        st_type = "FT"
      tick_label = f"{brain_region} "
      tick_done = True
      print("start state:", start_state, "dur:", dur, "start offset:", start_offset, "Brain region:", brain_region)
      if st_type == "RT":
        tick_label = f"{tick_label} {'Short' if dur == 0.3 else 'Long'} RT"
      else:
        assert st_type == "FT"
        if start_state == MatrixState.stimulus_delivery:
          if start_offset == 0 and dur == 0.35:
            tick_label = f"{tick_label} Early {start_state} FT"
          elif start_offset == 0.65 and (dur >= 0.35 or dur == -1):
            tick_label = f"{tick_label} Late {start_state} FT"
          elif start_offset == 0 and dur == -1:
            tick_label = f"{tick_label} All {start_state} FT"
          else:
            tick_done = False
        else:
          tick_done = False
      if not tick_done:
        start_time = "start" if start_offset == 0 else start_offset
        end_time = "end" if dur == -1 else start_offset + dur
        tick_label = f"{tick_label} {start_state} {start_time}:{end_time}"
      # tick_label = (f"{brain_region} - {start_state} "
      #               # f" - {start_state}" if start_state else ""
      #               f"T:{'start' if start_offset == 0 else start_offset}:"
      #               f"{'end' if dur == -1 else dur}")
      # x_ticks_labels.append(r"%s (%d $\bf{C}$/%d $\bf{Opto}$ trials)" % (
      #                       tick_label, len(control_trials), len(opto_config)))
      mice = "Mice" if used_animals > 1 else "Mouse"
      x_ticks_labels.append(rf"{tick_label} "
                  rf"($\bf{used_animals}$ {mice} / $\bf{used_sess}$ Sess - "
                  rf"$\bf{used_opto:,}$ opto-T / $\bf{used_cntrl:,}$ Cntrl-T)")
      x_ticks_pos.append(cur_x_pos-BAR_WIDTH*BAR_SEP)
      sort_dur = dur
      if sort_dur == -1: sort_dur = 1000
      org_sort.append((start_state, st_type, sort_dur,
                       start_offset, -brain_region))

  if not secs_std:
    Ystds = [0]*len(Xs)
  # http://stackoverflow.com/questions/3071415/efficient-method-to-calculate-the-rank-vector-of-a-list-in-python
  print("Re-enable this part to group same areas together")
  if True:
    new_sort = sorted(range(len(org_sort)), key=org_sort.__getitem__)
    # Re-sort everything except the x positions
    [Ys, Yerrs, Ystds, pvals, colors, x_ticks_labels] = [
    [li[idx] for idx in new_sort] for li in
    [Ys, Yerrs, Ystds, pvals, colors, x_ticks_labels]]

  fig, ax = plt.subplots()
  fig.set_size_inches((6, 8))
  # ax.set_aspect(0.3)
  for x,  y,  y_err, y_std, p_val, clr in zip(
      Xs, Ys, Yerrs, Ystds, pvals, colors):
    if unit == _PERCENT and mode != MetricMode.Gain:
      y = y * 100
    y_mean = y.mean()
    if mode == MetricMode.Gain:
      # ax.bar(x, y_mean, width=BAR_WIDTH*0.8, linestyle='-',
      #        color='none', edgecolor=clr)
      bplots = ax.boxplot(y, positions=[x], widths=BAR_WIDTH*0.8,
                          showmeans=True, meanline=True,
                          # showfliers=False, whis=0,
                          )
      for artist in ["boxes", "whiskers", "caps", "fliers"]:#, "medians", "means"]:
        plt.setp(bplots[artist], color=clr)
        for line in bplots[artist]:
          if artist != "fliers":
            line.set_color(clr)
          else:
            line.set_markeredgecolor(clr)

      pval_y_pos = np.quantile(y, q=0.75) + 1.5
    else:
      assert mode == MetricMode.Raw
      sign = 1 if y_mean > 0 else -1
      pval_y_pos = y_mean + (y_err + 0.1) * sign # TODO Fix
      # print("Idx", idx)
      # next_x = Xs[idx+1]
      # next_Ys = Ys[idx+1]
      # assert len(y) == len(next_Ys), f"{len(y)} != {len(next_Ys)}"
      print("x:", x)
      print("y:", y)
      # for y1, y2 in zip(Ys, next_Ys):
      #   ax.plot([x1, next_x], [y1, y2], color=clr, linewidth=0.5, alpha=0.3)
      ax.bar(x, y_mean, width=BAR_WIDTH*0.8, linestyle='-',
             color='none', edgecolor=clr)
    # ax.errorbar(x, y_mean, yerr=y_err, color=clr, linestyle='none', marker='o',
    #             elinewidth=3)
    # ax.errorbar([x-0.05]*len(y), y, yerr=y_std, color=clr, linestyle='none',
    #             alpha=0.2, marker='o', elinewidth=1)

    s = f"P={p_val:.3f}"
    ax.text(x + STEP/20, pval_y_pos, s, ha='left', va='bottom',
            fontsize=7)
    if p_val < 0.05:
      s = "***" if p_val <= 0.001 else ("**" if p_val < 0.01 else "*")
      ax.text(x + STEP/20, (pval_y_pos - 1.5), s, ha='left', va='bottom',
              fontsize=7)

  ax.axhline(0, color='black', linestyle='--', alpha=0.3)
  ax.set_xticks(x_ticks_pos)
  ax.set_xticklabels(x_ticks_labels, ha='right', rotation=45)
  ax.tick_params(axis='x', which='major', labelsize=7)
  # ax.set_title(f"{animal_name} - {display_name} Optogentics Trials")
  if mode == MetricMode.Gain:
    y_unit = f"Raw Optogenetics {unit}" if plot_actual_opto else "Percentage Gain"
  else:
    assert mode == MetricMode.Raw
    y_unit = unit
  ax.set_ylabel(f"Mean {display_name} ({y_unit})")
  if display_name == "Overall Performance":
    ax.set_ylim(bottom=-60, top=10)
  elif display_name == "Decision Time":
    # pass
    ax.set_ylim(bottom=-50, top=250)
  elif display_name == "Reaction Time":
    ax.set_ylim(bottom=-40, top=80)
  elif display_name == "Early-Withdrawal":
    ax.set_ylim(bottom=0, top=100)
  elif display_name == "Bias":
    ax.set_ylim(bottom=50, top=100)
  elif display_name == "Movement Time":
    ax.set_ylim(bottom=-100, top=200)
  ax.spines['top'].set_visible(False)
  ax.spines['right'].set_visible(False)
  ax.set_xlim(0, right=x+STEP/2)
  # from matplotlib.lines import Line2D
  # custom_lines = [
  #       Line2D([0],[0], color=adjustColorLightness("gray", amount=0.6), lw=4),
  #       Line2D([0],[0], color=adjustColorLightness("gray", amount=1.4), lw=4)]
  # ax.legend(custom_lines,
  #           ['Control Trials (dark shade)', 'Opto Trials (light shade)'],
  #           loc='upper right', fontsize='x-small')
  if save_figs:
    try:
        analysis.savePlot(save_prefix + f"{display_name}_{animal_name}")
    except Exception as e:
      print(f"Failed to save: {e}")
  plt.show()
  return used_sess_infos, used_sess_df_li


def _dominantBiasRatio(df):
  # df = df[df.ChoiceLeft.notnull()]
  # domininat_side_ratio = df.ChoiceLeft.sum()/len(df)
  domininat_side_ratio = analysis._calcLeftBias(df)
  if domininat_side_ratio < 0.5:
    domininat_side_ratio = 1 - domininat_side_ratio
  return domininat_side_ratio

class TTestDataMetric(Enum):
  Mean = auto()
  Median = auto()

def twoTailedTTest(df, *, df_col_name, metric : TTestDataMetric,
                   plot_brain_region, plot_animal_name, plot_display_name,
                   plot_start_state):
  df = df[df[df_col_name].notnull()]
  _, opto_trials = commonOptoSectionFilter(df,
                                           by_animal=True,
                                           by_session=True)
  if not len(opto_trials):
    print(f"TTTest Early bailout {plot_display_name} {plot_brain_region} - "
          f"{plot_start_state} {plot_animal_name}")
    return np.nan, np.nan, set(), set()
  grps_cntrl_opto_means_animals = []
  grps_cntrl_opto_means_sessions = []
  def calcGrpMean(grp_df, by_animal, by_session, info):
    control_trials, opto_trials = commonOptoSectionFilter(grp_df,
                                                          by_animal=by_animal,
                                                          by_session=by_session)
    if not len(opto_trials):
      if not by_session:
        print(f"TTTest Skipping test for {plot_display_name} "
              f"{plot_brain_region} {plot_start_state} {info}")
      return None
    data_cntrl = control_trials.toDF()[df_col_name]
    data_opto = opto_trials.toDF()[df_col_name]
    control_trials_mean = data_cntrl.mean() if metric == TTestDataMetric.Mean \
                                            else data_cntrl.median()
    opto_trials_mean = data_opto.mean() if metric == TTestDataMetric.Mean \
                                        else data_opto.median()
    return (control_trials_mean, opto_trials_mean)

  # is_ordinal = len(df[df_col_name].unique()) == 2
  # if not is_ordinal: # It's not (binary/categorial) dataset
  #   mean_trials = calcGrpMean(df,  by_session=False, by_animal=False)
  #   if mean_trials
  by_animal_sess_info = set()
  by_sess_sess_info = set()
  for animal_name, animal_df in df.groupby(df.Name):
    mean_animal = calcGrpMean(animal_df, by_animal=True, by_session=False,
                              info=animal_name)
    if mean_animal:
      grps_cntrl_opto_means_animals.append(mean_animal)
    for sess_info, sess_df in grpBySess(animal_df):
      mean_sess = calcGrpMean(sess_df, by_animal=True, by_session=True,
                     info=f"{animal_name} - {sess_info[0]} Sess-{sess_info[1]}")
      if mean_sess:
        grps_cntrl_opto_means_sessions.append(mean_sess)
      for mean_, set_ in ([mean_animal, by_animal_sess_info],
                          [mean_sess, by_sess_sess_info]):
        if mean_:
          set_.add((animal_name, *sess_info, plot_display_name,
                    str(plot_brain_region), plot_start_state))

  print(f"{plot_display_name} {plot_brain_region} {plot_start_state} "
        f"{plot_animal_name} - Len: {len(grps_cntrl_opto_means_sessions)}")
  from scipy import stats
  def calcPVal(grps_cntrl_opto_means, name):
    cntrl_means, opto_means = zip(*grps_cntrl_opto_means)
    statistic, pvalue = stats.ttest_rel(cntrl_means, opto_means)
    print(f"\tAcross {name} (Sample size: {len(cntrl_means)}) - "
          f"p-value: {pvalue}")
    return pvalue
  if len(grps_cntrl_opto_means_animals):
    animals_pval = calcPVal(grps_cntrl_opto_means_animals, "Animals")
  else:
    animals_pval = None
  sessions_pval = calcPVal(grps_cntrl_opto_means_sessions, "Sessions")
  # if len(calcPVal(grps_cntrl_opto_trials)):
  #   calcPVal(grps_cntrl_opto_trials, "Sessions")
  return animals_pval, sessions_pval, by_animal_sess_info, by_sess_sess_info

def fisherExactTest(animal_df, *, df_col_name, plot_brain_region, plot_animal_name,
                    plot_display_name, plot_start_state):
  animal_df = animal_df[animal_df[df_col_name].notnull()]
  control_trials, opto_trials = commonOptoSectionFilter(animal_df,
                                                        by_animal=False,
                                                        by_session=False)
  if not len(opto_trials):
    print("Skipping test")
    return
  else:
    print("Continuing test")
  control_trials = control_trials.toDF()[df_col_name].astype(np.bool)
  opto_trials = opto_trials.toDF()[df_col_name].astype(np.bool)
  count = np.array([len(opto_trials[opto_trials == True]),
                  len(control_trials[control_trials == True])])
  nobs = np.array([len(opto_trials), len(control_trials)])
  # print(f"contingency_table: {contingency_table}")
  print(f"{plot_display_name} {plot_brain_region} {plot_start_state} "
        f"{plot_animal_name}")
  import scipy.stats as stats
  oddsratio, pvalue = stats.fisher_exact([count, nobs - count])
  print(f"\t- fisher test p-value: {pvalue} - oddsratio: {oddsratio}")
  chi2, p, dof, expected = stats.chi2_contingency([count, nobs - count],
                                                  correction = False)
  print(f"\t- Chi-2  test p-value: {p}- Chi2: {chi2} - dof: {dof}")
  from statsmodels.stats.proportion import proportions_chisquare
  chi2, pval , expected = proportions_chisquare(count, nobs)
  print(f"\t- Chi-2  test p-value: {pval} - Chi2: {chi2}")
  from statsmodels.stats.proportion import proportions_ztest
  stat, pval = proportions_ztest(count, nobs)
  print(f"\t- Z-test test p-value: {pval} - stat: {stat}")

def gainDistr(animal_df, df_col_name, plot, plot_brain_region, plot_start_state,
              plot_animal_name, plot_display_name, save_fig, save_prefix):
  animal_df = animal_df[animal_df[df_col_name].notnull()]
  control_trials, opto_trials = commonOptoSectionFilter(animal_df,
                                                        by_animal=False,
                                                        by_session=False)
  if not len(opto_trials):
    return
  control_trials, opto_trials = control_trials.toDF(), opto_trials.toDF()
  mean_cntrl = control_trials[df_col_name].mean()
  mean_opto = opto_trials[df_col_name].mean()
  # TODO: Handle non-percent differently
  print("Mean cntrl:", mean_cntrl)
  print("Mean mean_opto:", mean_opto)
  obsv_gain = ((mean_opto/mean_cntrl)-1)
  is_positive_gain = obsv_gain > 0
  num_cycles = 1000000
  col = animal_df[df_col_name]
  # if list(col.unique()) == [0, 1] or list(col.unique()) == [1, 0]: # Its a binary values
  #   col = np.log(col + 1)
  #   print("Converted")
  # print("Col: ", col)
  len_control_trials, len_opto_trials = (len(control_trials), len(opto_trials))
  if True:
    # import pyximport; pyximport.install()
    gains_distr = np.empty(num_cycles, dtype=np.float64)
    from . import bootstrap
    col = col.to_numpy().astype(np.float64)
    gains_distr = bootstrap.bootstrap(col, gains_distr, num_cycles,
                                      len_control_trials, len_opto_trials)
  else:
    gains_distr = _hotLoop(col, num_cycles, len_control_trials, len_opto_trials)
  # print("gains_distr:", gains_distr)
  gains_distr.sort()
  cmp = np.greater_equal if is_positive_gain else np.less_equal
  # TODO: Is this wrong? are we take all the equal or less than events?
  new_p = len(gains_distr[cmp(gains_distr, obsv_gain)])/len(gains_distr)
  # old_p = p/NUM_CYCLES
  # print(f"Old p: {old_p} - new p: {new_p} - old == new?: {old_p == new_p}")
  print(f"P for {df_col_name} is: {new_p}")
  if plot:
    nan_count = np.sum(np.isnan(gains_distr))
    if nan_count:
      print(f"*********Found {nan_count} nans")
    inf_count = np.sum(np.isinf(gains_distr))
    if inf_count:
      print(f"************Found {inf_count} inf:", gains_distr)
      gains_distr[np.isinf(gains_distr)] = gains_distr[
                                                   ~np.isinf(gains_distr)].max()
      print("gains now:", gains_distr)
    # gains_distr = gains_distr[~np.isinf(gains_distr)]
    # gains_distr.sort() # Not needed for hist, but might help, but needed for CI
    # print(f"Gain distr: {gains_distr}")
    ax = plt.axes()
    # Can I assume that bin 95 will be the 95 percentil?, no I can't
    N, bins, patches = ax.hist(gains_distr, color='b', bins=int(1000))
    p_sig = np.nanpercentile(gains_distr, [95, 99, 99.9] if is_positive_gain
                                     else [5, 1, 0.1])
    print(f"P95: {p_sig[0]} P99: {p_sig[1]} - P99.9: {p_sig[2]}")
    brdr_idx = 0 if is_positive_gain else -1
    if is_positive_gain:
      p_bin_95, p_bin_99, p_bin_999 = [np.where(bins >= p)[0][0] for p in p_sig]
      slices = (patches[p_bin_95:p_bin_99],
                patches[p_bin_99:p_bin_999],
                patches[p_bin_999:])
      # print(f"col: {df_col_name} - 95idx: {p_bin_95} - "
      #       f"99idx: {p_bin_99} - 99.9idx: {p_bin_999}")
    else:
      p_bin_5, p_bin_1, p_bin_01 = [np.where(bins <= p)[0][-1] for p in p_sig]
      slices = (patches[p_bin_1:p_bin_5],
                patches[p_bin_01:p_bin_1],
                patches[:p_bin_01])
      print(f"col: {df_col_name} - 5idx: {p_bin_5} - "
            f"1idx: {p_bin_1} - 0.1idx: {p_bin_01}")

    for sub_patches, clr in [(slices[0], 'y'), (slices[1], 'r'),
                             (slices[2], 'k')]:
      [patch.set_facecolor(clr) for patch in sub_patches]
    ax.axvline(obsv_gain, linestyle='dashed', color='gray',
               label="Observed value")
    ax.set_title(f"{plot_brain_region} - {plot_start_state} {plot_animal_name} "
                 f"{plot_display_name} gains bootstrap distr",
                 fontsize="x-small")
    ax.set_xlabel(f"Gains distribution ({len_control_trials} control trials/ "
                  f"{len_opto_trials} opto trials) - P={new_p}")
    ax.set_ylabel(f"Histogram count - {num_cycles:,} cycles")
    if save_fig:
      analysis.savePlot(f"{save_prefix}gains_distr/{plot_display_name}_"+
                  f"{plot_brain_region}_{plot_start_state}_{plot_animal_name}")
    plt.show()
  return gains_distr

# import pyximport; pyximport.install()
def _hotLoop(col, num_cycles, len_control_trials, len_opto_trials):
  from report.utils import bootStrap
  from tqdm import tqdm
  # p = 0
  grps_sizes_li = (len_control_trials, len_opto_trials)
  gains_distr = np.empty(num_cycles)
  min_positive_val = 1/len_control_trials
  count_nonzero = np.count_nonzero

  for idx in tqdm(np.arange(num_cycles)):
    col_cntrl, col_opto = bootStrap(col, grps_sizes_li=grps_sizes_li,
                                    with_replacement=True)
    cntrl_mean = col_cntrl.mean()
    # cntrl_mean2 = col_cntrl.mean()
    zero_if_zero = count_nonzero(cntrl_mean)
    cntrl_mean = zero_if_zero*cntrl_mean + (1-zero_if_zero)*min_positive_val
    # if cntrl_mean2 == 0:
    #   cntrl_mean2 = min_positive_val
    # assert cntrl_mean2 == cntrl_mean
    # test_gain = ((col_opto.mean()/cntrl_mean)-1)
    gains_distr[idx] = ((col_opto.mean()/cntrl_mean)-1)
    # if (is_positive_gain and test_gain > obsv_gain) or (
    #     not is_positive_gain and test_gain < obsv_gain):
    #   p += 1
  return gains_distr

def animalOptoMetrics(animal_name, animal_df, *, is_many_animals, mode,
                      save_figs, save_prefix):
  used_sess_infos = set()
  used_sess_df_li = []
  for df_col_name, display_name, unit in [
                        ("ChoiceCorrect", "Overall Performance", _PERCENT),
                        ("calcDecisionTime", "Decision Time", _SECOND),
                        ("ST", "Reaction Time", _SECOND),
                        ("EarlyWithdrawal", "Early-Withdrawal", _PERCENT),
                        ("ChoiceCorrect", "Bias", _PERCENT),
                        ("calcMovementTime", "Movement Time", _SECOND),
                        ]:
    opto_df = animal_df
    if df_col_name == "calcDecisionTime":
      opto_df = opto_df[
                      ((opto_df.GUI_MinSampleType == MinSamplingType.FixMin) &
                      (opto_df.GUI_StimulusTime <= opto_df.GUI_MinSampleMin)) |
                      # Second condition
                      ((opto_df.GUI_MinSampleType == MinSamplingType.AutoIncr) &
                        (opto_df.GUI_StimulusTime <= opto_df.GUI_MinSampleMax))]
    elif df_col_name == "ST":
      opto_df = opto_df[
                      ((opto_df.GUI_MinSampleType == MinSamplingType.FixMin) &
                      (opto_df.GUI_StimulusTime > opto_df.GUI_MinSampleMin)) |
                      # Second condition
                      ((opto_df.GUI_MinSampleType == MinSamplingType.AutoIncr) &
                        (opto_df.GUI_StimulusTime > opto_df.GUI_MinSampleMax))]

    opto_chain = ChainedGrpBy(opto_df)
    tup = \
      processAnimalMetric(animal_name=animal_name, df_col_name=df_col_name,
                          display_name=display_name, unit=unit, mode=mode,
                          opto_chain=opto_chain,
                          is_many_animals=is_many_animals,
                          save_figs=save_figs, save_prefix=save_prefix)
    used_sess_infos |= tup[0]
    used_sess_df_li += tup[1]
  return used_sess_infos, used_sess_df_li

def optoMetrics(df, *, mode, save_figs, save_prefix):
  ALL_ANIMALS="All animals"
  used_sess_infos = set()
  used_sess_df_li = []
  for exp_type, sub_df in df.groupby(df.GUI_ExperimentType):
    exp_str = ExperimentType(exp_type) # It's an enum but we will use as str
    if len(sub_df.Name.unique()) > 1:
      used_sess, sess_li = animalOptoMetrics(
                        ALL_ANIMALS, sub_df, is_many_animals=True, mode=mode,
                        save_figs=save_figs,
                        save_prefix=f"{save_prefix}/{ALL_ANIMALS}/{exp_str}_")
      used_sess_infos |= set(
                            [(exp_str, ALL_ANIMALS, *inf) for inf in used_sess])
      used_sess_df_li += sess_li
    # for animal_name, animal_df in sub_df.groupby(sub_df.Name):
    #   used_sess, sess_li = animalOptoMetrics(
    #                     animal_name, animal_df, is_many_animals=False,
    #                     mode=mode, save_figs=save_figs,
    #                     save_prefix=f"{save_prefix}/{animal_name}/{exp_str}_")
    #   used_sess_infos |= set(
    #                         [(exp_str, animal_name, *inf) for inf in used_sess])
    #   used_sess_df_li += sess_li
  return used_sess_infos, used_sess_df_li
