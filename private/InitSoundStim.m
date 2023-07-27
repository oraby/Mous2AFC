function soundParams = InitSoundStim(samplename)
[projdir,~,~] = fileparts(fileparts(mfilename('fullpath')))
audfilepath = strcat(projdir, filesep, 'audstim', filesep, samplename, '.wav');
[wavedata, samplerate] = psychwavread(audfilepath);
nrchannels = size(wavedata,2);
assert(nrchannels == 2, "Expected stereo wave-file");
reallyneedlowlatency=1;
try
    InitializePsychSound(reallyneedlowlatency);
catch
    % Probably no sound card on system
    fprintf('\nFailed sto initialize sound. Creating dummy struct...\n');
    soundParams = struct;
    return
end
device = [];
mode = 1; %playback
reqlatencyclass = 1;
bubuffersize = 0;%32;
suggestedLatency = 0;%.001; % In seconds
try
    PsychPortAudio('Close'); % Try to close old handle
catch
end
% Next try/catch is taken from psychtoolbox's BasicSoundOutputDemo
try
    % Try with the frequency we wanted:
    pahandle = PsychPortAudio('Open', device, mode, reqlatencyclass,...
                              samplerate, nrchannels, bubuffersize,...
                              suggestedLatency);
catch
    try
        % Failed. Retry with default frequency as suggested by device:
        fprintf('\nCould not open device at wanted playback frequency of %i Hz. Will retry with device default frequency.\n');
        fprintf('Sound may sound a bit out of tune, ...\n\n');
        psychlasterror('reset');
        pahandle = PsychPortAudio('Open', device, mode, reqlatencyclass,...
                                  samplerate, nrchannels, bubuffersize,...
                                  suggestedLatency);
    catch
        fprintf('Failed to initialize sound..\n\n');
        soundParams = struct;
        return
    end
end
soundParams = struct;
soundParams.pahandle = pahandle;
soundParams.origWav = wavedata'; % Psychtoolbox expects each row as a channel
end
