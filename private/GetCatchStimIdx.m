function idx = GetCatchStimIdx(DV)
    % We multiply by 10 as Omegatable has 10 entries and try to map the DV to
    % the correct bucket. Finally, add one to start at Matlab's 1-based idxs.
    idx = 1 + floor((1-abs(DV))*10);
end
