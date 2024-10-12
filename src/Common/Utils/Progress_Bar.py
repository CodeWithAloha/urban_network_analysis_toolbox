"""
Easy to use progress bar to provide feedback while a tool is running.
"""

__author__ = 'mikemeko@mit.edu (Michael Mekonnen)'

from arcpy import ResetProgressor
from arcpy import SetProgressor
from arcpy import SetProgressorLabel
from arcpy import SetProgressorPosition


class Progress_Bar:
  """
  Wrapper for the arcpy progress bar.
  """
  def __init__(self, n, p, caption):
    """
    |n|: number of steps to count to.
    |p|: display is updated every |p| steps.
    |caption|: message to display with the progress bar.
    """
    self._n = n
    self._p = p
    self._caption = caption
    # Create progress bar
    self._bar = self._progress_bar()
    # Start progress bar
    self.step()

  def step(self):
    """
    Move the progress bar by 1 step
    """
    next(self._bar)

  def _progress_bar(self):
    """
    A generator representation of the arcpy progressor
    """
    # Setup progressor with min, max, interval, and label
    SetProgressor("step", "", 0, self._n, self._p)
    SetProgressorLabel(self._caption)
    # Counter
    count = 0
    while True:
      # Update display
      if count % self._p == 0:
        SetProgressorPosition(count)
      # Finished?
      if count == self._n:
        SetProgressorLabel("")
        ResetProgressor()
      count += 1
      yield
