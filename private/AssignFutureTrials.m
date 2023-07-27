function [Trials, startFrom] = AssignFutureTrials(Trials, GUI, startFrom,...
                                                  NumTrialsToGenerate, LeftBias,...
                                                  SecExpType)
function [OneZeroArr] = ControlledRandom(prob)
    NumPositiveTrials = NumTrialsToGenerate*prob;
    % If it's not a whole number, then we will generate one extra entry and
    % will shuffle the array, and wil drop the last extra entry (if any)
    OneZeroArr = [ones(1, ceil(NumPositiveTrials))...
                  zeros(1, ceil(NumTrialsToGenerate-NumPositiveTrials))];
    OneZeroArr = OneZeroArr(randperm(numel(OneZeroArr)));
    OneZeroArr = OneZeroArr(1:NumTrialsToGenerate);
end
%% Generate guaranteed probability distribution over the few trials we have
IsLeftRewarded = ControlledRandom(1-LeftBias);
SecExpIsUsed = ControlledRandom(GUI.SecExpUseProb);
SecExpIsUsedAlone = ControlledRandom(GUI.SecExpProbUseAloneProb);
SecExpIsUsedAlone(SecExpIsUsed == 0) = nan;
SecExpDirIsInversed = ControlledRandom(GUI.SecExpInverseStimDirRatio);
SecExpDirIsInversed(SecExpIsUsed == 0) = nan;
%% Make future trials
lastidx = startFrom;
for a = 0:NumTrialsToGenerate-1
    % If it's a fifty-fifty trial, then place stimulus in the middle
    if rand(1,1) < GUI.Percent50Fifty && (lastidx+a) > GUI.StartEasyTrials % 50Fifty trials
        StimulusOmega = 0.5;
    else
        if GUI.StimulusSelectionCriteria == StimulusSelectionCriteria.BetaDistribution
            % Divide beta by 4 if we are in an easy trial
            BetaDiv = iff((lastidx+a) <= GUI.StartEasyTrials, 4, 1);
            StimulusOmega = betarnd(GUI.BetaDistAlphaNBeta/BetaDiv,GUI.BetaDistAlphaNBeta/BetaDiv,1,1);
            StimulusOmega = iff(StimulusOmega < 0.1, 0.1, StimulusOmega); %prevent extreme values
            StimulusOmega = iff(StimulusOmega > 0.9, 0.9, StimulusOmega); %prevent extreme values
        elseif GUI.StimulusSelectionCriteria == StimulusSelectionCriteria.DiscretePairs
            if (lastidx+a) <= GUI.StartEasyTrials
                index = find(GUI.OmegaTable.OmegaProb > 0, 1);
                StimulusOmega = GUI.OmegaTable.Omega(index)/100;
            else
                % Choose a value randomly given the each value probability
                StimulusOmega = randsample(GUI.OmegaTable.Omega,1,1,GUI.OmegaTable.OmegaProb)/100;
            end
        else
            assert(false, 'Unexpected StimulusSelectionCriteria');
        end
        % In case of beta distribution, our distribution is symmetric,
        % so prob < 0.5 is == prob > 0.5, so we can just pick the value
        % that corrects the bias
        if (IsLeftRewarded(a+1) && StimulusOmega < 0.5) || (~IsLeftRewarded(a+1) && StimulusOmega >= 0.5)
            StimulusOmega = -StimulusOmega + 1;
        end
    end

    Trial = Trials(lastidx+a);
    Trial.StimulusOmega = StimulusOmega;
    if StimulusOmega ~= 0.5
        Trial.LeftRewarded = StimulusOmega > 0.5;
    else
        Trial.LeftRewarded = rand < 0.5;
    end
    Trial.SecExpIsUsed = SecExpIsUsed(a+1);
    Trial.SecExpIsUsedAlone = SecExpIsUsedAlone(a+1);
    Trial.SecExpDirIsInversed = SecExpDirIsInversed(a+1);
    Trials(lastidx+a) = Trial;
end%for a=1:5
startFrom = startFrom + NumTrialsToGenerate;

end
