function SoftCodeHandler(softCode)
%soft code 11-20 reserved for PulsePal sound delivery
persistent EarlyWithdrawalStartTime
global BpodSystem
global TaskParameters

if softCode == 1
    EarlyWithdrawalStartTime = posixtime(datetime('now'));
elseif softCode == 2
    if posixtime(datetime('now')) - EarlyWithdrawalStartTime >...
       TaskParameters.GUI.TimeOutEarlyWithdrawal
        SendBpodSoftCode(1)
    end
elseif softCode > 10 && softCode < 21 %for auditory clicks
    fprintf('softCode: %d\n', softCode);
    if true%~BpodSystem.EmulatorMode
        if softCode == 11 && TaskParameters.GUI.PlayNoiseforError %noise on chan 1
            try
                ProgramPulsePal(BpodSystem.Data.Custom.PulsePalParamFeedback);
                SendCustomPulseTrain(1,cumsum(randi(9,1,601))/10000,(rand(1,601)-.5)*20); % White(?) noise on channel 1+2
                SendCustomPulseTrain(2,cumsum(randi(9,1,601))/10000,(rand(1,601)-.5)*20);
                TriggerPulsePal(1,2);
                ProgramPulsePal(BpodSystem.Data.Custom.PulsePalParamStimulus);
            catch ME
                display(getReport(ME));
            end
        elseif softCode == 12 && TaskParameters.GUI.ITISignalType == ITISignalType.Beep %beep on chan 2
            ProgramPulsePal(BpodSystem.Data.Custom.PulsePalParamFeedback);
            SendCustomPulseTrain(2,0:.001:.3,(ones(1,301)*3));  % Beep on channel 1+2
            SendCustomPulseTrain(1,0:.001:.1,(ones(1,101)));
            TriggerPulsePal(1,2);
            ProgramPulsePal(BpodSystem.Data.Custom.PulsePalParamStimulus);
        end
    end
elseif softCode == 5
    BpodSystem.SystemSettings.dotsMapped_file.Data(1:4) =...
                                                    typecast(uint32(2), 'uint8');
elseif softCode == 6
    BpodSystem.SystemSettings.dotsMapped_file.Data(1:4) =...
                                                    typecast(uint32(0), 'uint8');
elseif softCode == 7 % Sound stimulus start
    PsychPortAudio('Start', BpodSystem.Data.Custom.soundParams.pahandle,...
                   0); % 0 = infinte sound loop
elseif softCode == 8
    PsychPortAudio('Stop', BpodSystem.Data.Custom.soundParams.pahandle);
elseif softCode == 30 && BpodSystem.Data.Custom.IsHomeCage
    disp('Reporting animal is using the system at this very moment.');
    BpodSystem.ProtocolSettings.HomeCage.ReportAnimalInsideFn();
    BpodSystem.ProtocolSettings.StartTime = posixtime(datetime('now'));
end
end
