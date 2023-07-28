function UpdateIncorrectSignalTypeCb(DropDownHandler,~)
  global TaskParameters;
  TextHandler = GetGUIParamHandler('TaskParameters.GUI.PunishRewardAmount');
  if DropDownHandler.Value == IncorrectChoiceSignalType.SmallReward
    TextHandler.Enable = 'on';
  else
    TextHandler.Enable = 'off';
  end
end