function RewardObtained = CalcRewObtained(DataCustom, iTrial)
Trials = DataCustom.Trials(1:iTrial);
RewardObtained = sum([Trials.RewardReceivedTotal]);
end

