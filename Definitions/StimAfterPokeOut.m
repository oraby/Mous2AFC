classdef StimAfterPokeOut
    properties (Constant)
        UntilFeedbackStart = 1;
        UntilFeedbackEnd = 2;
        UntilEndOfTrial = 3;
        NotUsed = 4;
    end
    methods(Static)
        function string = String()
            string = properties(StimAfterPokeOut)';
        end
    end
end
