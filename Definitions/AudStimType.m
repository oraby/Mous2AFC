classdef AudStimType
    properties (Constant)
        ClicksLeftTelephoneRight = 1;
        TelephoneLeftRight = 2;
        ClicksLeftRight = 3;
        FreqSweepStereo = 4;
    end
    properties (Constant, Access = private)
        asStr = AudStimType.String();
    end
    methods(Static)
        function string = String(varargin)
            if isempty(varargin)
                string = properties(AudStimType)';
            else
                string = AudStimType.asStr{varargin{1}};
            end
        end
    end
end
