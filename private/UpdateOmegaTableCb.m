function UpdateOmegaTableCb(OmegaTableHandle,~)
global TaskParameters;
CatchTableHandle = GetGUIParamHandler('TaskParameters.GUI.CatchTable');
CatchTableData = CatchTableHandle.Data;
CatchTableData(:,1) = OmegaTableHandle.Data(:,1);
set(CatchTableHandle, 'Data', CatchTableData);
TaskParameters.GUI.CatchTable.Omega = CatchTableData(:,1);
% Update RDK values
OmegaData = OmegaTableHandle.Data;
OmegaData(:, 2) = (OmegaData(:,1) - 50) * 2;
set(OmegaTableHandle, 'Data', OmegaData);
TaskParameters.GUI.OmegaTable.RDK = OmegaData(:, 2);
end
