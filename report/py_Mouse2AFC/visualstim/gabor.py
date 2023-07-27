import numpy as np
from pyglet import clock
from psychopy import core
from psychopy.tools.monitorunittools import deg2pix
from psychopy import visual
from common.definitions import DrawStimType
from common.loadSerializedData import loadSerializedData
# from .checkclose import checkClose

REST_AFTER_SECS = 5*60

class Gabor:
  def __init__(self, wins_ptrs, win_size, photo_diode_size, photo_diode_pos,
               frame_rate, monitor):
    self._wins_ptrs = wins_ptrs
    self._win_size = win_size
    self._frame_rate = frame_rate
    self._monitor = monitor

    self._wait_fill_rects = []
    self._stim_fill_rects = []
    self._photo_diode_boxes = []
    for cur_win_ptr in self._wins_ptrs:
      rect = visual.Rect(cur_win_ptr, units="norm",  pos=(0, 0), size=(2, 2),
                         fillColor="black", lineColor="black")
      self._wait_fill_rects.append(rect)
      rect = visual.Rect(cur_win_ptr, units="norm",  pos=(0, 0), size=(2, 2),
                         fillColor="gray", lineColor="gray")
      self._stim_fill_rects.append(rect)
      box = visual.Rect(cur_win_ptr, units="norm", fillColor="white",
                        lineColor="white",  pos=photo_diode_pos,
                        size=photo_diode_size)
      self._photo_diode_boxes.append(box)
    # Maybe converting it to numpy would yield faster looping?
    self._wait_fill_rects = np.array(self._wait_fill_rects)
    self._stim_fill_rects = np.array(self._stim_fill_rects)
    self._photo_diode_boxes = np.array(self._photo_diode_boxes)

  def loop(self, cur_cmd, mm_file):
    while True:
      # checkClose(self._wins_ptrs)
      # Either this is the first run or the next iteration, in both way, clear
      # the screen to prepare for the next run.
      for win_ptr, fill_rect in zip(self._wins_ptrs, self._wait_fill_rects):
        fill_rect.draw()
        win_ptr.waitBlanking = False
        win_ptr.flip(clearBuffer=False)
        win_ptr.waitBlanking = True
      # Keep waiting until we receive the load or run command
      while cur_cmd == 0:
        core.wait(0.01) # Sleep until the next command
        cur_cmd = np.frombuffer(mm_file[:4], dtype=np.uint32)[0]

      # Load the the drawing parameters
      _, drawParams = loadSerializedData(mm_file, 4)
      if drawParams.stimType != DrawStimType.StaticGratings and \
         drawParams.stimType != DrawStimType.DriftingGratings:
        return cur_cmd, drawParams

      gratings, shifts_per_frame = self._load(drawParams)
      cur_cmd = self._renderLoop(mm_file, cur_cmd, gratings, shifts_per_frame)
      if cur_cmd == 1:
        print("Resting due to inactivity...")
        while cur_cmd == 1:
          [win_ptr.winHandle.dispatch_events() for win_ptr in self._wins_ptrs]
          core.wait(0.3, hogCPUperiod=0)
          cur_cmd = np.frombuffer(mm_file[:4], dtype=np.uint32)[0]
    # We can only break if we want exit
    print("User asked to exit")
    return -1, None


  def _load(self, drawParams):
    drawParams.gaborSizeFactor *= 2 # User scale is between zero and 1
    gratings = []
    drawParams.screenDistCm = 30 # TODO: Add this
    self._monitor.setDistance(drawParams.screenDistCm)
    pixs_per_deg = deg2pix(1, monitor=self._monitor)
    # print("pixs_per_deg:", pixs_per_deg)
    for cur_win_ptr in self._wins_ptrs:
      cur_grating = visual.GratingStim(
                      cur_win_ptr,
                      tex='sin',
                      units="norm",
                      size=drawParams.gaborSizeFactor,
                      ori=drawParams.gratingOrientation,
                      phase=drawParams.phase/360,
                      sf=drawParams.numCycles,
                      mask='gauss',
                      maskParams={"sd":drawParams.gaussianFilterRatio})
      # Make it cycles per degree
      gabor_size = self._win_size * drawParams.gaborSizeFactor
      # print("Gabor size:", gabor_size, "- internal size:", cur_grating.size)
      gabor_degrees = gabor_size/pixs_per_deg
      # print("Gabor degrees:", gabor_degrees)
      cycles_per_deg = gabor_degrees * drawParams.numCycles
      # print("Cycles per deg:", cycles_per_deg)
      cur_grating.sf = cycles_per_deg
      gratings.append(cur_grating)
    shifts_per_frame = drawParams.cyclesPerSecondDrift/self._frame_rate
    return np.array(gratings), shifts_per_frame

  def _renderLoop(self, mm_file, cur_cmd, gratings, shifts_per_frame):
    ifi = 1/self._frame_rate
    next_frame_time = 0
    # cur_cmd = 2 # This function should have not been called if cur_cmd is not 2
    # next_frame_time = 0
    # cur_cmd = np.frombuffer(mm_file[:4], dtype=np.uint32)[0]
    # # TODO: Send trial number as well to check if we missed a whole trial and
    # # accordingly if we should load a new config
    # while cur_cmd == 1:
    #   core.wait(0.005) # Wait for the run command
    #   cur_cmd = np.frombuffer(mm_file[:4], dtype=np.uint32)[0]
    #   # checkClose(self._wins_ptrs)
    wins_handles = [win_ptr.winHandle for win_ptr in self._wins_ptrs]
    num_frames = 0
    render_start_time = 0
    loop_start_time = clock.tick()
    vbl = loop_start_time
    while True:
      [stim_rect.draw() for stim_rect in self._stim_fill_rects]
      # Drawy one grating per window
      for grating in gratings:
        grating.draw()
        # Shift the grating' phase
        grating.phase = (grating.phase + shifts_per_frame)%1.0
      # Draw the corner box for the photo diode to detect
      [box.draw() for box in self._photo_diode_boxes]
      # Now we can render
      # sleep_for = next_frame_time - core.monotonicClock.getTime()
      # if sleep_for > 0:
      #   core.wait(sleep_for)
      if cur_cmd != 2: # To keep the flip() in cache, we flip() anyhow but we
                       # might clear first if we shouldn't render yet
        for handle in wins_handles:
          handle.switch_to()
          handle.clear()
        num_frames -= 1
      # https://stackoverflow.com/a/56761157/11996983
      for handle in wins_handles:
        handle.switch_to()
        handle.flip()
        handle.clear()
        # poll the operating system event queue
        handle.dispatch_events()
      # vbl = self._wins_ptrs[0].flip()
      # for cur_win_ptr in self._wins_ptrs[1:]:
      #   cur_win_ptr.waitBlanking = False
      #   cur_win_ptr.flip()
      #   cur_win_ptr.waitBlanking = True
      vbl += clock.tick()
      next_frame_time = vbl + (0.5*ifi)
      num_frames += 1
      # Read the new command and prepare to quit if we shouldn't keep on
      # rendering
      new_cmd = np.frombuffer(mm_file[:4], dtype=np.uint32)[0]
      if cur_cmd == 1 and new_cmd == 2:
        # print("Setting start time")
        render_start_time = core.monotonicClock.getTime()
      elif new_cmd == 0 or vbl - loop_start_time > REST_AFTER_SECS:
        break
      cur_cmd = new_cmd
    # print("New cur cmd:", new_cmd)
    if render_start_time:
      time_taken = core.monotonicClock.getTime() - render_start_time
      print(f"num_frames: {num_frames} - over: {time_taken}s - Frame rate: "
            f"{num_frames/time_taken} FPS")
      # print(f"Slept for: {wait_time}s uin {times_slept}/{num_frames} frames -"
      #       f" time: {wait_time/num_frames} Per frame")
      self._frame_rate = num_frames/time_taken
    return new_cmd
