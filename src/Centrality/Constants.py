# ------------------------------------------------------------------------------
# Urban Network Analysis Toolbox for ArcGIS10
# Credits: Michael Mekonnen, Andres Sevtsuk
# MIT City Form Research Group
# Usage: Creative Commons Attribution - NonCommercial - ShareAlike 3.0 Unported
#   License
# License: http://creativecommons.org/licenses/by-nc-sa/3.0/
# ------------------------------------------------------------------------------

"""
Constants.
"""
import sys
from os.path import join
from sys import path

# Location of Scripts
SCRIPT_DIR = path[0]

# The six steps of the tool
STEP_1 = "Computing adjacency list"
STEP_2 = "Building graph from adjacency list"
STEP_3 = "Retrieving necessary node attributes"
STEP_4 = "Running centrality computation"
STEP_5 = "Writing out results"
STEP_6 = "Displaying results"


# Inputs to the tool
# Denote each input by its index
def index():
  i = 0
  while True:
    yield i
    i += 1


input_number = index()

INPUT_BUILDINGS = next(input_number)
POINT_LOCATION = next(input_number)
INPUT_NETWORK = next(input_number)
COMPUTE_REACH = next(input_number)
COMPUTE_GRAVITY = next(input_number)
COMPUTE_BETWEENNESS = next(input_number)
COMPUTE_CLOSENESS = next(input_number)
COMPUTE_STRAIGHTNESS = next(input_number)
ID_ATTRIBUTE = next(input_number)
NODE_WEIGHT_ATTRIBUTE = next(input_number)
IMPEDANCE_ATTRIBUTE = next(input_number)
SEARCH_RADIUS = next(input_number)
USE_NETWORK_RADIUS = next(input_number)
BETA = next(input_number)
NORMALIZE_RESULTS = next(input_number)
OUTPUT_LOCATION = next(input_number)
OUTPUT_FILE_NAME = next(input_number)
ACCUMULATOR_ATTRIBUTES = next(input_number)
OUTPUT_FEATURE_CLASS = next(input_number)

# Number of inputs
INPUT_COUNT = next(input_number)

# Network vs. Euclidean radius option
ON_THE_NETWORK_OPTION = "On the network"

# We convert input buildings to point feature class
INPUT_POINTS = "INPUT_POINTS"
# Name of input points after feature to point conversion
# POINT_FEATURE_CLASS_NAME = lambda feature_class_name, point_location: (
#     ("%s_%s_FeatureToPoint" % (feature_class_name, point_location)))


def POINT_FEATURE_CLASS_NAME(feature_class_name, point_location):
    return f"{feature_class_name}_{point_location}_FeatureToPoint"


# Console messages
INPUT_BUILDINGS_COPY_STARTED = "[started] Copying input buildings"
INPUT_BUILDINGS_COPY_FINISHED = "[finished]"
INPUT_BUILDINGS_COPY_FAILED = "[failed]"

PROGRESS_NORMALIZATION = "Normalizing results"

WARNING_LARGE_ADJ_FILE_NAME = ("Adjacency list DBF name is too large, "
                               "please rerun with shorter input file names")
WARNING_OUTPUT_ALREADY_EXISTS = "Output with the same name already exists"
# WARNING_NO_EDGE_FEATURE = lambda input_network: ("%s does not have edge feature"
#                                                  % input_network)
# WARNING_NO_JUNCTION_FEATURE = lambda input_network: ("%s does not have junction"
#                                                      " feature" % input_network)
# WARNING_POINTS_NOT_IN_GRAPH = lambda in_graph, not_in_graph: ("%d out of %d "
#                                                               "input points not recorded in graph" % (
#                                                                 not_in_graph, (in_graph +
#                                                                                not_in_graph)))


def WARNING_NO_EDGE_FEATURE(input_network):
  return f"{input_network} does not have edge feature"


def WARNING_NO_JUNCTION_FEATURE(input_network):
  return f"{input_network} does not have junction feature"


def WARNING_POINTS_NOT_IN_GRAPH(in_graph, not_in_graph):
  return f"{not_in_graph} out of {in_graph + not_in_graph} input points not recorded in graph"


WARNING_NO_NODES = "No nodes in graph"
WARNING_APPLY_SYMBOLOGY_FAILED = "Failed to apply symbology to output layer"
WARNING_FAIL_TO_DISPLAY = "Layer produced but not displayed"
WARNING_NO_BETWEENNESS_NORMALIZATION = ("Betweenness values were not normalized"
                                        " since not all nodes were used as origins")

POINT_CONVERSION_STARTED = ("... [started] Converting polygons to network "
                            "locations")
POINT_CONVERSION_FINISHED = "... [finished]"
POINT_CONVERSION_DONE = "Conversion has already been done"

ADJACENCY_LIST_COMPUTED = "Adjacency list already computed on previous run"

BARRIER_COST_PRE_PROCESSING = "Barrier cost computation pre-processing"
BARRIER_COST_COMPUTATION = "Barrier cost computation"
BARRIER_COST_COMPUTATION_STARTED = "... [started] Computing barrier costs"
BARRIER_COST_COMPUTATION_FINISHED = "... [finished]"

CALCULATE_LOCATIONS_STARTED = ("... [started] Calculating locations on the "
                               "network")
CALCULATE_LOCATIONS_FINISHED = "... [finished]"

