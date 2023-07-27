classdef BrainRegion
    properties (Constant)
        V1_L = 1;
        V1_R = 2;
        V1_Bi = 3;
        ALM_L = 4;
        ALM_R = 5;
        ALM_Bi = 6;
        PPC_L = 7;
        PPC_R = 8;
        PPC_Bi = 9;
        POR_L = 10;
        POR_R = 11;
        POR_Bi = 12;
        M2_L = 13;
        M2_R = 14;
        M2_Bi = 15;
        RSP_L = 16;
        RSP_R = 17;
        RSP_Bi = 18;
        S1_L = 19;
        S1_R = 20;
        S1_Bi = 21;
        M1_L = 22;
        M1_R = 23;
        M1_Bi = 24;
    end
    methods(Static)
        function string = String()
            string = properties(BrainRegion)';
        end
    end
end
