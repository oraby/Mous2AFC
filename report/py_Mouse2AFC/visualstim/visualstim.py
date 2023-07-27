# A modified version from the code found in:
# http://www.mbfys.ru.nl/~robvdw/DGCN22/PRACTICUM_2011/LABS_2011/ALTERNATIVE_LABS/Lesson_2.html#18
import time
import sys
import numpy as np
from ctypes import cdll
try:
  cdll.LoadLibrary('nvapi64.dll')
except:
  pass
else:
  print("Managed to force using of Nvidia's graphics card, I think...")
from psychopy import prefs
# prefs.general['winType'] = "pyglet"
from psychopy import visual
from psychopy import monitors
from common.definitions import DrawStimType
from common.loadSerializedData import loadSerializedData
from . import drawdots, gabor
# from .checkclose import checkClose

def availableScreens():
  import ctypes
  import win32api
  from pyglet.canvas import get_display
  display = get_display()
  screens = display.get_screens()
  #primary_screen = display.get_default_screen() # This is buggy
  shcore = ctypes.windll.shcore
  # http://timgolden.me.uk/pywin32-docs/win32api__EnumDisplayMonitors_meth.html
  monitors = win32api.EnumDisplayMonitors()
  int_p = ctypes.c_uint()
  screens_li = []
  for screen_idx, monitor in enumerate(monitors):
    # From EnumDisplayMonitors() documentation at the link above:
    # Return Value:
    # Returns a sequence of tuples. For each monitor found, returns a handle to
    # the monitor, device context handle, and intersection rectangle: (hMonitor,
    # hdcMonitor, PyRECT)
    hMonitor, hdcMonitor, (left, top, right, bottom) = monitor
    shcore.GetScaleFactorForMonitor(monitor[0].handle, ctypes.byref(int_p))
    scale_factor = int_p.value/100
    print(f"Monitor {screen_idx} Scale: {scale_factor}")
    # screens[screen_idx].width *= scale_factor
    # screens[screen_idx].height *= scale_factor
    # left == 0 and top == 0 => this is the primary/default screen
    screens_li.append((screen_idx, screens[screen_idx], left == 0 and top == 0))
  return screens_li


def createWindow(screen_id, screen_inf):
  #cur_win_ptr, cur_win_rect = PsychImaging('OpenWindow', cur_screen_id,
  #    BLACK_COLOR, cur_win_rect, 32, 2, [], [],  kPsychNeed32BPCFloat)
  win = visual.Window(size=(screen_inf.width, screen_inf.height),
                      screen=screen_id, winType="pyglet", fullscr=True,
                      #bpc=32, depthBits=32, waitBlanking=True,
                      bpc=8, depthBits=24, waitBlanking=True,
                      color='black', allowGUI=True,
                      # We will do it later more extensively
                      checkTiming=False)
                      # Should we add also stencil bits = 32?
  # win.mouseVisible = False
  info = win.winHandle.context.get_info()
  print("GL info:", info.get_version())
  print("Renderer:", info.get_renderer())
  win.winHandle.on_close = closeEvent
  # from pyglet.info import dump_gl
  # dump_gl(win.winHandle.context)
  # From some reasons, if we use more than one screen and we don't run
  # the line below, then the code hangs while trying to measure the FPS.
  # Related: https://stackoverflow.com/q/51159363/11996983
  win.winHandle.dispatch_events()
  return win

def closeEvent():
  sys.exit(0)

def mousePos(pos=None):
  # This only works on windows
  import win32api
  if pos:
    try:
      win32api.SetCursorPos(pos)
    except:
      pass
  else:
    pos = win32api.GetCursorPos()
  # print("Pos:", pos)
  return pos