ADDING_DESTINATIONS_STARTED = ("... [started] Adding destinations to OD cost "
                               "matrix layer")
ADDING_DESTINATIONS_FINISHED = "... [finished]"
ADDING_BARRIERS_STARTED = ("... [started] Adding barriers to OD cost matrix "
                           "layer")
ADDING_BARRIERS_FINISHED = "... [finished]"

STEP_1_STARTED = "[1 started] %s" % STEP_1
STEP_1_FAILED = "[1 failed] "
STEP_1_FINISHED = "[1 finished]"
STEP_2_STARTED = "[2 started] %s" % STEP_2
STEP_2_FAILED = "[2 failed]"
STEP_2_FINISHED = "[2 finished]"
STEP_3_STARTED = "[3 started] %s" % STEP_3
STEP_3_FAILED = "[3 failed]"
STEP_3_FINISHED = "[3 finished]"
STEP_4_STARTED = "[4 started] %s" % STEP_4
STEP_4_FAILED = "[4 failed]"
STEP_4_FINISHED = "[4 finished]"
STEP_5_STARTED = "[5 started] %s" % STEP_5
STEP_5_FAILED = "[5 failed]"
STEP_5_FINISHED = "[5 finished]"
STEP_6_STARTED = "[6 started] %s" % STEP_6
STEP_6_FAILED = "[6 failed]"
STEP_6_FINISHED = "[6 finished]"

SUCCESS = "Successful!"
FAILURE = "Not successful"

# Node attribute names
NEIGHBORS = "Neighbors"
LOCATION = "Location"
WEIGHT = "Weight"
REACH = "Reach"
NORM_REACH = "Norm_Reach"
GRAVITY = "Gravity"
NORM_GRAVITY = "Norm_Gravity"
BETWEENNESS = "Betweenness"
NORM_BETWEENNESS = "Norm_Betweenness"
CLOSENESS = "Closeness"
NORM_CLOSENESS = "Norm_Closeness"
STRAIGHTNESS = "Straightness"
NORM_STRAIGHTNESS = "Norm_Straightness"

# Attributes that might be written to file
METRICS = (REACH, GRAVITY, BETWEENNESS, CLOSENESS, STRAIGHTNESS)
NORM_METRICS = (NORM_REACH, NORM_GRAVITY, NORM_BETWEENNESS, NORM_CLOSENESS,
                NORM_STRAIGHTNESS)
FINAL_ATTRIBUTES = METRICS + NORM_METRICS

# Constants for adjacency list computation
# Network feature type identifiers
EDGE_FEATURE = "EdgeFeature"
JUNCTION_FEATURE = ("JunctionFeature", "SystemJunction")
# Network location field names
NETWORK_LOCATION_FIELDS = ("SourceID", "SourceOID", "PosAlong", "SideOfEdge",
                           "SnapX", "SnapY", "Distance")
# Number of entries in the OD matrix during a solve
OD_MATRIX_ENTRIES = 10 * 10**6
# High cost assigned to buildings to stop neighbor search when a building is
#     encountered
BARRIER_COST_FIELD = "Barrier_Cost"
# BARRIER_COST = (maxint / 5) * 2
BARRIER_COST = (sys.maxsize / 5) * 2
# Maximum extent of search on the network
SEARCH_TOLERANCE = "5000 Meters"
# Distance offset when buildings are snapped to the network
SNAP_OFFSET = "5 Meters"
# Origin and Destination ID names
ORIGIN_ID_FIELD_NAME = "OriginID"
DESTINATION_ID_FIELD_NAME = "DestinationID"


# File names
def feature_class_name(base):
  return f"{base}_Featureclass"


def layer_name(base):
  return f"{base}_Layer"


def get_symbology_layer_name(shape_type, first_metric):
  return f"{shape_type}_{first_metric}_Symbology_Layer.lyr"


SYMBOLOGY_DIR_NAME = "Symbology_Layers"
SYMBOLOGY_DIR = join(SCRIPT_DIR, SYMBOLOGY_DIR_NAME)
ADJACENCY_LIST_NAME = "Adj"
AUXILIARY_DIR_NAME = "Auxiliary_Files"
OD_COST_MATRIX_LAYER_NAME = layer_name("OD_Cost_Matrix")
OD_COST_MATRIX_LINES = "Lines"


def TEMP_ADJACENCY_DBF_NAME(adj_dbf_name):
  return f"Temp_{adj_dbf_name}"


POLYGONS_SHAPEFILE_NAME = "Polygons.shp"
PARTIAL_ADJACENCY_LIST_NAME = "Partial_Adjacency_List.dbf"
POLYGONS_LAYER_NAME = layer_name("Polygons")
RASTER_NAME = "Raster"
INPUT_POINTS_LAYER_NAME = layer_name("Input_Points")

# Name of the column that stores the original FID of polygons when converting to
#     points
ORIGINAL_FID = "ORIG_FID"

# Largest allowed length of a file name
MAX_FILE_NAME_LENGTH = 160

# Representation for an infinite radius (or infinite extent on the network)
# INFINITE_RADIUS = sys.maxint
INFINITE_RADIUS = sys.maxsize

# Tolerance for inequality (if abs(a - b) <= |TOLERANCE|, consider a and b equal)
TOLERANCE = 0.000001
