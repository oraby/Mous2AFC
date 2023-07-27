function [NextTrial, GUI, CurTimer] = GenNextTrial(NextTrial, NextTrialIdx,...
            GUI, PrimaryExpType, SecExpType, CurTimer, LastSuccessCatchTial,...
            CatchCount, IsLastTrialRewarded, NextTrialBlockNum)
% Tracks the amount of water the animal received up tp this point
% TODO: Check if RewardReceivedTotal is needed and calculate it using
% CalcRewObtained() function.
NextTrial.RewardReceivedTotal = 0; % We will updated later
NextTrial.RewardMagnitude = GUI.RewardAmount*[1,1];
NextTrial.CenterPortRewAmount = GUI.CenterPortRewAmount;
NextTrial.PreStimCntrReward = GUI.PreStimuDelayCntrReward;
% Block number assignment requires No computation, but centralizes all
% trial generation information in one place
NextTrial.BlockNum = NextTrialBlockNum;

tic;
[NextTrial, DV] = CalcTrialDV(NextTrial, PrimaryExpType,...
                              NextTrial.StimulusOmega);
NextTrial.DV = DV;
% cross-modality difficulty for plotting
%  0 <= (left - right) / (left + right) <= 1
NextTrial.DV = DV;

% Secondary Experiment DV can be none or another value.
if rand(1,1) < GUI.SecExpUseProb
    NextTrial = GenSecExp(NextTrial, SecExpType,...
                          GUI.SecExpStimIntensity, GUI.SecExpStimDir,...
                          GUI.OmegaTable);
else
    NextTrial.SecDV = NaN;
end
CurTimer.customSecDV = toc; tic;

% Set current stimulus for next trial
GUI.CurrentStim = StimDirStr(PrimaryExpType, NextTrial.DV, SecExpType,...
                             NextTrial.SecDV);
%determine if optogentics trial
OptoEnabled = rand(1,1) <  GUI.OptoProb;
if NextTrialIdx < GUI.StartEasyTrials
    OptoEnabled = false;
end
NextTrial.OptoEnabled = OptoEnabled;
GUI.IsOptoTrial = iff(OptoEnabled, 'true', 'false');

% determine if catch trial
if NextTrialIdx < GUI.StartEasyTrials || GUI.PercentCatch == 0
    NextTrial.CatchTrial = false;
else
    every_n_trials = round(1/GUI.PercentCatch);
    limit = round(every_n_trials*0.2);
    lower_limit = every_n_trials - limit;
    upper_limit = every_n_trials + limit;
    if ~IsLastTrialRewarded || NextTrialIdx < LastSuccessCatchTial + lower_limit
        NextTrial.CatchTrial = false;
    elseif NextTrialIdx < LastSuccessCatchTial + upper_limit
        %TODO: If OmegaProb changed since last time, then redo it
        non_zero_prob = GUI.OmegaTable.Omega(GUI.OmegaTable.OmegaProb > 0);
        non_zero_prob = [1-(non_zero_prob'/100), flip(non_zero_prob'/100)];
        active_stim_idxs = GetCatchStimIdx(non_zero_prob);
        cur_stim_idx = GetCatchStimIdx(NextTrial.StimulusOmega);
        min_catch_counts = min(CatchCount(active_stim_idxs));
        min_catch_idxs = intersect(active_stim_idxs,...
                                   find(floor(CatchCount) == min_catch_counts));
        NextTrial.CatchTrial = any(min_catch_idxs == cur_stim_idx);
    else
        NextTrial.CatchTrial = true;
    end
end
% Create as char vector rather than string so that GUI sync doesn't complain
GUI.IsCatch = iff(NextTrial.CatchTrial, 'true', 'false');

% Determine if Forced LED trial:
if GUI.PortLEDtoCueReward
    NextTrial.ForcedLEDTrial = rand(1,1) < GUI.PercentForcedLEDTrial;
else
    NextTrial.ForcedLEDTrial = false;
end
% Calculate RDK pulses. Ideally, I would calculate this in CalcDV() function,
% but I would have to pass a lot of GUI parameters to make this work.
RDKCohr = nan;
if PrimaryExpType == ExperimentType.RandomDots
    RDKCohr = abs(NextTrial.DV);
elseif ~isnan(NextTrial.SecDV) && SecExpType == ExperimentType.RandomDots
    RDKCohr = abs(NextTrial.SecDV);
end
if ~isnan(RDKCohr)
    % Create either a positive or negative pulse coherence.
    % If GUI pulse value between 0 -> 100 then it's either randomly positive or
    % negative.
    % If it's < 0 then it's negative.
    % And if it's 100 >, then subtract 100 and use the remaining positive value
    is_pos_rand = rand() >= 0.5;
    PulseCohr = 0;
    if GUI.dotsPulseCohr > 100 || (GUI.dotsPulseCohr > 0 && is_pos_rand)
      PulseCohr = GUI.dotsPulseCohr;
      if PulseCohr > 100
        PulseCohr = PulseCohr - 100;
      end
      % pulseCohr is +ve, so make sure that we have enough coherence to add.
      PulseCohr = min(PulseCohr/100, 1-RDKCohr);
    elseif GUI.dotsPulseCohr < 0 || (GUI.dotsPulseCohr <= 100 && ~is_pos_rand)
      % pulseCohr is -ve, so make sure that we have enough coherence to
      % subtract.
      PulseCohr = max(abs(GUI.dotsPulseCohr)/-100, -RDKCohr);
    end
    % Now check if we should actually use the pulse coherence
    if rand() < GUI.dotsPulseProb && PulseCohr
        NextTrial.DotsPulseCoherence = PulseCohr;
        % For a pulse to start and finish, it borrows and lends coherences from
        % the other sides. For a coherence to start
        if GUI.dotsPulseOffset_Neg1Rnd == -1
            st = max(GUI.MinSample, GUI.StimulusTime);
            NextTrial.DotsPulseStart = rand() * (st - GUI.dotLifetimeSecs);
        else
            NextTrial.DotsPulseStart = GUI.dotsPulseOffset_Neg1Rnd;
        end
        NextTrial.DotsPulseDur = GUI.dotsPulseMinDur;
    else
        NextTrial.DotsPulseCoherence = nan; % It should be already nan by default
    end
end
if ~isnan(NextTrial.DotsPulseCoherence) && NextTrial.DotsPulseCoherence
    GUI.LastPulse = sprintf('P=%s%d%% S=%.2fsec T=%d',...
        iff(NextTrial.DotsPulseCoherence < 0, '-', '+'),...
            round(abs(NextTrial.DotsPulseCoherence*100)),...
            NextTrial.DotsPulseStart,...
        NextTrial.TrialNumber);
else
    GUI.LastPulse  = sprintf('Not Used - Trial Num=%d', NextTrial.TrialNumber);
end
CurTimer.customCatchNForceLed = toc;

end