def setup():
  import sys
  screens_li = availableScreens()
  print("Found screens:", screens_li)
  if len(sys.argv) == 1: # They user didn't specify which monitor
    # If there are more than one screen, then set the screen number to all the
    # monitor connected monitors other than the primary one.
    if len(screens_li) > 1:
      screens_li = list(filter(lambda scr: scr[2] == False, screens_li))
    used_screens = screens_li
    #screens_ids_infs = [(len(screens)-1, screens[-1],)] # The list is reversed
    print("screens_ids_infs", used_screens)
  else:
    # Convert to numpy array so we can use sys.argv list as an indices
    used_screens = np.array(screens_li)[[int(arg) for arg in sys.argv[1:]]]

  from common.createMMFile import createMMFile
  FILE_SIZE = 512*1024 # 512 kb mem-mapped file
  mm_file = createMMFile(r"c:\Bpoduser\mmap_matlab_randomdot.dat", FILE_SIZE)

  wins_ptrs = []
  fill_rects = []
  photo_diode_boxes = []
  # Open the screens
  print("Screens ids:", used_screens)

  for cur_screen_id, cur_screen_inf, _ in used_screens:
    print("Opening screen:", cur_screen_id)
    cur_win_ptr = createWindow(cur_screen_id, cur_screen_inf)
    # Disable alpha blending just in case it was still enabled by a previous
    # run that crashed. # Can this happen?
    cur_win_ptr.blendMode = "avg"
    wins_ptrs.append(cur_win_ptr)
  wins_ptrs = np.array(wins_ptrs)

  monitors_names = monitors.getAllMonitors()
  # Assume it's the only one setup
  cur_monitor = monitors.Monitor(monitors_names[0])
  # TODO: If we are using more than one monitor, then set the pixel size for
  # each different monitor and calculate the pix-size differently according to
  # each monitor.
  cur_monitor.setSizePix((used_screens[0][1].width, used_screens[0][1].height))
  # Query maximum useable priority_level on this system:
  #priority_level = MaxPriority(cur_screen_id)
  return mm_file, wins_ptrs, cur_monitor

def main():
  cur_mouse_pos = mousePos()
  mm_file, wins_ptrs, monitor = setup()
  mousePos(cur_mouse_pos)

  PHOTO_DIODE_POS_NORM = (0.925, 0.925)
  PHOTO_DIODE_SIZE_NORM = (0.3, 0.15)
  # For verbosity, the same windows rect is valid for all screens as all
  # the screens should have the same resolution
  win_size = np.array((wins_ptrs[0].viewport[2] - wins_ptrs[0].viewport[0],
                       wins_ptrs[0].viewport[3] - wins_ptrs[0].viewport[1]))
  # For the next parts, we assume that all the screens has the same dimension,
  # so just use wins_ptrs[0] as it should hold the sane parameters for all the
  # windows.
  for i in range(1, 6):
    print(f"Measuring screen frame rate at {i}ms std. threshold")
    frame_rate = wins_ptrs[0].getActualFrameRate(nMaxFrames=200, threshold=i,
                                                 nWarmUpFrames=30)
    if frame_rate is not None:
      break
    else:
      print(f"Failed to get good measurements at {i}ms std.")
  else:
    print("Failed to get measure frame rate. Using monitor referesh rate value")
    frame_rate = 1/wins_ptrs[0].monitorFramePeriod
  print("Using frame rate:", frame_rate)

  draw_dots = drawdots.DrawDots(wins_ptrs, win_size, PHOTO_DIODE_SIZE_NORM,
                                PHOTO_DIODE_POS_NORM, frame_rate, monitor)
  gabor_stim = gabor.Gabor(wins_ptrs, win_size, PHOTO_DIODE_SIZE_NORM,
                           PHOTO_DIODE_POS_NORM, frame_rate, monitor)
  # Commands
  # 0 = Stop running
  # 1 = Load new stim info
  # 2 = Start running or keep running
  cur_cmd = 0
  while True:
    while cur_cmd == 0:
      time.sleep(0.01) # Sleep until the next command
      # checkClose(wins_ptrs)
      cur_cmd = np.frombuffer(mm_file[:4], dtype=np.uint32)[0]
    # Load the the drawing parameters
    _, drawParams = loadSerializedData(mm_file, 4)
    if drawParams.stimType == DrawStimType.RDK:
      cur_cmd, draw_params = draw_dots.loop(cur_cmd, mm_file)
    elif drawParams.stimType == DrawStimType.StaticGratings or \
         drawParams.stimType == DrawStimType.DriftingGratings:
      cur_cmd, draw_params = gabor_stim.loop(cur_cmd, mm_file)
    else:
      print("Unknown command:", drawParams.stimType)
      continue

if __name__ == "__main__":
  main()
