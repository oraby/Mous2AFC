classdef IncorrectChoiceSignalType
    properties (Constant)
        None = 1;
        NoisePulsePal = 2;
        PortLED = 3;
        BeepOnWire_1 = 4;
        SmallReward = 5;
    end
    methods(Static)
        function string = String()
            string = properties(IncorrectChoiceSignalType)';
        end
    end
end
