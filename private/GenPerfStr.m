function [PerfStr, AllPerfStr, PrimPerfStr, PrimAllPerfStr, SecPerfStr,...
          SecAllPerfStr] = GenPerfStr(ChoiceCorrectTrials, PrimDV, SecDV,...
                                      IsLeftChoice)

function Perfs = processSlice(ChoiceCorrectTrialsSlice, PrimDVSlice,...
                              SecDVSlice, IsLeftChoiceSlice)
PrimExpCorrectTrials = NaN(size(ChoiceCorrectTrialsSlice));
NonNanDV = ~isnan(PrimDVSlice);
PrimDVTotaCount = sum(NonNanDV);
% The goal here is to copy nan-trials to the new array. We will overwrite
% the non-nan trials.
PrimExpCorrectTrials(NonNanDV) = IsLeftChoiceSlice(NonNanDV);
PrimDVChoiceCount = sum(~isnan(PrimExpCorrectTrials));
PrimExpCorrectTrials = (PrimExpCorrectTrials == 1 & PrimDVSlice >= 0.5) |...
                       (PrimExpCorrectTrials == 0 & PrimDVSlice < 0.5);
SecExpCorrectTrials = NaN(size(ChoiceCorrectTrialsSlice));
NonNanDV = ~isnan(SecDVSlice);
SecDVTotalCount = sum(NonNanDV);
% Same as the comment above
SecExpCorrectTrials(NonNanDV) = IsLeftChoiceSlice(NonNanDV);
SecDVChoiceCount = sum(~isnan(SecExpCorrectTrials));
SecExpCorrectTrials = (SecExpCorrectTrials == 1 & SecDVSlice >= 0.5) |...
                      (SecExpCorrectTrials == 0 & SecDVSlice < 0.5);
Grps = {ChoiceCorrectTrialsSlice, PrimExpCorrectTrials, SecExpCorrectTrials};
TotalCounts = {length(ChoiceCorrectTrialsSlice), PrimDVTotaCount,...
               SecDVTotalCount};
ChoicMadeCounts = {sum(~isnan(ChoiceCorrectTrialsSlice)), PrimDVChoiceCount,...
                   SecDVChoiceCount};
Perfs = NaN(3, 4);
for idx = 1:length(Grps)
    AllPerfLen = TotalCounts{idx};
    PerfLen = ChoicMadeCounts{idx};
    if AllPerfLen >= 1
        CurGrp = Grps{idx};
        CorrectChoiceCount = sum(CurGrp == 1);
        AllPerf = 100*CorrectChoiceCount/AllPerfLen;
        if PerfLen >= 1
            Perf = 100*CorrectChoiceCount/PerfLen;
        else
            Perf = NaN;
        end
    else
        AllPerf = NaN;
        Perf = NaN;
    end
    Perfs(idx,:) = [Perf, PerfLen, AllPerf, AllPerfLen];
end
end


function Str = fmtStr(Perf, PerfLen, LastPerf, LastPerfLen)
    if PerfLen >= 1
        if LastPerfLen >= 1
            Str = sprintf('%.2f%%/%dT - %.2f%%/%dT', Perf, PerfLen, LastPerf,...
                          LastPerfLen);
        else
            Str = sprintf('%.2f%%/%dT', Perf, PerfLen);
        end
    else
        Str = '(Not trials to compute)';
    end
end

LAST_NUM_TRIALS = 20;
WholePerfs = processSlice(ChoiceCorrectTrials, PrimDV, SecDV, IsLeftChoice);
if length(ChoiceCorrectTrials) >= LAST_NUM_TRIALS
    End = length(ChoiceCorrectTrials);
    Start = End - LAST_NUM_TRIALS + 1;
    ChoiceCorrectTrials = ChoiceCorrectTrials(Start:End);
    PrimDV = PrimDV(Start:End);
    SecDV = SecDV(Start:End);
    IsLeftChoice = IsLeftChoice(Start:End);
    LastPerfs = processSlice(ChoiceCorrectTrials, PrimDV, SecDV, IsLeftChoice);
else
    LastPerfs = zeros(3, 4);
end

% The size of each of the following is 3x4. Rows are: 1. Everything,
% 2.Prim, 3. Sec. Columns are: 1. Sess %, 2. Sess % #Trials, 3. Last %,
% 4. Last % #Trials
Perfs = [WholePerfs(:,1:2) LastPerfs(:,1:2)];
AllPerfs = [WholePerfs(:,3:4) LastPerfs(:,3:4)];

PerfStr =     fmtStr(Perfs(1,1), Perfs(1,2), Perfs(1,3), Perfs(1,4));
PrimPerfStr = fmtStr(Perfs(2,1), Perfs(2,2), Perfs(2,3), Perfs(2,4));
SecPerfStr =  fmtStr(Perfs(3,1), Perfs(3,2), Perfs(3,3), Perfs(3,4));
% Now dow it for AllPerfs
AllPerfStr =     fmtStr(AllPerfs(1,1), AllPerfs(1,2), AllPerfs(1,3), AllPerfs(1,4));
PrimAllPerfStr = fmtStr(AllPerfs(2,1), AllPerfs(2,2), AllPerfs(2,3), AllPerfs(2,4));
SecAllPerfStr =  fmtStr(AllPerfs(3,1), AllPerfs(3,2), AllPerfs(3,3), AllPerfs(3,4));
end
