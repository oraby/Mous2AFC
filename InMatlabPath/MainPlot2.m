function AxesHandles = MainPlot2(AxesHandles, Action, DataCustom,...
                                 TaskParametersGUI, TrialStartTimestamp,...
                                 SessionStartTime, varargin)
global nTrialsToShow %this is for convenience

switch Action
    case 'init'

        %% Outcome
        %initialize pokes plot
        nTrialsToShow = 90; %default number of trials to display

        if nargin >=7  %custom number of trials
            nTrialsToShow = varargin{1};
        end
        axes(AxesHandles.HandleOutcome);
        line([0 3000], [1.3  1.3], 'LineStyle', '--', 'Color', [0.4 0.4 0.4]);
        line([0 3000], [1.1  1.1], 'LineStyle', '--', 'Color', [0.4 0.4 0.4]);
        line([0 3000], [-1.1  -1.1], 'LineStyle', '--', 'Color', [0.4 0.4 0.4]);
        line([0 3000], [-1.3  -1.3], 'LineStyle', '--', 'Color', [0.4 0.4 0.4]);
        annotation('textbox',[.9 .31 .1 .2], 'String','Sec Exp', 'EdgeColor', 'none', 'FontSize', 8);
        annotation('textbox',[.9 .27 .1 .2], 'String','No Stim', 'EdgeColor', 'none', 'FontSize', 8);
        annotation('textbox',[.9 .09  .1 .2], 'String','No Stim', 'EdgeColor', 'none', 'FontSize', 8);
        annotation('textbox',[.9 .045 .1 .2], 'String','Sec Exp', 'EdgeColor', 'none', 'FontSize', 8);
        %plot in specified axes
        DV = [DataCustom.Trials(1:DataCustom.DVsAlreadyGenerated).StimulusOmega]*2 - 1; % Use stimulus Omega as a proxy for DV
        AxesHandles.DV = line(1:DataCustom.DVsAlreadyGenerated, DV, 'LineStyle','none','Marker','o','MarkerEdge','b','MarkerFace','b', 'MarkerSize',6);
        AxesHandles.CurrentTrialCircle = line(1,0, 'LineStyle','none','Marker','o','MarkerEdge','k','MarkerFace',[1 1 1], 'MarkerSize',6);
        AxesHandles.CurrentTrialCross = line(1,0, 'LineStyle','none','Marker','+','MarkerEdge','k','MarkerFace',[1 1 1], 'MarkerSize',6);
        AxesHandles.CumRwd = text(1,1,'0mL','verticalalignment','bottom','horizontalalignment','center');
        AxesHandles.Correct = line(-1,1, 'LineStyle','none','Marker','o','MarkerEdge','g','MarkerFace','g', 'MarkerSize',6);
        AxesHandles.Incorrect = line(-1,1, 'LineStyle','none','Marker','o','MarkerEdge','r','MarkerFace','r', 'MarkerSize',6);
        % TODO: Get rid of NoChoice and Sec NoChoice (if possible) and just use normal blue DV plotting.
        AxesHandles.PrimNoStimNoChoice= line(-1,1, 'LineStyle','none','Marker','o','MarkerEdge',[1, 1, 1],'MarkerFace', 'b', 'MarkerSize',8); % around DV limits
        AxesHandles.SecDVCorrect = line(-1,1, 'LineStyle','none','Marker','o','MarkerEdge',[0, 0, 0],'MarkerFace', [1, 1, 1], 'MarkerSize',8); % around Primary No Stim
        AxesHandles.SecDVIncorrect = line(-1,1, 'LineStyle','none','Marker','o','MarkerEdge',[1, 1, 1],'MarkerFace', 'k', 'MarkerSize',8); % around Primary No Stim
        AxesHandles.SecDVNoChoice= line(-1,1, 'LineStyle','none','Marker','o','MarkerEdge',[1, 1, 1],'MarkerFace', 'b', 'MarkerSize',8); % around Primary No Stim
        AxesHandles.SecDV = line(-1,1, 'LineStyle','none','Marker','o','MarkerEdge','none','MarkerFace',[.7,.7,.7], 'MarkerSize',6);
        AxesHandles.BrokeFix = line(-1,0, 'LineStyle','none','Marker','d','MarkerEdge','b','MarkerFace','none', 'MarkerSize',6);
        AxesHandles.EarlyWithdrawal = line(-1,0, 'LineStyle','none','Marker','d','MarkerEdge','none','MarkerFace','b', 'MarkerSize',6);
        AxesHandles.NoFeedback = line(-1,0, 'LineStyle','none','Marker','o','MarkerEdge','none','MarkerFace','w', 'MarkerSize',5);
        AxesHandles.NoResponse = line(-1,[0 1], 'LineStyle','none','Marker','x','MarkerEdge','w','MarkerFace','none', 'MarkerSize',6);
        AxesHandles.Catch = line(-1,[0 1], 'LineStyle','none','Marker','o','MarkerEdge',[0,0,0],'MarkerFace',[0,0,0], 'MarkerSize',4);
        set(AxesHandles.HandleOutcome,'TickDir', 'out','XLim',[0, nTrialsToShow],'YLim', [-1.6, 1.6], 'YTick', [-1, 1],'YTickLabel', {'Right','Left'}, 'FontSize', 13);
        lbl = sprintf('Trial # - Cur Trial: %d\n%s - Session Start: %s', 1, DataCustom.Subject, SessionStartTime);
        xlabel(AxesHandles.HandleOutcome, lbl, 'FontSize', 12);
        hold(AxesHandles.HandleOutcome, 'on');
        %% Psyc Stimulus
        AxesHandles.PsycStim = line(AxesHandles.HandlePsycStim,[-1 1],[.5 .5], 'LineStyle','none','Marker','o','MarkerEdge','k','MarkerFace','k', 'MarkerSize',6,'Visible','off');
        AxesHandles.PsycStimFit = line(AxesHandles.HandlePsycStim,[-1. 1.],[.5 .5],'color','k','Visible','off');
        AxesHandles.PsycStimForced = line(AxesHandles.HandlePsycStim,[-1 1],[.5 .5], 'LineStyle','none','Marker','o','MarkerEdge','g','MarkerFace','g', 'MarkerSize',6,'Visible','off');
        AxesHandles.PsycStimForcedFit = line(AxesHandles.HandlePsycStim,[-1. 1.],[.5 .5],'color','g','Visible','off');
        AxesHandles.HandlePsycStim.YLim = [-.05 1.05];
        AxesHandles.HandlePsycStim.XLim = [-1.05, 1.05];
        AxesHandles.HandlePsycStim.XLabel.String = 'DV'; % FIGURE OUT UNIT
        AxesHandles.HandlePsycStim.YLabel.String = '% left';
        AxesHandles.HandlePsycStim.Title.String = 'Psychometric Stim';
        %% Vevaiometric curve
        hold(AxesHandles.HandleVevaiometric,'on')
        AxesHandles.VevaiometricCatch = line(AxesHandles.HandleVevaiometric,-2,-1, 'LineStyle','-','Color','g','Visible','off','LineWidth',2);
        AxesHandles.VevaiometricErr = line(AxesHandles.HandleVevaiometric,-2,-1, 'LineStyle','-','Color','r','Visible','off','LineWidth',2);
        AxesHandles.VevaiometricPointsErr = line(AxesHandles.HandleVevaiometric,-2,-1, 'LineStyle','none','Color','r','Marker','o','MarkerFaceColor','r', 'MarkerSize',2,'Visible','off','MarkerEdgeColor','r');
        AxesHandles.VevaiometricPointsCatch = line(AxesHandles.HandleVevaiometric,-2,-1, 'LineStyle','none','Color','g','Marker','o','MarkerFaceColor','g', 'MarkerSize',2,'Visible','off','MarkerEdgeColor','g');
        AxesHandles.HandleVevaiometric.YLim = [0 20];
        AxesHandles.HandleVevaiometric.XLim = [-1.05, 1.05];
        AxesHandles.HandleVevaiometric.XLabel.String = 'DV';
        AxesHandles.HandleVevaiometric.YLabel.String = 'WT (s)';
        AxesHandles.HandleVevaiometric.Title.String = 'Vevaiometric';
        %% Trial rate
        hold(AxesHandles.HandleTrialRate,'on')
        AxesHandles.TrialRate = line(AxesHandles.HandleTrialRate,[0],[0], 'LineStyle','-','Color','k','Visible','off'); %#ok<NBRAK>
        AxesHandles.HandleTrialRate.XLabel.String = 'Time (min)'; % FIGURE OUT UNIT
        AxesHandles.HandleTrialRate.YLabel.String = 'nTrials';
        AxesHandles.HandleTrialRate.Title.String = 'Trial rate';
        %% Stimulus delay
        hold(AxesHandles.HandleFix,'on')
        AxesHandles.HandleFix.XLabel.String = 'Time (ms)';
        AxesHandles.HandleFix.YLabel.String = 'trial counts';
        AxesHandles.HandleFix.Title.String = 'Pre-stimulus delay';
        %% ST histogram
        hold(AxesHandles.HandleST,'on')
        AxesHandles.HandleST.XLabel.String = 'Time (ms)';
        AxesHandles.HandleST.YLabel.String = 'trial counts';
        AxesHandles.HandleST.Title.String = 'Stim sampling time';
        %% Feedback Delay histogram
        hold(AxesHandles.HandleFeedback,'on')
        AxesHandles.HandleFeedback.XLabel.String = 'Time (ms)';
        AxesHandles.HandleFeedback.YLabel.String = 'trial counts';
        AxesHandles.HandleFeedback.Title.String = 'Feedback delay';
    case 'update'
        %% Reposition and hide/show axes
        ShowPlots = [TaskParametersGUI.ShowPsycStim,TaskParametersGUI.ShowVevaiometric,...
                     TaskParametersGUI.ShowTrialRate,TaskParametersGUI.ShowFix,TaskParametersGUI.ShowST,TaskParametersGUI.ShowFeedback];
        NoPlots = sum(ShowPlots);
        NPlot = cumsum(ShowPlots);
        if ShowPlots(1)
            AxesHandles.HandlePsycStim.Position =      [NPlot(1)*.05+0.005 + (NPlot(1)-1)*1/(1.65*NoPlots)    .6   1/(1.65*NoPlots) 0.3];
            AxesHandles.HandlePsycStim.Visible = 'on';
            set(get(AxesHandles.HandlePsycStim,'Children'),'Visible','on');
        else
            AxesHandles.HandlePsycStim.Visible = 'off';
            set(get(AxesHandles.HandlePsycStim,'Children'),'Visible','off');
        end
        if ShowPlots(2)
            AxesHandles.HandleVevaiometric.Position = [NPlot(2)*.05+0.005 + (NPlot(2)-1)*1/(1.65*NoPlots)    .6   1/(1.65*NoPlots) 0.3];
            AxesHandles.HandleVevaiometric.Visible = 'on';
            set(get(AxesHandles.HandleVevaiometric,'Children'),'Visible','on');
        else
            AxesHandles.HandleVevaiometric.Visible = 'off';
            set(get(AxesHandles.HandleVevaiometric,'Children'),'Visible','off');
        end
        if ShowPlots(3)
            AxesHandles.HandleTrialRate.Position =    [NPlot(3)*.05+0.005 + (NPlot(3)-1)*1/(1.65*NoPlots)    .6   1/(1.65*NoPlots) 0.3];
            AxesHandles.HandleTrialRate.Visible = 'on';
            set(get(AxesHandles.HandleTrialRate,'Children'),'Visible','on');
        else
            AxesHandles.HandleTrialRate.Visible = 'off';
            set(get(AxesHandles.HandleTrialRate,'Children'),'Visible','off');
        end
        if ShowPlots(4)
            AxesHandles.HandleFix.Position =          [NPlot(4)*.05+0.005 + (NPlot(4)-1)*1/(1.65*NoPlots)    .6   1/(1.65*NoPlots) 0.3];
            AxesHandles.HandleFix.Visible = 'on';
            set(get(AxesHandles.HandleFix,'Children'),'Visible','on');
        else
            AxesHandles.HandleFix.Visible = 'off';
            set(get(AxesHandles.HandleFix,'Children'),'Visible','off');
        end
        if ShowPlots(5)
            AxesHandles.HandleST.Position =           [NPlot(5)*.05+0.005 + (NPlot(5)-1)*1/(1.65*NoPlots)    .6   1/(1.65*NoPlots) 0.3];
            AxesHandles.HandleST.Visible = 'on';
            set(get(AxesHandles.HandleST,'Children'),'Visible','on');
        else
            AxesHandles.HandleST.Visible = 'off';
            set(get(AxesHandles.HandleST,'Children'),'Visible','off');
        end
        if ShowPlots(6)
            AxesHandles.HandleFeedback.Position =     [NPlot(6)*.05+0.005 + (NPlot(6)-1)*1/(1.65*NoPlots)    .6   1/(1.65*NoPlots) 0.3];
            AxesHandles.HandleFeedback.Visible = 'on';
            set(get(AxesHandles.HandleFeedback,'Children'),'Visible','on');
        else
            AxesHandles.HandleFeedback.Visible = 'off';
            set(get(AxesHandles.HandleFeedback,'Children'),'Visible','off');
        end

        %% Outcome
        iTrial = varargin{1};
        [mn, ~] = rescaleX(AxesHandles.HandleOutcome,iTrial,nTrialsToShow); % recompute xlim
        %Plot past trial outcomes
        indxToPlot = mn:iTrial;
        % As DVs are generated on spot and can be sometimes NaN, use Stimulus
        % omega instead as a proxy for DV for past, current and future trials
        DV = [DataCustom.Trials(1:DataCustom.DVsAlreadyGenerated).StimulusOmega]*2 - 1;
        choiceLeft = [DataCustom.Trials(indxToPlot).ChoiceLeft];
        set(AxesHandles.CurrentTrialCircle, 'xdata', iTrial+1, 'ydata', 0);
        set(AxesHandles.CurrentTrialCross, 'xdata', iTrial+1, 'ydata', 0);
        %plot modality background
        ndxNoStimDV = isnan([DataCustom.Trials(indxToPlot).DV]);
        %plot past&future trials. Plot it on two steps
        Xdata1 = mn:iTrial;
        Xdata1 = Xdata1(~ndxNoStimDV);
        Ydata1 = DV(mn:iTrial);
        Ydata1 = Ydata1(~ndxNoStimDV);
        Xdata2 = iTrial+1:DataCustom.DVsAlreadyGenerated;
        Ydata2 = DV(iTrial+1:DataCustom.DVsAlreadyGenerated);
        set(AxesHandles.DV, 'xdata', [Xdata1 Xdata2] ,'ydata', [Ydata1 Ydata2]);
        %plot secondary modality background
        SecDV = [DataCustom.Trials(indxToPlot).SecDV];
        ndxSecDV = ~isnan(SecDV);
        SecXdata = indxToPlot(ndxSecDV);
        Ydata = SecDV(ndxSecDV);
        set(AxesHandles.SecDV, 'xdata', SecXdata,'ydata', Ydata);

        %Cumulative Reward Amount
        RewardObtained = CalcRewObtained(DataCustom, iTrial);
        set(AxesHandles.CumRwd, 'position', [iTrial+9 0.7], 'string', ...
            [num2str(RewardObtained/1000) ' mL']);
        %Plot Rewarded
        ndxCor = [DataCustom.Trials(indxToPlot).ChoiceCorrect] == 1;
        Xdata = indxToPlot(ndxCor);
        ndxNoStim = ndxNoStimDV(Xdata-mn+1);
        Ydata = DV(indxToPlot); Ydata = Ydata(ndxCor);
        Ydata(ndxNoStim & Ydata < 0) = -1.2; Ydata(ndxNoStim & Ydata > 0) = 1.2;
        set(AxesHandles.Correct, 'xdata', Xdata, 'ydata', Ydata);
        %Plot Incorrect
        ndxInc = [DataCustom.Trials(indxToPlot).ChoiceCorrect] == 0;
        Xdata = indxToPlot(ndxInc);
        ndxNoStim = ndxNoStimDV(Xdata-mn+1);
        Ydata = DV(indxToPlot); Ydata = Ydata(ndxInc);
        Ydata(ndxNoStim & Ydata < 0) = -1.2; Ydata(ndxNoStim & Ydata > 0) = 1.2;
        set(AxesHandles.Incorrect, 'xdata', Xdata, 'ydata', Ydata);
        %Plot Broken Fixation
        ndxBroke = [DataCustom.Trials(indxToPlot).FixBroke];
        Xdata = indxToPlot(ndxBroke); Ydata = zeros(1,sum(ndxBroke));
        set(AxesHandles.BrokeFix, 'xdata', Xdata, 'ydata', Ydata);
        %Plot Early Withdrawal
        ndxEarly = [DataCustom.Trials(indxToPlot).EarlyWithdrawal];
        Xdata = indxToPlot(ndxEarly);
        Ydata = zeros(1,sum(ndxEarly));
        set(AxesHandles.EarlyWithdrawal, 'xdata', Xdata, 'ydata', Ydata);
        %Plot missed choice trials
        ndxMiss = isnan([DataCustom.Trials(indxToPlot).ChoiceLeft])&~ndxBroke&~ndxEarly;
        Xdata = indxToPlot(ndxMiss);
        Ydata = DV(indxToPlot); Ydata = Ydata(ndxMiss);
        set(AxesHandles.NoResponse, 'xdata', Xdata, 'ydata', Ydata);
        %Plot NoFeedback trials
        ndxNoFeedback = ~[DataCustom.Trials(indxToPlot).Feedback];
        Xdata = indxToPlot(ndxNoFeedback&~ndxMiss);
        ndxNoStim = ndxNoStimDV(Xdata-mn+1);
        Ydata = DV(indxToPlot); Ydata = Ydata(ndxNoFeedback&~ndxMiss);
        Ydata(ndxNoStim & Ydata < 0) = -1.2; Ydata(ndxNoStim & Ydata > 0) = 1.2;
        set(AxesHandles.NoFeedback, 'xdata', Xdata, 'ydata', Ydata);
        %Plot catch trials
        ndxCatch = [DataCustom.Trials(indxToPlot).CatchTrial];
        Xdata = indxToPlot(ndxCatch&~ndxMiss);
        ndxNoStim = ndxNoStimDV(Xdata-mn+1);
        Ydata = DV(indxToPlot); Ydata = Ydata(ndxCatch&~ndxMiss);
        Ydata(ndxNoStim & Ydata < 0) = -1.2; Ydata(ndxNoStim & Ydata > 0) = 1.2;
        set(AxesHandles.Catch, 'xdata', Xdata, 'ydata', Ydata);
        % Make non used primary DV transparent, this would happen if secondary DV
        % is set to be used alone. This should be also used for
        % ExperimentType == no stimulus, but we don't have access to this
        % information here.
        Xdata = indxToPlot(ndxNoStimDV & isnan(choiceLeft));
        Ydata = DV(indxToPlot); Ydata = Ydata(ndxNoStimDV & isnan(choiceLeft));
        Ydata(Ydata < 0) = -1.2; Ydata(Ydata > 0) = 1.2;
        set(AxesHandles.PrimNoStimNoChoice, 'xdata', Xdata, 'ydata', Ydata);
        if ~isempty(SecXdata)
            leftSecDV = SecDV == 1;
            ndxSecCor = leftSecDV == choiceLeft;
            Xdata = indxToPlot(ndxSecCor);
            Ydata = SecDV(ndxSecCor);
            Ydata(Ydata < 0) = -1.4; Ydata(Ydata > 0) = 1.4;
            set(AxesHandles.SecDVCorrect, 'xdata', Xdata, 'ydata', Ydata);
            ndxSecInc = (leftSecDV ~= choiceLeft) & ~isnan(choiceLeft);
            Xdata = indxToPlot(ndxSecInc);
            Ydata = SecDV(ndxSecInc);
            Ydata(Ydata < 0) = -1.4; Ydata(Ydata > 0) = 1.4;
            set(AxesHandles.SecDVIncorrect, 'xdata', Xdata, 'ydata', Ydata);
            Xdata = indxToPlot(ndxSecDV & isnan(choiceLeft));
            Ydata = SecDV(ndxSecDV & isnan(choiceLeft));
            Ydata(Ydata < 0) = -1.4; Ydata(Ydata > 0) = 1.4;
            set(AxesHandles.SecDVNoChoice, 'xdata', Xdata, 'ydata', Ydata);
        end
        runtime = seconds(TrialStartTimestamp(end)-TrialStartTimestamp(1));
        runtime.Format = 'hh:mm:ss';
        lbl = sprintf('Trial # - Cur Trial: %d\n%s - Session Start: %s - RunTime: %s',...
                      iTrial, DataCustom.Subject, SessionStartTime, runtime);
        xlabel(AxesHandles.HandleOutcome, lbl, 'FontSize', 12);
        %% Psych Stim
        if TaskParametersGUI.ShowPsycStim
            ndxNan = isnan([DataCustom.Trials(1:iTrial).ChoiceLeft]);
            ForcedTrials = [DataCustom.Trials(1:iTrial).ForcedLEDTrial];
            ndxChoice = ForcedTrials == 0 & ...
                        ~isnan([DataCustom.Trials(1:iTrial).DV]);
            ndxForced = ForcedTrials == 1 |...
                        ~isnan([DataCustom.Trials(1:iTrial).SecDV]);
            StimDV = [DataCustom.Trials(1:iTrial).DV];
            StimSecDV = [DataCustom.Trials(1:iTrial).SecDV];
            % Try to handle case where forced cue LED was on, but maybe
            % second experiment wasn't used.
            StimSecDV(ForcedTrials == 1) = StimDV(ForcedTrials == 1);
            StimBin = 8;
            % Choice trials
            if sum(~ndxNan&ndxChoice) > 1
                BinIdx = discretize(StimDV,linspace(min(StimDV),max(StimDV),StimBin+1));
                PsycY = grpstats([DataCustom.Trials(~ndxNan&ndxChoice).ChoiceLeft],BinIdx(~ndxNan&ndxChoice),'mean');
                PsycX = unique(BinIdx(~ndxNan&ndxChoice))/StimBin*2-1-1/StimBin;
                AxesHandles.PsycStim.YData = PsycY;
                AxesHandles.PsycStim.XData = PsycX;
                AxesHandles.PsycStimFit.XData = linspace(min(StimDV),max(StimDV),100);
                AxesHandles.PsycStimFit.YData = glmval(glmfit(StimDV(~ndxNan&ndxChoice),...
                    [DataCustom.Trials(~ndxNan&ndxChoice).ChoiceLeft]','binomial'),linspace(min(StimDV),max(StimDV),100),'logit');
            end
            % Forced trials
            if sum(~ndxNan&ndxForced) > 1
                SecBinIdx = discretize(StimSecDV,linspace(min(StimSecDV),max(StimSecDV),StimBin+1));
                PsycY = grpstats([DataCustom.Trials(~ndxNan&ndxForced).ChoiceLeft],SecBinIdx(~ndxNan&ndxForced),'mean');
                PsycX = unique(SecBinIdx(~ndxNan&ndxForced))/StimBin*2-1-1/StimBin;
                AxesHandles.PsycStimForced.YData = PsycY;
                AxesHandles.PsycStimForced.XData = PsycX;
                % Still use main DV here so we'd have the same scale on the
                % Psychometric x-axis
                AxesHandles.PsycStimForcedFit.XData = linspace(min(StimSecDV),max(StimSecDV),100);
                AxesHandles.PsycStimForcedFit.YData = glmval(glmfit(StimSecDV(~ndxNan&ndxForced),...
                    [DataCustom.Trials(~ndxNan&ndxForced).ChoiceLeft]','binomial'),linspace(min(StimSecDV),max(StimSecDV),100),'logit');
            end

        end
        %% Vevaiometric
        if TaskParametersGUI.ShowVevaiometric
            AxesHandles.HandleVevaiometric.YLim = [0 TaskParametersGUI.VevaiometricYLim];
            set(AxesHandles.HandleVevaiometric,'YLim', [0 TaskParametersGUI.VevaiometricYLim]);
            ndxError = [DataCustom.Trials(1:iTrial).ChoiceCorrect] == 0 ; %all (completed) error trials (including catch errors)
            ndxCorrectCatch = [DataCustom.Trials(1:iTrial).CatchTrial] & [DataCustom.Trials(1:iTrial).ChoiceCorrect] == 1; %only correct catch trials
            ndxMinWT = [DataCustom.Trials(1:iTrial).FeedbackTime] > TaskParametersGUI.VevaiometricMinWT;
            % Also use here StimulusOmega as a proxy for DV
            DV = [DataCustom.Trials(1:iTrial).StimulusOmega]*2 - 1;
            DVNBin = TaskParametersGUI.VevaiometricNBin;
            if ~isnan(StimDV)
                BinIdx = discretize(DV,linspace(min(StimDV),max(StimDV),DVNBin+1));
                WTerr = grpstats([DataCustom.Trials(ndxError&ndxMinWT).FeedbackTime],BinIdx(ndxError&ndxMinWT),'mean')';
                WTcatch = grpstats([DataCustom.Trials(ndxCorrectCatch&ndxMinWT).FeedbackTime],BinIdx(ndxCorrectCatch&ndxMinWT),'mean')';
                Xerr = unique(BinIdx(ndxError&ndxMinWT))/DVNBin*2-1-1/DVNBin;
                Xcatch = unique(BinIdx(ndxCorrectCatch&ndxMinWT))/DVNBin*2-1-1/DVNBin;
                AxesHandles.VevaiometricErr.YData = WTerr;
                AxesHandles.VevaiometricErr.XData = Xerr;
                AxesHandles.VevaiometricCatch.YData = WTcatch;
                AxesHandles.VevaiometricCatch.XData = Xcatch;
                if TaskParametersGUI.VevaiometricShowPoints
                    AxesHandles.VevaiometricPointsErr.YData = [DataCustom.Trials(ndxError&ndxMinWT).FeedbackTime];
                    AxesHandles.VevaiometricPointsErr.XData = DV(ndxError&ndxMinWT);
                    AxesHandles.VevaiometricPointsCatch.YData = [DataCustom.Trials(ndxCorrectCatch&ndxMinWT).FeedbackTime];
                    AxesHandles.VevaiometricPointsCatch.XData = DV(ndxCorrectCatch&ndxMinWT);
                else
                    AxesHandles.VevaiometricPointsErr.YData = -1;
                    AxesHandles.VevaiometricPointsErr.XData = 0;
                    AxesHandles.VevaiometricPointsCatch.YData = -1;
                    AxesHandles.VevaiometricPointsCatch.XData = 0;
                end
            end
        end
        %% Trial rate
        if TaskParametersGUI.ShowTrialRate
            AxesHandles.TrialRate.XData = (TrialStartTimestamp-min(TrialStartTimestamp))/60;
            AxesHandles.TrialRate.YData = 1:numel(TrialStartTimestamp);
        end
        if TaskParametersGUI.ShowFix
            %% Stimulus delay
            cla(AxesHandles.HandleFix)
            FixDur = [DataCustom.Trials(1:iTrial).FixDur];
            FixBroke = [DataCustom.Trials(1:iTrial).FixBroke];
            AxesHandles.HistBroke = histogram(AxesHandles.HandleFix, FixDur(FixBroke)*1000);
            AxesHandles.HistBroke.BinWidth = 50;
            AxesHandles.HistBroke.EdgeColor = 'none';
            AxesHandles.HistBroke.FaceColor = 'r';
            AxesHandles.HistFix = histogram(AxesHandles.HandleFix,FixDur(~FixBroke)*1000);
            AxesHandles.HistFix.BinWidth = 50;
            AxesHandles.HistFix.FaceColor = 'b';
            AxesHandles.HistFix.EdgeColor = 'none';
            BreakP = mean(FixBroke);
            cornertext(AxesHandles.HandleFix,sprintf('P=%1.2f',BreakP))
        end
        %% ST
        if TaskParametersGUI.ShowST
            cla(AxesHandles.HandleST)
            ST = [DataCustom.Trials(1:iTrial).ST];
            EarlyWithdrawal = [DataCustom.Trials(1:iTrial).EarlyWithdrawal];
            AxesHandles.HistSTEarly = histogram(AxesHandles.HandleST, ST(EarlyWithdrawal)*1000);
            AxesHandles.HistSTEarly.BinWidth = 50;
            AxesHandles.HistSTEarly.FaceColor = 'r';
            AxesHandles.HistSTEarly.EdgeColor = 'none';
            AxesHandles.HistST = histogram(AxesHandles.HandleST, ST(~EarlyWithdrawal)*1000);
            AxesHandles.HistST.BinWidth = 50;
            AxesHandles.HistST.FaceColor = 'b';
            AxesHandles.HistST.EdgeColor = 'none';
            FixBroke = [DataCustom.Trials(1:iTrial).FixBroke];
            EarlyP = sum(EarlyWithdrawal)/sum(~FixBroke);
            cornertext(AxesHandles.HandleST,sprintf('P=%1.2f',EarlyP))
        end
        %% Feedback delay (exclude catch trials and error trials, if set on catch)
        if TaskParametersGUI.ShowFeedback
            cla(AxesHandles.HandleFeedback)
            if TaskParametersGUI.CatchError
                ndxExclude = [DataCustom.Trials(1:iTrial).ChoiceCorrect] == 0; %exclude error trials if they are set on catch
            else
                ndxExclude = false(1,iTrial);
            end
            FeedbackTime = [DataCustom.Trials(1:iTrial).FeedbackTime];
            AxesHandles.HistNoFeed = histogram(AxesHandles.HandleFeedback,FeedbackTime(~[DataCustom.Trials(1:iTrial).Feedback]&~[DataCustom.Trials(1:iTrial).CatchTrial]&~ndxExclude)*1000);
            AxesHandles.HistNoFeed.BinWidth = 100;
            AxesHandles.HistNoFeed.EdgeColor = 'none';
            AxesHandles.HistNoFeed.FaceColor = 'r';
            %AxesHandles.HistNoFeed.Normalization = 'probability';
            AxesHandles.HistFeed = histogram(AxesHandles.HandleFeedback,FeedbackTime([DataCustom.Trials(1:iTrial).Feedback]&~[DataCustom.Trials(1:iTrial).CatchTrial]&~ndxExclude)*1000);
            AxesHandles.HistFeed.BinWidth = 50;
            AxesHandles.HistFeed.EdgeColor = 'none';
            AxesHandles.HistFeed.FaceColor = 'b';
            %AxesHandles.HistFeed.Normalization = 'probability';
            LeftSkip = sum(~[DataCustom.Trials(1:iTrial).Feedback]&~[DataCustom.Trials(1:iTrial).CatchTrial]&~ndxExclude&[DataCustom.Trials(1:iTrial).ChoiceLeft]==1)/sum(~[DataCustom.Trials(1:iTrial).CatchTrial]&~ndxExclude&[DataCustom.Trials(1:iTrial).ChoiceLeft]==1);
            RightSkip = sum(~[DataCustom.Trials(1:iTrial).Feedback]&~[DataCustom.Trials(1:iTrial).CatchTrial]&~ndxExclude&[DataCustom.Trials(1:iTrial).ChoiceLeft]==0)/sum(~[DataCustom.Trials(1:iTrial).CatchTrial]&~ndxExclude&[DataCustom.Trials(1:iTrial).ChoiceLeft]==0);
            cornertext(AxesHandles.HandleFeedback,{sprintf('L=%1.2f',LeftSkip),sprintf('R=%1.2f',RightSkip)})
        end
end

end

function [mn,mx] = rescaleX(AxesHandle,CurrentTrial,nTrialsToShow)
FractionWindowStickpoint = .75; % After this fraction of visible trials, the trial position in the window "sticks" and the window begins to slide through trials.
mn = max(round(CurrentTrial - FractionWindowStickpoint*nTrialsToShow),1);
mx = mn + nTrialsToShow - 1;
set(AxesHandle,'XLim',[mn-1 mx+1]);
end

function cornertext(h,str)
unit = get(h,'Units');
set(h,'Units','char');
pos = get(h,'Position');
if ~iscell(str)
    str = {str};
end
for i = 1:length(str)
    x = pos(1)+1;y = pos(2)+pos(4)-i;
    uicontrol(h.Parent,'Units','char','Position',[x,y,length(str{i})+1,1],'string',str{i},'style','text','background',[1,1,1],'FontSize',8);
end
set(h,'Units',unit);
end

