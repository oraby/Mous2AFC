function [DeliverStimulus, ContDeliverStimulus, StopStimulus, GUI,...
    drawParams] = HandleStateMatrixStim(GUI, CurTrial, LeftPort, LeftPWM,...
                                        RightPort, RightPWM, soundParams,...
                                        dotsMapped_file, SessionPath)
%TODO: Create drawParams as persistent object
drawParams = struct;
%The rest of this function continue down below

function [DeliverStimulus_, ContDeliverStimulus_, StopStimulus_] = ...
    SingleExpType(ExpType, DV)
if ExpType == ExperimentType.Auditory
    DeliverStimulus_ =  {'BNCState',1};
    ContDeliverStimulus_ = {};
    StopStimulus_ = {'BNCState',0};
elseif ExpType == ExperimentType.LightIntensity
    % Divide Intensity by 100 to get fraction value
    LeftPWMStim = round(CurTrial.LightIntensityLeft*LeftPWM/100);
    RightPWMStim = round(CurTrial.LightIntensityRight*RightPWM/100);
    DeliverStimulus_ = {strcat('PWM',num2str(LeftPort)),LeftPWMStim,...
                        strcat('PWM',num2str(RightPort)),RightPWMStim};
    ContDeliverStimulus_ = DeliverStimulus_;
    StopStimulus_ = {};
elseif ExpType == ExperimentType.SoundIntensity
    if GUI.UsePCSpeakers
        trialWav = soundParams.origWav;
        % Get the other channel to modify it
        otherChannelIdx = iff(DV < 0, 1, 2);
        if contains(AudStimType.String(GUI.AudStimType), 'Stereo')
            trialWav(otherChannelIdx,:) = trialWav(mod(2+otherChannelIdx,2)+1,:);
        else
            trialWav(otherChannelIdx,:) = (1-abs(DV))*trialWav(otherChannelIdx,:);
        end
        PsychPortAudio('FillBuffer', soundParams.pahandle, trialWav);
        DeliverStimulus_ = {'SoftCode',7};
        ContDeliverStimulus_ = {};
        StopStimulus_ = {'SoftCode',8};
    else
        LeftSoundPort = floor(mod(GUI.Ports_LMRAudLRAir/100,10));
        RightSoundPort = floor(mod(GUI.Ports_LMRAudLRAir/10,10));
        LeftSoundPWM = round((100-GUI.LeftSpeakerAttenPrcnt) * 2.55);
        RightSoundPWM = round((100-GUI.RightSpeakerAttenPrcnt) * 2.55);
        % Divide maxsound by 100 to get fraction value
        LeftPWMSound = round(CurTrial.SoundIntensityLeft*LeftSoundPWM/100);
        RightPWMSound = round(CurTrial.SoundIntensityRight*RightSoundPWM/100);
        DeliverStimulus_ = {strcat('PWM',num2str(LeftSoundPort)),LeftPWMSound,...
                            strcat('PWM',num2str(RightSoundPort)),RightPWMSound};
        ContDeliverStimulus_ = DeliverStimulus_;
        StopStimulus_ = {};
    end
elseif ExpType == ExperimentType.GratingOrientation
    rightPortAngle = VisualStimAngle.getDegrees(GUI.VisualStimAnglePortRight);
    leftPortAngle = VisualStimAngle.getDegrees(GUI.VisualStimAnglePortLeft);
    % Calculate the distance between right and left port angle to determine
    % whether we should use the circle arc between the two values in the
    % clock-wise or counter-clock-wise direction to calculate the different
    % difficulties.
    % TODO: Can't we convert this to simply a condition without true, false?
    ccw = iff(mod(rightPortAngle-leftPortAngle,360) < mod(leftPortAngle-rightPortAngle,360), true, false);
    if ccw
        finalDV = DV;
        if rightPortAngle < leftPortAngle
            rightPortAngle = rightPortAngle + 360;
        end
        angleDiff = rightPortAngle - leftPortAngle;
        minAngle = leftPortAngle;
    else
        finalDV = -DV;
        if leftPortAngle < rightPortAngle
            leftPortAngle = leftPortAngle + 360;
        end
        angleDiff = leftPortAngle - rightPortAngle;
        minAngle = rightPortAngle;
    end
    % orientation = ((DVMax - DV)*(DVMAX-DVMin)*(MaxAngle - MinANgle)) + MinAngle
    gratingOrientation = ((1 - finalDV)*angleDiff/2) + minAngle;
    gratingOrientation = mod(gratingOrientation, 360);
    drawParams.stimType = DrawStimType.StaticGratings;
    drawParams.gratingOrientation = gratingOrientation;
    drawParams.numCycles = GUI.numCycles;
    drawParams.cyclesPerSecondDrift = GUI.cyclesPerSecondDrift;
    drawParams.phase = GUI.phase;
    drawParams.gaborSizeFactor = GUI.gaborSizeFactor;
    drawParams.gaussianFilterRatio = GUI.gaussianFilterRatio;

    wait_mmap_file = createMMFile(tempdir, 'mmap_matlab_dot_read.dat', 4);
    % Start from the 5th byte
    serializeAndWrite(dotsMapped_file, 5, drawParams, wait_mmap_file, 1);
    dotsMapped_file.Data(1:4) = typecast(uint32(1), 'uint8');

    DeliverStimulus_ = {'SoftCode',5};
    ContDeliverStimulus_ = {};
    StopStimulus_ = {'SoftCode',6};
