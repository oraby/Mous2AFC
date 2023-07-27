function [IsNextCatch, CatchOmegaTrack] = HandleCatchTrials(PrevTrial,...
                                                 NextTrial, GUI, CatchOmegaTrack)

function [CatchRowIdx, CatchColIdx] = GetCatchIdx(StimulusOmega)
    if GUI.CatchSepLeftRight
        if StimulusOmega < 0.5
            CatchColIdx  = 1;
            StimulusOmega = -StimulusOmega + 1;
        else
            CatchColIdx  = 2;
        end
    else % Reduce both sides
        CatchColIdx = [1 2];
        if StimulusOmega < 0.5
            StimulusOmega = -StimulusOmega + 1;
        end
    end
    [MinVal, CatchRowIdx] = min(abs(GUI.CatchTable.Omega - StimulusOmega*100));
    if MinVal ~= 0
       disp('Unexpected min val found, are you using beta distribution?...');
    end
end

function ProcessPrevTrial()
    % Handle the previos trial counters
    [CatchRowIdx, CatchColIdx] = GetCatchIdx(PrevTrial.StimulusOmega);
    if PrevTrial.CatchTrial && (PrevTrial.ChoiceCorrect == 1 ||...
                                ~GUI.CatchCorrectOnlyCounts)
        CatchOmegaTrack(CatchRowIdx, CatchColIdx) = inf; % Reset counters
    else
        CatchOmegaTrack(CatchRowIdx, CatchColIdx) = ... % Reduce counter by 1
                                   CatchOmegaTrack(CatchRowIdx, CatchColIdx) - 1;
    end
end

% Assume initially that it's not a catch trial
IsNextCatch = false;
if NextTrial.TrialNumber < GUI.StartEasyTrials
    return
end

ProcessPrevTrial();
[CatchRowIdx, CatchColIdx] = GetCatchIdx(NextTrial.StimulusOmega);
CatchEveryStart = GUI.CatchTable.EveryMin(CatchRowIdx);
CatchEveryEnd = GUI.CatchTable.EveryMax(CatchRowIdx);
if CatchEveryStart > 0 && CatchEveryStart <= CatchEveryEnd % i.e valid GUI fields
    CurCatchCount = CatchOmegaTrack(CatchRowIdx, 1:2);
    % Check if new catch value is added or current catch value is reduced
    InvalidCounts = CurCatchCount > CatchEveryEnd;
    if any(InvalidCounts)
        CatchNewCount = randi([CatchEveryStart  CatchEveryEnd], 1,...
                               sum(InvalidCounts));
        CatchOmegaTrack(CatchRowIdx, InvalidCounts) = CatchNewCount;
        if ~GUI.CatchSepLeftRight % Right and left should be the same
            CatchOmegaTrack(CatchRowIdx, 1) = CatchOmegaTrack(CatchRowIdx, 2);
        end
    end
    % A catch counter can have -ve value if it was skipped before
    if any(CatchOmegaTrack(CatchRowIdx, CatchColIdx) <= 0) && ...
       (PrevTrial.ChoiceCorrect == 1 || GUI.CatchCanComeAfterErr)
        IsNextCatch = true;
    end
end
end
