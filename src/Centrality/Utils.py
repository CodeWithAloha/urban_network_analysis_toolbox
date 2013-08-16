# ------------------------------------------------------------------------------
# Urban Network Analysis Toolbox for ArcGIS10
# Credits: Michael Mekonnen, Andres Sevtsuk
# MIT City Form Research Group
# Usage: Creative Commons Attribution - NonCommercial - ShareAlike 3.0 Unported
#   License
# License: http://creativecommons.org/licenses/by-nc-sa/3.0/
# ------------------------------------------------------------------------------

"""
Utility methods.
"""

from arcpy import AddMessage
from arcpy import AddWarning
from arcpy import CalculateLocations_na
from arcpy import Delete_management
from arcpy import Describe
from arcpy import Exists
from arcpy import FeatureToPoint_management
from arcpy import UpdateCursor
from Constants import CALCULATE_LOCATIONS_FINISHED
from Constants import CALCULATE_LOCATIONS_STARTED
from Constants import EDGE_FEATURE
from Constants import JUNCTION_FEATURE
from Constants import POINT_CONVERSION_DONE
from Constants import SEARCH_TOLERANCE
from Constants import TOLERANCE
from Constants import WARNING_NO_EDGE_FEATURE
from Constants import WARNING_NO_JUNCTION_FEATURE
from math import sqrt
from os import remove
from os import rmdir
from os.path import basename as os_basename
from os.path import isfile
from os.path import isdir
from os.path import splitext

class Invalid_Input_Exception(Exception):
  """
  Exception thrown when input is invalid
  """

  def __init__(self, input_name):
    """
    |input_name|: the name of the invalid input
    """
    Exception.__init__(self, "Invalid Input: %s" % input_name)

class Invalid_Parameters_Exception(Exception):
  """
  Exception thrown when parameters to a method are invalid
  """
  pass

def to_point_feature_class(feature_class, point_feature_class, point_location):
  """
  Converts a feature class to a point feature class
  |point_location|: parameter for conversion, should be "CENTROID" or "INSIDE"
  """
  if Exists(point_feature_class):
    AddMessage(POINT_CONVERSION_DONE)
  else:
    FeatureToPoint_management(in_features=feature_class,
        out_feature_class=point_feature_class,
        point_location=point_location)

def all_values_in_column(table, column):
  """
  Returns a set of all the values in the some column of a table
  |table|: a dbf
  |column|: the name of a column in the table, the column must be in the table
  """
  values = set()
  rows = UpdateCursor(table)
  for row in rows:
    values.add(row.getValue(column))
  return values

def network_features(network):
  """
  Returns the junction and edge feature names of |network|
  |network|: a network dataset
  """
  edge_feature = None
  junction_feature = None
  for source in Describe(network).sources:
    if source.sourceType == EDGE_FEATURE:
      edge_feature = source.name
    elif source.sourceType in JUNCTION_FEATURE:
      junction_feature = source.name
  if edge_feature == None:
    AddWarning(WARNING_NO_EDGE_FEATURE(network))
    raise Invalid_Input_Exception("Input Network")
  if junction_feature == None:
    AddWarning(WARNING_NO_JUNCTION_FEATURE(network))
    raise Invalid_Input_Exception("Input Network")
  return (junction_feature, edge_feature)

def calculate_network_locations(points, network):
  """
  Computes the locations of |points| in |network|
  |points|: a feature class (points or polygons)
  |network|: a network dataset
  """
  AddMessage(CALCULATE_LOCATIONS_STARTED)
  CalculateLocations_na(in_point_features=points,
      in_network_dataset=network,
      search_tolerance=SEARCH_TOLERANCE,
      search_criteria=("%s SHAPE; %s SHAPE;" %
          network_features(network)),
      exclude_restricted_elements="INCLUDE")
  AddMessage(CALCULATE_LOCATIONS_FINISHED)

def eq_tol(a, b):
  """
  Returns True if |a| and |b| are within |TOLERANCE|, False otherwise
  """
  return abs(a - b) <= TOLERANCE

def lt_tol(a, b):
  """
  Returns True if |a| is less than |b| by more than |TOLERANCE|, False otherwise
  """
  return b - a > TOLERANCE

def basename(path):
  """
  Returns the base name of |path|, not including the extension
  """
  return splitext(os_basename(path))[0]

def delete(path):
  """
  Deletes the file or directory located at |path|
  """
  try:
    # Attempt to delete using arcpy methods
    if Exists(path):
      Delete_management(path)
  except:
    # If arcpy methods fail, attempt to delete using native methods
    try:
      if isfile(path):
        remove(path)
      elif isdir(path):
        rmdir(path)
    except:
      pass

def trim(field_name):
  """
  Returns the first 10 characters of |field_name|
  (DBF files truncate field names to 10 characters)
  """
  return field_name[:10]

def dist(loc1, loc2):
  """
  Computes the euclidean distance between |loc1| and |loc2|
  |loc1|: (x1, y1)
  |loc2|: (x2, y2)
  """
  x1, y1 = loc1
  x2, y2 = loc2
  return sqrt((x1 - x2)**2 + (y1 - y2)**2)

def merge_maps(map1, map2, f):
  """
  Returns comb_map, such that comb_map[key] = |f|(|map1|[key], |map2|[key])
  |map1| and |map2| must have the same keys
  """
  if set(map1.keys()) != set(map2.keys()):
    raise Exception("Invalid input, dictionaries must have the same keys")
  comb_map = {}
  for key in map1:
    comb_map[key] = f(map1[key], map2[key])
  return comb_map

def row_has_field(row, field):
  """
  Returns True if |row| has the field |field|, False otherwise
  """
  try:
    row.getValue(field)
    return True
  except:
    return False

def is_accumulator_field(field):
  """
  Returns True if |field| is an accumulator field, False otherwise
  """
  return field.startswith("Total_")