elseif ExpType == ExperimentType.RandomDots
    % Setup the parameters
    % Use 20% of the screen size. Assume apertureSize is the diameter
    GUI.circleArea = (pi*((GUI.apertureSizeWidth/2).^2));
    GUI.nDots = round(GUI.circleArea * GUI.drawRatio);
    drawParams.stimType = DrawStimType.RDK;
    drawParams.circleRDK = GUI.circleRDK;
    drawParams.centerX = GUI.centerX;
    drawParams.centerY = GUI.centerY;
    drawParams.apertureSizeWidth = GUI.apertureSizeWidth;
    drawParams.apertureSizeHeight = GUI.apertureSizeHeight;
    drawParams.drawRatio = GUI.drawRatio;
    drawParams.mainDirection = floor(VisualStimAngle.getDegrees(...
        iff(CurTrial.LeftRewarded,GUI.VisualStimAnglePortLeft,...
                                  GUI.VisualStimAnglePortRight)));
    drawParams.dotSpeed = GUI.dotSpeedDegsPerSec;
    drawParams.dotLifetimeSecs = GUI.dotLifetimeSecs;
    drawParams.coherence = CurTrial.DotsCoherence;
    drawParams.screenWidthCm = GUI.screenWidthCm;
    drawParams.screenDistCm = GUI.screenDistCm;
    drawParams.dotSizeInDegs = GUI.dotSizeInDegs;
    if ~isnan(CurTrial.DotsPulseCoherence)
        drawParams.pulseCohr = CurTrial.DotsPulseCoherence;
        drawParams.pulseOffset = CurTrial.DotsPulseStart;
        drawParams.pulseDur = CurTrial.DotsPulseDur;
    else
        drawParams.pulseCohr = 0;
        drawParams.pulseOffset = 999;
        drawParams.pulseDur = 0;
    end
    % The next two fields helps the renderer to know when and where to dump its
    % data when a new animal is detected.
    % Leave TrialNumber as PascalCase to use it later to merge dataframes
    % on with TrialNumber in Data.Custom.Trials.
    drawParams.TrialNumber = CurTrial.TrialNumber;
    drawParams.sessionPath = SessionPath;
    % Start from the 5th byte
    wait_mmap_file = createMMFile(tempdir, 'mmap_matlab_dot_read.dat', 4);
    serializeAndWrite(dotsMapped_file, 5, drawParams, wait_mmap_file, 1);
    dotsMapped_file.Data(1:4) = typecast(uint32(1), 'uint8');

    DeliverStimulus_ = {'SoftCode',5};
    ContDeliverStimulus_ = {};
    StopStimulus_ = {'SoftCode',6};
elseif ExpType == ExperimentType.NoStimulus
    DeliverStimulus_ = {};
    ContDeliverStimulus_ = {};
    StopStimulus_ = {};
else
    assert(false, 'Unexpected ExperimentType');
end
end

[DeliverStimulus1, ContDeliverStimulus1, StopStimulus1] = SingleExpType(...
                                                GUI.ExperimentType, CurTrial.DV);
if ~isnan(CurTrial.SecDV)
    [DeliverStimulus2, ContDeliverStimulus2, StopStimulus2,] = SingleExpType(...
                                          GUI.SecExperimentType, CurTrial.SecDV);
else
    DeliverStimulus2 = {};
    ContDeliverStimulus2 = {};
    StopStimulus2 = {};
end
DeliverStimulus = [DeliverStimulus1 DeliverStimulus2];
ContDeliverStimulus = [ContDeliverStimulus1 ContDeliverStimulus2];
StopStimulus = [StopStimulus1 StopStimulus2];
end
