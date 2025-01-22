"""
Main file for redundancy index tool.
"""

__author__ = 'raul_kalvo, mikemeko'
__date__ = 'June 24, 2013'

from arcpy import AddError
from arcpy import AddField_management
from arcpy import AddMessage
from arcpy import AddWarning
from arcpy import ApplySymbologyFromLayer_management
from arcpy import CopyFeatures_management
from arcpy import Describe
from arcpy import env
from arcpy import MakeFeatureLayer_management
from arcpy import SaveToLayerFile_management
from arcpy.da import UpdateCursor
# from arcpy.mapping import Layer
# from arcpy.mp import Layer
from arcpy import mp
from Common.Utils.Progress_Bar import Progress_Bar
from math import sqrt
from .Network import construct_network_and_load_buildings
from os.path import join
from .RedundancyIndex import find_redundancy_index
from sys import argv
from sys import path
from .Utils import add_layer_to_display
from .Utils import fields
from .Utils import flagged_points
from .Utils import is_number
from .Utils import network_cost_attributes
from .Utils import select_edges_from_network


def main():
    # tool inputs
    INPUT_NETWORK = argv[1]
    INPUT_POINTS = argv[2]
    INPUT_ORIGINS_FIELD = argv[3]
    INPUT_DESTINATIONS_FIELD = argv[4]
    INPUT_BUILDING_WEIGHTS_FIELD = argv[5]
    INPUT_COEFF = float(argv[6])
    INPUT_SEARCH_RADIUS = float(argv[7]) if is_number(
        argv[7]) else float('inf')
    INPUT_OUTPUT_DIRECTORY = argv[8]
    INPUT_OUTPUT_FEATURE_CLASS_NAME = argv[9]

    # check that network has "Length" attribute
    if "Length" not in network_cost_attributes(INPUT_NETWORK):
        AddError(f"Network <{INPUT_NETWORK}> does not have Length attribute")
        return

    # check that coeff is at least 1
    if INPUT_COEFF < 1:
        AddError(f"Redundancy coefficient <{INPUT_COEFF}> must be at least 1")
        return

    # if we are given a building weights field, check that it is valid
    if INPUT_BUILDING_WEIGHTS_FIELD == "#":
        INPUT_BUILDING_WEIGHTS_FIELD = ""
    if INPUT_BUILDING_WEIGHTS_FIELD and (INPUT_BUILDING_WEIGHTS_FIELD not in
                                         fields(INPUT_POINTS)):
        AddError(f"Building weights field <{INPUT_BUILDING_WEIGHTS_FIELD}> is not a valid " +
                 f"attribute in the input points <{INPUT_POINTS}>")
        return

    # setup
    env.overwriteOutput = True

    # copy the input points into an output feature class
    AddMessage("Copying input points to output feature class ...")
    # input_points_layer = Layer(INPUT_POINTS)
    # output_feature_class = f"{join(INPUT_OUTPUT_DIRECTORY, INPUT_OUTPUT_FEATURE_CLASS_NAME)}.shp"
    # CopyFeatures_management(in_features=input_points_layer,
    #                         out_feature_class=output_feature_class)

    output_feature_class = f"{join(INPUT_OUTPUT_DIRECTORY, INPUT_OUTPUT_FEATURE_CLASS_NAME)}.shp"
    CopyFeatures_management(in_features=INPUT_POINTS,
                            out_feature_class=output_feature_class)
    AddMessage("\tDone.")

    # construct network and points
    network, points, edge_to_points = construct_network_and_load_buildings(
        INPUT_POINTS, INPUT_NETWORK, INPUT_BUILDING_WEIGHTS_FIELD)

    # extract origin and destination ids
    origin_ids = flagged_points(INPUT_POINTS, INPUT_ORIGINS_FIELD)
    destination_ids = flagged_points(INPUT_POINTS, INPUT_DESTINATIONS_FIELD)
    if (len(origin_ids) == 0 or
            len(destination_ids) == 0 or
            (len(origin_ids) == 1 and origin_ids == destination_ids)):
        AddWarning("No OD pair found, no computation will be done.")

    # compute redundancy index statistics for each origin point
    AddMessage("Computing redundancy indices ...")
    redundancy_indices = {}
    # memoize: computing index from O to D is same as computing it from D to O
    memo = {}
    for origin_id in origin_ids:
        progress_bar = Progress_Bar(len(destination_ids),
                                    1,
                                    f"Computing index for O={origin_id} ...")
        # statistics variables
        tot_redundancy_index = 0
        tot_squared_redundancy_index = 0
        min_redundancy_index = None
        max_redundancy_index = None
        all_unique_segments = set()
        # track the number of destinations for which a numeric redundancy index is
        #     successfully computed
        n = 0
        for destination_id in destination_ids:
            if origin_id != destination_id:
                memo_key = (min(origin_id, destination_id),
                            max(origin_id,
                                destination_id))
                if memo_key not in memo:
                    memo[memo_key] = find_redundancy_index(network, points,
                                                           edge_to_points, INPUT_COEFF, origin_id, destination_id,
                                                           INPUT_SEARCH_RADIUS, bool(INPUT_BUILDING_WEIGHTS_FIELD))
                if memo[memo_key] is not None:
                    n += 1
                    redundancy_pair, unique_segments_pair = memo[memo_key]
                    min_redundancy_index = (min(min_redundancy_index, redundancy_pair)
                                            if min_redundancy_index is not None else redundancy_pair)
                    max_redundancy_index = (max(max_redundancy_index, redundancy_pair)
                                            if max_redundancy_index is not None else redundancy_pair)
                    tot_redundancy_index += redundancy_pair
                    tot_squared_redundancy_index += redundancy_pair * redundancy_pair
                    all_unique_segments |= unique_segments_pair
            progress_bar.step()
        if n > 0:
            avg_redundancy_index = tot_redundancy_index / n
            avg_squared_redundancy_index = tot_squared_redundancy_index / n
        else:
            avg_redundancy_index = avg_squared_redundancy_index = 0
        # TODO(mikemeko): work on std computation with better accuracy
        std = sqrt(max(avg_squared_redundancy_index - avg_redundancy_index *
                       avg_redundancy_index, 0))
        if min_redundancy_index is None:
            min_redundancy_index = 0
        if max_redundancy_index is None:
            max_redundancy_index = 0
        redundancy_indices[origin_id] = (n, avg_redundancy_index, std,
                                         min_redundancy_index, max_redundancy_index, all_unique_segments)
    AddMessage("\tDone.")

    # write out redundancy statistics to output feature class
    # delete all points that are not origins from the output feature class
    AddMessage("Writing out results ...")
    int_fields = ["InputID", "Reach"]
    double_fields = ["AvgRedund", "StdRedund", "MinRedund", "MaxRedund"]
    for field in int_fields:
        AddField_management(in_table=output_feature_class, field_name=field,
                            field_type="INTEGER")
    for field in double_fields:
        AddField_management(in_table=output_feature_class, field_name=field,
                            field_type="DOUBLE")
    rows = UpdateCursor(output_feature_class,
                        ["OID@"] + int_fields + double_fields)
    for row in rows:
        oid = row[0]
        if Describe(INPUT_POINTS).extension != "shp":
            # original ids start from 1, but shapefile ids start from 0, so add
            #     1 to shapefile id for correct matching
            oid += 1
        if oid in redundancy_indices:
            n, avg, std, m, M, all_unique_segments = redundancy_indices[oid]
            row[1:] = [oid, n, avg, std, m, M]
            rows.updateRow(row)
        else:
            rows.deleteRow()
    # create a layer of the output feature class, for symbology purposes
    output_layer = f"{join(INPUT_OUTPUT_DIRECTORY, INPUT_OUTPUT_FEATURE_CLASS_NAME)}.lyr"
    MakeFeatureLayer_management(in_features=output_feature_class,
                                out_layer=INPUT_OUTPUT_FEATURE_CLASS_NAME)
    SaveToLayerFile_management(INPUT_OUTPUT_FEATURE_CLASS_NAME,
                               output_layer,
                               "ABSOLUTE")
    # add output feature layer to display after applying symbology
    ApplySymbologyFromLayer_management(output_layer, join(path[0],
                                                          "Symbology_Layers",
                                                          "sample_points_symbology.lyr"))
    add_layer_to_display(output_layer)
    # if there is only one origin, symbolize selected edges
    if _common_id(list(memo.keys())) and len(all_unique_segments) > 0:
        n, avg, std, m, M, all_unique_segments = redundancy_indices[origin_ids[0]]
        select_edges_from_network(INPUT_NETWORK, all_unique_segments,
                                  INPUT_OUTPUT_DIRECTORY,
                                  f"{INPUT_OUTPUT_FEATURE_CLASS_NAME}_edges")
    AddMessage("\tDone.")


def _common_id(id_pairs):
    """
    Returns True if all of the tuples in |id_pairs| contain a certain common
        value.
    """
    if len(id_pairs) == 0:
        return False
    elif len(id_pairs) == 1:
        return True
    else:
        first_pair_intersection = set(id_pairs[0]) & set(id_pairs[1])
        if len(first_pair_intersection) != 1:
            return False
        else:
            common = next(iter(first_pair_intersection))
            return all([common in pair for pair in id_pairs[2:]])
