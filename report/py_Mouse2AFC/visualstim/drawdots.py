import time
import numpy as np
import pandas as pd
from psychopy import core
from psychopy.tools.monitorunittools import deg2pix
import pyglet.gl as GL
from pyglet import clock
from psychopy import visual
from common.definitions import DrawStimType
from common.loadSerializedData import loadSerializedData
from . import dotsshaders as ds
# from .checkclose import checkClose

TEST_RATIO = False
REST_AFTER_SECS = 5*60

class DrawDots:
  def __init__(self, wins_ptrs, win_size, photo_diode_size, photo_diode_pos,
               frame_rate, monitor):
    self._wins_ptrs = wins_ptrs
    self._win_size = win_size
    self._frame_rate = frame_rate
    self._monitor = monitor

    self._fill_rects = []
    self._photo_diode_boxes = []
    self._pix_scale = []
    for cur_win_ptr in self._wins_ptrs:
      rect = visual.Rect(cur_win_ptr, units="norm",  pos=(0, 0), size=(2, 2),
                         fillColor="black", lineColor="black")
      self._fill_rects.append(rect)
      box = visual.Rect(cur_win_ptr, units="norm", fillColor="white",
                        lineColor="white",  pos=photo_diode_pos,
                        size=photo_diode_size)
      self._photo_diode_boxes.append(box)
      # Next part is adapted from psychopy's visual.window.py:setScale()
      prev_scale = np.asarray((1.0, 1.0))
      this_scale = (2.0 / win_size) *  (2 if cur_win_ptr.useRetina else 1)
      self._pix_scale.append(this_scale/prev_scale)
    # Maybe converting it to numpy would yield faster looping?
    self._fill_rects = np.array(self._fill_rects)
    self._photo_diode_boxes = np.array(self._photo_diode_boxes)
    self._pix_scale = np.array(self._pix_scale)

    # Create a very big buffer to hold the dots
    self._dots_arr_buf = np.empty((50000, 2)) # 2: Prepare for x,y
    # print("_dots_arr_buf", self._dots_arr_buf.dtype)
    # actually set the scale as appropriate
    # allows undoing of a previous scaling procedure
    # _dots array will be set later as a slice of self.dots_arr_buf. It's being
    # used to reuse memory and in the hope to to speed computations.
    self._dots_arr = None
    self.INCREMENTS_DEG = 45
    self.NUM_DIRECTIONS = int(360/self.INCREMENTS_DEG)
    # Create all the self._directions that we have
    self._directions = np.arange(0, 360, self.INCREMENTS_DEG)
    self._directionsRatios = np.empty(len(self._directions))
    # TODO: Ooptimize the next variable
    self._direction_ndots = None
    # Distance traveled in ch frame movement for each self._directions' x,y
    self._dxy = np.empty((len(self._directions), 2))
    self._rnd_gen = np.random.default_rng()
    MAX_NUM_FRAMES = 20000
    self._frames_cohr = np.zeros((self.NUM_DIRECTIONS,MAX_NUM_FRAMES), np.uint)
    self._frames_timing = np.zeros(MAX_NUM_FRAMES)
    self._frames_enabled = np.zeros(MAX_NUM_FRAMES, np.bool)
    # Variables for handling dots shaders. Flag that we didn't attempt yet to
    # compile shaders
    self._smooth_point_shader = None
    self._attempted_gen_shaders = False
    # Assume all the windows are the same
    (min_smooth_point_Size, max_smooth_point_size, min_aliased_point_size,
      max_aliased_point_size) = ds.dotsSizeRange(self._wins_ptrs[0])
    # max smoothed: 1, 189.875,  max aliased: 1, 2047
    # print(f"minSmoothPointSize: {min_smooth_point_Size} - "
    #       f"max_smooth_point_size: {max_smooth_point_size}")
    # print(f"minAliasedPointSize: {min_aliased_point_size} - "
    #       f"maxAliasedPointSize: {max_aliased_point_size}")
    self._max_aliased_point_size = max_aliased_point_size
    self._max_smooth_point_size = max_smooth_point_size
    self._cur_session_path = ""
    self._df_perf = pd.DataFrame()

  def loop(self, cur_cmd, mm_file):
    while True:
      # Either this is the first run or the next iteration, in both way, clear
      # the screen to prepare for the next run.
      for win_ptr, fill_rect in zip(self._wins_ptrs, self._fill_rects):
        fill_rect.draw()
        win_ptr.waitBlanking = False
        win_ptr.flip(clearBuffer=False)
        win_ptr.waitBlanking = True
      # print("Cur cmd:", cur_cmd)
      # Keep waiting until we receive the load or run command
      while cur_cmd == 0:
        core.wait(0.01) # Sleep until the next command
        [win_ptr.winHandle.dispatch_events() for win_ptr in self._wins_ptrs]
        cur_cmd = np.frombuffer(mm_file[:4], dtype=np.uint32)[0]

      # Load the the drawing parameters
      _, drawParams = loadSerializedData(mm_file, 4)
      if drawParams.stimType != DrawStimType.RDK:
        return cur_cmd, drawParams

      renderLoop_args = self._load(drawParams)
      # import cProfile
      # cProfile.runctx('self._renderLoop(mm_file, cur_cmd, *renderLoop_args)',
      #                 globals=globals(),
      #                 locals={"self": self, "mm_file":mm_file,
      #                         "cur_cmd":cur_cmd,
      #                         "renderLoop_args":renderLoop_args})
      cur_cmd = self._renderLoop(mm_file, cur_cmd, *renderLoop_args)
      if cur_cmd == 1:
        print("Resting due to inactivity...")
        # Just dump current data in case the user wants to analyze it shortly
        if not self._df_perf.empty:
          self._dumpPerf(self._df_perf, self._cur_session_path)
        while cur_cmd == 1:
          [win_ptr.winHandle.dispatch_events() for win_ptr in self._wins_ptrs]
          core.wait(0.3, hogCPUperiod=0)
          cur_cmd = np.frombuffer(mm_file[:4], dtype=np.uint32)[0]
    # We can only break if we want exit
    print("User asked to exit")
    return -1, None

  def _load(self, drawParams):
    # print("drawParams.pulseOffset:", drawParams.pulseOffset)
    # print("drawParams.pulseCohr:", drawParams.pulseCohr)
    # print("drawParams.pulseDur:", drawParams.pulseDur)
    # print("drawParams.TrialNumber:", drawParams.TrialNumber)
    drawParams.sessionPath = drawParams.sessionPath.tostring().decode()
    # print("self._df_perf:", drawParams.sessionPath)
    if not self._df_perf.empty and \
                               self._cur_session_path != drawParams.sessionPath:
      self._dumpPerf(self._df_perf, self._cur_session_path)
      # Clear current df but keep the created columns
      self._df_perf = self._df_perf.iloc[0:0]
    self._cur_session_path = drawParams.sessionPath

    drawParams.apertureSizeWidth = min(1, drawParams.apertureSizeWidth)
    drawParams.apertureSizeHeight = min(1, drawParams.apertureSizeHeight)
    if drawParams.circleRDK:
      # Ellipse area: πab where a and b are the radii of each side
      field_area_pix = (drawParams.apertureSizeWidth*self._win_size[0]/2)*\
                       (drawParams.apertureSizeHeight*self._win_size[1]/2)*np.pi
    else:
      # Rectangle area
      field_area_pix = (drawParams.apertureSizeWidth*self._win_size[0])*\
                       (drawParams.apertureSizeHeight*self._win_size[1])
    # Calculate the size of a dot in pixel
    self._monitor.setWidth(drawParams.screenWidthCm)
    self._monitor.setDistance(drawParams.screenDistCm)
    dot_size_pix = deg2pix(drawParams.dotSizeInDegs, monitor=self._monitor)
    # print(f"dot_size_pix: {dot_size_pix:.3f}", end='')
    if np.rint(dot_size_pix) != dot_size_pix:
      dot_size_pix = np.int(np.rint(dot_size_pix))
      # print(" ==>", dot_size_pix, end='')
    # print()
    ##
    if dot_size_pix <= self._max_smooth_point_size:
      dot_type = 2
    elif dot_size_pix <= self._max_aliased_point_size:
      dot_type = 1
    else:
      dot_type = 3
    # We should calculate the dot_size_pix area based on whether it's a circle
    # or whether it's a rectangle. If we are in test mode, we assume rectangle
    # so that the numbers would add up exactly to the total screen size.
    if not TEST_RATIO and dot_type != 4:
      dot_area = np.pi*((dot_size_pix/2)**2)
    else:
      dot_area = dot_size_pix**2
    nDots = np.around(drawParams.drawRatio*field_area_pix/dot_area)
    # First we'll calculate the left, right top and bottom of the
    # aperture (in degrees)
    # Apreture size between 0 and 1, We need to multiple by 2 to normalize
    # 0:2 to -1:1 then divide by 2, So basically we will just use the
    # apertureSize as its current value.
    # TODO: Create each dimension as an array of pixels between -0.5 to 0.5 so
    # that it would work for circle RDK as well.
    l =  drawParams.centerX - drawParams.apertureSizeWidth/2
    r =  drawParams.centerX + drawParams.apertureSizeWidth/2
    b =  drawParams.centerX - drawParams.apertureSizeHeight/2
    t =  drawParams.centerX + drawParams.apertureSizeHeight/2
    # print(f"l: {l} - r: {r} - b: {b} - t: {t}")

    # Calculate ratio of incoherent for each direction so can use it later
    # to know how many dots should be per each direction. The ratio is
    # equal to the total incoherence divide by the number of self._directions
    # minus one. A coherence of zero has equal opportunity in all
    # self._directions, and thus the main direction ratio is the normal
    # coherence plus the its share of random incoherence.
    main_dir_idx = np.where(self._directions == drawParams.mainDirection)[0][0]
    directionIncoherence = (1-drawParams.coherence)/self.NUM_DIRECTIONS
    self._directionsRatios[:] = directionIncoherence
    self._directionsRatios[main_dir_idx] += drawParams.coherence
    self._inf_main_cohr = drawParams.coherence*100
    # Round the number of dots that we have such that we get whole number
    # for each direction
    self._direction_ndots = np.rint(self._directionsRatios * nDots).astype(np.int)
    # Re-evaluate the number of dots. Convert to int and create as an
    # array so we can pass it as a list.
    nDots = np.int(self._direction_ndots.sum(),)
    # Convert lifetime to number of frames
    # TODO: Fix this as dots frame rate might be variable
    lifetime = np.ceil(drawParams.dotLifetimeSecs * self._frame_rate)
    # The distance traveled by a dot (in degrees) is the speed (degrees/second)
    # divided by the frame rate (frames/second). The units cancel, leaving
    # degrees/frame which makes sense. Basic trigonometry (sines and cosines)
    # allows us to determine how much the changes in the x and y position.
    dot_speed_norm = deg2pix(drawParams.dotSpeed, self._monitor)/self._win_size
    self._dxy[:,0] = (dot_speed_norm[0]*np.sin(self._directions*np.pi/180)/
                      self._frame_rate)
    self._dxy[:,1] = (-dot_speed_norm[1]*np.cos(self._directions*np.pi/180)/
                      self._frame_rate)
    np.set_printoptions(suppress=True)
    # Floor it rather than rounding it, to avoid the case where we might get
    # stuck rounding up requires more dots than available

    if drawParams.pulseCohr > 0:
      drawParams.pulseCohr = min(drawParams.pulseCohr, 1 - drawParams.coherence)
      main_buffer = np.int(np.ceil(np.abs(nDots*drawParams.pulseCohr)))
      non_main_buffer = 0
    elif drawParams.pulseCohr < 0:
      # pulseCohr is -ve, so make sure that we have enough coherence to subtract
      drawParams.pulseCohr = max(drawParams.pulseCohr, -drawParams.coherence)
      main_buffer = 0
      non_main_buffer = np.int(np.ceil(np.abs(nDots*drawParams.pulseCohr))/(
                                                         self.NUM_DIRECTIONS-1))
    else:
      main_buffer = 0
      non_main_buffer = 0
    self._inf_pulse_cohr = drawParams.pulseCohr*100
    # print("main_buffer :", main_buffer, "- Non main buffer:", non_main_buffer)
    if not drawParams.pulseCohr:
      drawParams.pulseOffset = 999
    # Take a slice of the original array, Second dimension has length of 2
    # for x and y
    total_dots = int(nDots + main_buffer +
                     (self.NUM_DIRECTIONS-1)*non_main_buffer)
    self._dots_arr = self._dots_arr_buf[:total_dots, :]
    print("nDots", nDots, "- total dots:", total_dots)
          #, "Dots arr shape:", self._dots_arr.shape)
    # Add one to make it pragmatically easy to access the next index for
    # the last item in the list
    dir_idx_offset = np.empty(self.NUM_DIRECTIONS + 1, np.uint)
    next_offset_idx = 0
    for dir_idx in range(self.NUM_DIRECTIONS):
      dir_idx_offset[dir_idx] = next_offset_idx
      offset = main_buffer if dir_idx == main_dir_idx else non_main_buffer
      # print("next_offset_idx:", next_offset_idx)
      next_offset_idx += self._direction_ndots[dir_idx] + offset
    # Assign last item to the total number of dots
    # print("next_offset_idx:", next_offset_idx, "Total dots:", total_dots)
    assert next_offset_idx == total_dots
    dir_idx_offset[self.NUM_DIRECTIONS] = next_offset_idx
    # print("dir_idx_offset: ", dir_idx_offset)

    # Create all the dots in random starting positions between -0.5 to +0.5 on
    # both x and y axes
    self._dots_arr = self._rnd_gen.random(self._dots_arr.shape,
                                          out=self._dots_arr) - 0.5
    self._dots_arr[:,0] *= drawParams.apertureSizeWidth + drawParams.centerX
    self._dots_arr[:,1] *= drawParams.apertureSizeHeight + drawParams.centerY
    # Each dot will have a integer value 'life' which is how many frames the
    # dot has been going.  The starting 'life' of each dot will be a random
    # number between 0 and dotsParams.lifetime-1 so that they don't all 'die'
    # on the same frame:
    dots_life = np.ceil(self._rnd_gen.random(total_dots)*lifetime)
    # Next part is adapted from Psychtoolbox
    # TODO: Compare against max allowed point size
    if dot_type in (1, 2):
      # Psychtoolbox: A dot type of 2 requests highest quality point smoothing
      GL.glEnable(GL.GL_POINT_SMOOTH)
      GL.glHint(GL.GL_POINT_SMOOTH_HINT,
                GL.GL_NICEST if dot_type == 2 else GL.GL_DONT_CARE)
    else:
      # Disable anti-aliasing for dots
      GL.glDisable(GL.GL_POINT_SMOOTH)
      self._handleShaders(dot_type)

    if TEST_RATIO:
      self._testDrawRatio(nDots, dot_size_pix, dot_type)
      time.sleep(20)
      import sys
      sys.exit(0)
    # GL.glGetFloatv(GL.GL_ALIASED_POINT_SIZE_RANGE, (GLfloat*) &pointsizerange);
    # Need this when drawing the dots later
    return (dot_size_pix, dots_life, lifetime, drawParams.circleRDK,
            drawParams.apertureSizeWidth, drawParams.apertureSizeHeight,
            drawParams.centerX, drawParams.centerY, (l, r, b, t), dot_type,
            drawParams.pulseOffset, drawParams.pulseDur, main_dir_idx,
            dir_idx_offset, main_buffer, non_main_buffer,
            drawParams.TrialNumber)

  def _renderLoop(self, mm_file, cur_cmd, dot_size_pix, dots_life, lifetime,
                  circle_rdk, aperture_size_width, aperture_size_height,
                  center_x, center_y, l_r_b_t, dot_type, pulse_offset,
                  pulse_dur, main_dir_idx, dir_idx_offset, main_buffer,
                  non_main_buffer, trial_number):
    l, r, b, t = l_r_b_t
    # ifi = 1/self._frame_rate
    # next_frame_time = 0
    # print("len(self._dots):", len(self._dots_arr))
    getTime = core.monotonicClock.getTime
    start_pulse_timer = False
    if pulse_offset == 0:
      if non_main_buffer:
        dirs_shortages = np.full(self.NUM_DIRECTIONS, non_main_buffer,
                                  np.uint)
        dirs_shortages[main_dir_idx] = 0
        lending_goal = non_main_buffer * (self.NUM_DIRECTIONS-1)
        lending_start_time = getTime() # Used for debugging
        borrowing_goal = 0
        borrowing_start_time = 0
      else:
        dirs_shortages = np.zeros(self.NUM_DIRECTIONS, dtype=np.uint)
        borrowing_goal = main_buffer
        borrowing_start_time = getTime() # Used for debugging
        lending_goal = 0
        lending_start_time = 0
    else:
      dirs_shortages = np.zeros(self.NUM_DIRECTIONS, dtype=np.uint)
      borrowing_goal = 0
      lending_goal = 0
      borrowing_start_time, lending_start_time = 0, 0
    pulse_start, pulse_end = 0, 0
    pulse_start_debug, pulse_end_debug = 0, 0
    # TODO: Craete these 3 as class arrays, or as a view of class buffers
    directions_range = np.arange(self.NUM_DIRECTIONS)
    all_dirs_range_wo_main = np.concatenate([np.arange(main_dir_idx),
                                 np.arange(main_dir_idx+1,self.NUM_DIRECTIONS)])
    active_dots_mask = np.ones(self._dots_arr.shape[0], dtype=bool)
    for dir_idx in directions_range:
      end_idx = dir_idx_offset[dir_idx+1]
      buffer_size = main_buffer if dir_idx == main_dir_idx else non_main_buffer
      active_dots_mask[end_idx-buffer_size:end_idx] = False
    # cur_cmd = np.frombuffer(mm_file[:4], dtype=np.uint32)[0]
    # TODO: Send trial number as well to check if we missed a whole trial and
    # accordingly if we should load a new config
    # while cur_cmd == 1:
    #   core.wait(0.005) # Wait for the run command
    #   cur_cmd = np.frombuffer(mm_file[:4], dtype=np.uint32)[0]
    #   checkClose(self._wins_ptrs)
    ifi = 1/self._frame_rate
    self._frames_enabled.fill(0)
    self._frames_cohr.fill(0)
    self._frames_timing.fill(0)
    wins_handles = [win_ptr.winHandle for win_ptr in self._wins_ptrs]
    win_ptrs_range = np.arange(len(self._wins_ptrs))
    # [handle.set_vsync(False) for handle in wins_handles]
    rendered_num_frames = 0
    cur_frame_idx = 0
    render_start_time = 0
    vbl = clock.tick()
    loop_start_time = getTime()
    while True:
      good_dots = self._dots_arr[active_dots_mask]
      if circle_rdk:
        enbld_dots = (good_dots[:,0]-center_x)**2/(aperture_size_width/2)**2 + \
                    (good_dots[:,1]-center_y)**2/(aperture_size_height/2)**2 < 1
        good_dots = good_dots[enbld_dots]
      good_dots_pix = (good_dots-0.5) * self._win_size + self._win_size/2

      #print("Good dots:", good_dots_pix)
      for idx in win_ptrs_range:
        # Modified from Psychopy's DotsStim.Draw()
        #self._wins_ptrs[idx]._setCurrent()
        wins_handles[idx].switch_to()
        GL.glPushMatrix()  # push before drawing, pop after
        if dot_type >= 3:
          GL.glMultiTexCoord1f(GL.GL_TEXTURE2, dot_size_pix)
          GL.glUseProgram(self._smooth_point_shader)
        # draw the dots
        # Either call the next setScale() or do what it does
        #cur_win_ptr.setScale('pix') # It's necessary to call this function here
        pix_scale = self._pix_scale[idx]
        GL.glScalef(pix_scale[0], pix_scale[1], 1.0)
        GL.glPointSize(dot_size_pix)
        # load Null textures into multitexteureARB - they modulate with
        # glColor
        # GL.glActiveTexture(GL.GL_TEXTURE0)
        # GL.glEnable(GL.GL_TEXTURE_2D)
        # GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        # GL.glActiveTexture(GL.GL_TEXTURE1)
        # GL.glEnable(GL.GL_TEXTURE_2D)
        # GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glVertexPointer(2, GL.GL_DOUBLE, 0, good_dots_pix.ctypes.data)
        #desiredRGB = self._getDesiredRGB(rgb, colorSpace, contrast)
        #GL.glColor4f(desiredRGB[0], desiredRGB[1], desiredRGB[2],
        #             opacity)
        GL.glColor4f(1, 1, 1, 1) # White (r, g, b) at full opacity
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDrawArrays(GL.GL_POINTS, 0, good_dots_pix.shape[0])
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        # GL.glVertexPointer(2, GL.GL_DOUBLE, 0, 0)
        GL.glPopMatrix()

      now = getTime()
      # Increment (or rather decrement) the 'life' of each dot
      dots_life = dots_life + 1
      #find the 'dead' dots
      dead_dots_idxs = np.where((dots_life % lifetime) == 0)[0]
      # Replace the positions of the dead dots to a random location
      if dead_dots_idxs.shape[0]:
        # print("Found dead dots:", borrowing_goal, lending_goal)
        if borrowing_goal:
          # Filter out main direction idxs
          start_idx = dir_idx_offset[main_dir_idx]
          end_idx = dir_idx_offset[main_dir_idx+1]
          non_main_dead = dead_dots_idxs[(dead_dots_idxs < start_idx) |
                                         (end_idx <= dead_dots_idxs)]
          borrowable_dots_len = len(non_main_dead)
          if borrowing_goal < borrowable_dots_len:
            # If we shuffle and it affects the original dead dots array, it
            # shouldn't make a difference as all the dead_dots will have the
            # same computation later
            np.random.shuffle(non_main_dead)
            non_main_dead = non_main_dead[:borrowing_goal]
            borrowable_dots_len = borrowing_goal
          borrowing_goal -= borrowable_dots_len
          active_dots_mask[non_main_dead] = False
          # Depending on the pulse cohr sign. We can either start by borrowing
          # or lending, for this reason we aren't sure which idxs in the main
          # direction are available to show
          main_dir_mask = active_dots_mask[start_idx:end_idx]
          appearing_idxs = start_idx + np.where(main_dir_mask == False)[0]
          appearing_idxs = appearing_idxs[:borrowable_dots_len]
          active_dots_mask[appearing_idxs] = True
          if not borrowing_goal:
            if pulse_end:
              pulse_end_debug = now - loop_start_time
              pulse_end = 0
            else:
              pulse_start = now
              pulse_start_debug = now - loop_start_time
        elif lending_goal:
          start_idx = dir_idx_offset[main_dir_idx]
          end_idx  = dir_idx_offset[main_dir_idx+1]
          main_dead = dead_dots_idxs[(start_idx <= dead_dots_idxs) &
                                     (dead_dots_idxs < end_idx)]
          lendable_dots_len = len(main_dead)
          if lending_goal < lendable_dots_len:
            # I don't need to shuffle here, already dots locations for a given
            # direction are random.
            main_dead = main_dead[:lending_goal]
            lendable_dots_len = lending_goal
          active_dots_mask[main_dead] = False
          lending_goal -= lendable_dots_len
          dirs_shares = np.ceil(lendable_dots_len * dirs_shortages/np.sum(
                                                dirs_shortages)).astype(np.uint)
          # print("dirs_shares:", dirs_shares, "available_dots:", available_dots,
          #       "dirs_shortages:", dirs_shortages)
          # Shuffle directions just to make sure that we don't fill certain directions first
          # although this effect is quite quite tiny.
          np.random.shuffle(all_dirs_range_wo_main)
          for dir_idx in all_dirs_range_wo_main:
            dir_share = np.amin((lendable_dots_len, dirs_shares[dir_idx]))
            # print("dir_share:", dir_share)
            start_idx = dir_idx_offset[dir_idx]
            end_idx = dir_idx_offset[dir_idx+1]
            dir_mask = active_dots_mask[start_idx:end_idx]
            appearing_idxs = start_idx + np.where(dir_mask == False)[0]
            appearing_idxs = appearing_idxs[:dir_share]
            active_dots_mask[appearing_idxs] = True
            dirs_shortages[dir_idx] -= dir_share
            lendable_dots_len -= dir_share
            if not lendable_dots_len:
              break
          if not lending_goal:
            if pulse_end:
              pulse_end_debug = now - loop_start_time
              pulse_end = 0
            else:
              pulse_start = now
              pulse_start_debug = now - loop_start_time
        # Use store location from the end of the dots buffer array
        dead_dots = self._dots_arr_buf[-dead_dots_idxs.shape[0]:,:]
        #print("Dead dots:", dead_dots)
        #print("Dead dots life:", dots_life[dead_dots_idxs])
        dead_dots = self._rnd_gen.random(dead_dots.shape, out=dead_dots) - 0.5
        dead_dots[:,0] *= aperture_size_width + center_x
        dead_dots[:,1] *= aperture_size_height + center_y
        #print("new replacing dots:", dead_dots)
        # Assign back to original array
        self._dots_arr[dead_dots_idxs] = dead_dots
        #print("Deda dots idxss:", dead_dots_idxs)
        dots_life[dead_dots_idxs] = 1

      # Update the dots for each direction
      firstIdx = 0
      lastIdx = 0
      for directionIdx in directions_range:
        lastIdx = dir_idx_offset[directionIdx+1]
        # Update the dot position
        self._dots_arr[firstIdx:lastIdx] += self._dxy[directionIdx]
        # TODO: Disable this part unless we are profiling performance
        self._frames_cohr[directionIdx, cur_frame_idx] =\
                                      np.sum(active_dots_mask[firstIdx:lastIdx])
        firstIdx = lastIdx
      self._frames_enabled[cur_frame_idx] = render_start_time > 0
      self._frames_timing[cur_frame_idx] = now - loop_start_time
      # Move the dots that are outside the aperture back one aperture
      # width.
      self._dots_arr[self._dots_arr[:,0]<l,0] += aperture_size_width
      self._dots_arr[self._dots_arr[:,0]>r,0] -= aperture_size_width
      self._dots_arr[self._dots_arr[:,1]<b,1] += aperture_size_height
      self._dots_arr[self._dots_arr[:,1]>t,1] -= aperture_size_height

      # Finally draw the corner box for the photo diode to detect
      [box.draw() for box in self._photo_diode_boxes]
      # sleep_for = next_frame_time - core.monotonicClock.getTime()
      # if sleep_for > 0:
      #   # times_slept += 1
      #   # wait_time += sleep_for
      #   core.wait(sleep_for)
      # Now we can render
      if cur_cmd != 2: # To keep the flip() in cache, we flip() anyhow but we
                       # might clear first if we shouldn't render yet
        for handle in wins_handles:
          handle.switch_to()
          handle.clear()
        rendered_num_frames -= 1
      # https://stackoverflow.com/a/56761157/11996983
      for handle in wins_handles:
        handle.switch_to()
        # Use only if vsync is disabled, but doesn't give the expected effect of
        # manually forcing vsync
        # GL.glFinish()
        handle.flip()
        handle.clear()
        # poll the operating system event queue
        handle.dispatch_events()

      #vbl = self._wins_ptrs[0].flip()
      # wins_handles[0].switch_to()
      # wins_handles[0].flip()
      # signify to pzglet that one frame has passed
      vbl += clock.tick()
      rendered_num_frames += 1
      cur_frame_idx = (cur_frame_idx+1)%len(self._frames_enabled)
      # wins_handles[0].clear()
      # poll the operating system event queue
      # wins_handles[0].dispatch_events()
      # next_frame_time = vbl + (0.5*ifi)
      # for cur_win_ptr in wins_handles[1:]:
        # cur_win_ptr.waitBlanking = False
        # cur_win_ptr.flip()
        # cur_win_ptr.waitBlanking = True
      # Read the new command and prepare to quit if we shouldn't keep on
      # rendering
      new_cmd = np.frombuffer(mm_file[:4], dtype=np.uint32)[0]
      now = getTime()
      if new_cmd == 0 or now - loop_start_time > REST_AFTER_SECS:
        break
      elif cur_cmd == 1 and new_cmd == 2:
        # print("Setting start time")
        render_start_time = now
        # Only start pulse timer if it wasn't already started
        if pulse_start:
          pulse_start = now # Reset pulse start to now
          start_pulse_timer = False
        else:
          start_pulse_timer = True
      # Add ifi to count for next frame
      elif start_pulse_timer and now + ifi - render_start_time > pulse_offset:
        if non_main_buffer:
          dirs_shortages = np.full(self.NUM_DIRECTIONS, non_main_buffer,
                                   np.uint)
          dirs_shortages[main_dir_idx] = 0
          lending_goal = non_main_buffer * (self.NUM_DIRECTIONS-1)
          lending_start_time = now - loop_start_time # Used for debugging
        else: # i.e main_buffer > 0
          #  dirs_shortages = np.zeros(NUM_DIRECTIONS, np.uint)
          #  dirs_shortages[main_dir_idx] = main_buffer
          borrowing_goal = main_buffer
          borrowing_start_time = now - loop_start_time # Used for debugging
        start_pulse_timer = False
      elif render_start_time and pulse_start and \
           now + ifi - pulse_start >= pulse_dur:
        if non_main_buffer:
          borrowing_goal =  non_main_buffer * (self.NUM_DIRECTIONS-1)
          borrowing_start_time = now - loop_start_time # Used for debugging
        else:  # i.e main_buffer > 0:
          dirs_shortages = np.full(self.NUM_DIRECTIONS, main_buffer/
                                   (self.NUM_DIRECTIONS-1), np.uint)
          dirs_shortages[main_dir_idx] = 0
          lending_goal = main_buffer # Repay all what we have borrowed
          lending_start_time = now - loop_start_time # Used for debugging
        pulse_start = 0 # Don't check for it again
        pulse_end = now
        pulse_end_debug = now - loop_start_time
      cur_cmd = new_cmd
    # print("New cur cmd:", new_cmd)
    if render_start_time:
      time_taken = now - render_start_time
      print(f"num_frames: {rendered_num_frames} - over: {time_taken}s - "
            f"Frame rate: {rendered_num_frames/time_taken:.3f} FPS")
      if lending_start_time or borrowing_start_time:
        if borrowing_start_time < lending_start_time:
          first, first_time = "borrowing", borrowing_start_time
          second, second_time = "repaying", lending_start_time
        else:
          first, first_time = "lending", lending_start_time
          second, second_time = "collecting back", borrowing_start_time
        offset_ms = int((render_start_time - loop_start_time)*1000)
        first_time_ms = int(first_time*1000) - offset_ms
        second_time_ms = int(second_time*1000) - offset_ms
        pulse_start_debug_ms = int(pulse_start_debug*1000) - offset_ms
        pulse_end_debug_ms = int(pulse_end_debug*1000) - offset_ms
        first_dur_ms = pulse_start_debug_ms-first_time_ms
        second_dur_ms = pulse_end_debug_ms-second_time_ms
        print(f"Started {first} at {first_time_ms}ms => "
              f"{pulse_start_debug_ms}ms (dur {first_dur_ms}ms)")
        print(f"Started {second} at {second_time_ms}ms => "
              f"{pulse_end_debug_ms}ms (dur {second_dur_ms}ms)")
      # print(f"Slept for: {wait_time}s uin {times_slept}/{rendered_num_frames}"
      #       f"frames time: {wait_time/rendered_num_frames} Per frame")
      self._frame_rate = rendered_num_frames/time_taken
      self._logPerf(trial_number, main_dir_idx, max_frame_idx=cur_frame_idx,
                    time_pulse_start=pulse_start_debug,
                    time_borrow_start=borrowing_start_time,
                    time_lend_start=lending_start_time,
                    time_pulse_end=pulse_end_debug,
                    inf_pulse_offset=pulse_offset, inf_pulse_dur=pulse_dur,
                    inf_cohr=self._inf_main_cohr,
                    inf_pulse_cohr=self._inf_pulse_cohr)
    return new_cmd

  def _logPerf(self, trial_number, main_dir_idx, max_frame_idx, **kargs):
    # max_idx = np.where(self._frames_timing > 0)[0][-1] + 1
    def dirCol(dir_idx):
      return f"Dir{dir_idx}Dots"
    dirs_idxs = np.arange(self.NUM_DIRECTIONS)
    all_dirs_cols = [dirCol(idx) for idx in dirs_idxs]
    df_dict = {"TrialNumber":int(trial_number),
               "Enabled":self._frames_enabled[:max_frame_idx],
               "FrameTime":self._frames_timing[:max_frame_idx],
               "Cohr":np.NaN}# WIll be set later few lines below}
    df_dict.update(kargs)
    for dir_idx, dir_name in zip(dirs_idxs, all_dirs_cols):
      df_dict[dir_name] = self._frames_cohr[dir_idx,:max_frame_idx]
    trial_df = pd.DataFrame(df_dict)
    main_col = dirCol(main_dir_idx)
    all_other_cols = [col for col in all_dirs_cols if col != main_col]
    # Cohr = Main cohr dots - mean of others directions dots / summ of all dots
    trial_df["Cohr"] = (trial_df[main_col] -
                        trial_df[all_other_cols].mean(axis=1)) / \
                       trial_df[all_dirs_cols].sum(axis=1)
    self._df_perf = self._df_perf.append(trial_df, ignore_index=True)
    #
    # print("df[all_other_cols]:", df[all_other_cols])
    # print("df[all_other_cols] mean:", df[all_other_cols].mean(axis=1))
    # print("df[all_cols]:", df[all_cols])
    # print("df[all_cols] sum:", df[all_cols].sum(axis=1))

  def _dumpPerf(self, df, session_path):
    from pathlib import Path
    fp = Path(session_path.replace("Session Data", "RDK_Data")[:-4] + ".pkl")
    fp.parent.mkdir(exist_ok=True)
    # import os
    # os.makedirs(dir_part, exist_ok=True)
    fp = f"{fp}"
    print(f"Dumping rdk performance logs to to desk: {fp}")
    df.to_pickle(fp)

  def _testDrawRatio(self, num_dots, dot_size_pix, dot_type):
    cur_x = dot_size_pix - self._win_size[0]/2
    cur_y = self._win_size[1]/2 - dot_size_pix/2
    idx = 0
    while idx < num_dots:
      self._dots_arr[idx,:] = cur_x, cur_y
      idx += 1
      cur_x += dot_size_pix
      if cur_x > self._win_size[0]/2:
        cur_x -= self._win_size[0]
        cur_y -= dot_size_pix
    dots = self._dots_arr[:idx,:]
    print(f"Win-limits x={-self._win_size[0]/2} -> {self._win_size[0]/2}")
    print(f"   X min={np.amin(dots[:,0])} - max={np.amax(dots[:,0])}")
    print(f"Win-limits y={-self._win_size[1]/2} -> {self._win_size[1]/2}")
    print(f"   Y min={np.amin(dots[:,1])} - max={np.amax(dots[:,1])}")
    print(f"Last dot at: {dots[-1,:]}")
    # Modified from Psychopy's DotsStim.Draw()
    cur_win_idx = 0
    self._wins_ptrs[cur_win_idx].winHandle.switch_to()
    GL.glPushMatrix()  # push before drawing, pop after
    if dot_type >= 3:
      GL.glMultiTexCoord1f(GL.GL_TEXTURE2, dot_size_pix)
      GL.glUseProgram(self._smooth_point_shader)
    # draw the dots
    pix_scale = self._pix_scale[cur_win_idx]
    GL.glScalef(pix_scale[0], pix_scale[1], 1.0)
    GL.glPointSize(dot_size_pix)
    GL.glVertexPointer(2, GL.GL_DOUBLE, 0, dots.ctypes.data)
    GL.glColor4f(1, 1, 1, 1) # White (r, g, b) at full opacity
    GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
    GL.glDrawArrays(GL.GL_POINTS, 0, dots.shape[0])
    GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
    GL.glPopMatrix()
    self._wins_ptrs[cur_win_idx].winHandle.flip()

  def _handleShaders(self, dot_type):
    if not self._attempted_gen_shaders:
      from .dotsshaderscode import PointSmoothFragmentShaderSrc, \
                                   PointSmoothVertexShaderSrc
      PsychtoolBox_COMPILE = True
      if PsychtoolBox_COMPILE:
        self._smooth_point_shader = ds.CreateGLSLProgram(
           PointSmoothFragmentShaderSrc, PointSmoothVertexShaderSrc, debug=True)
      else:
        from OpenGL.GL.shaders import compileProgram, compileShader
        self._smooth_point_shader = compileProgram(
            compileShader(PointSmoothVertexShaderSrc, GL.GL_VERTEX_SHADER),
            compileShader(PointSmoothFragmentShaderSrc, GL.GL_FRAGMENT_SHADER))
      print("Shaders:", self._smooth_point_shader)
      self._attempted_gen_shaders = True

    if self._smooth_point_shader:
      GL.glUseProgram(self._smooth_point_shader)
      # ^ Or we can use SetShader(self._smooth_point_shader)
      GL.glActiveTexture(GL.GL_TEXTURE1)
      GL.glTexEnvi(GL.GL_POINT_SPRITE, GL.GL_COORD_REPLACE, GL.GL_TRUE)
      GL.glActiveTexture(GL.GL_TEXTURE0)
      GL.glEnable(GL.GL_POINT_SPRITE)
      # Tell shader from where to get its color information: Unclamped
      # high precision colors from texture coordinate set 0, or regular
      # colors from vertex color attribute?
      DefaultDrawShader = 0 # 1 or 0, zero by default
      GL.glUniform1i(GL.glGetUniformLocation(self._smooth_point_shader,
                                             b"useUnclampedFragColor"),
                     DefaultDrawShader)
      # Tell shader if it should shade smooth round dots, or square dots
      GL.glUniform1i(GL.glGetUniformLocation(self._smooth_point_shader,
                                             b"drawRoundDots"),
                     1 if dot_type == 3 else 0)
      # Tell shader about current point size in pointSize uniform:
      GL.glEnable(GL.GL_PROGRAM_POINT_SIZE)
      GL.glDisable(GL.GL_POINT_SMOOTH)
