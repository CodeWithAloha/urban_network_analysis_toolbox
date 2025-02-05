"""
Main file for redundant paths tool.
"""

__author__ = 'mikemeko'
__date__ = 'August 12, 2013'

from arcpy import AddError
from arcpy import AddField_management
from arcpy import AddMessage
from arcpy import AddWarning
from arcpy import ApplySymbologyFromLayer_management
from arcpy import Array
from arcpy import CopyFeatures_management
from arcpy import env
from arcpy import Exists
from arcpy import MakeFeatureLayer_management
from arcpy import Point
from arcpy import Polyline
from arcpy import SaveToLayerFile_management
from arcpy.da import UpdateCursor
from collections import defaultdict
from src.Common.Utils.Progress_Bar import Progress_Bar
from Network import construct_network_and_load_buildings
from os.path import join
from RedundantPaths import find_all_paths
from sys import argv
from sys import path
from Utils import add_layer_to_display
from Utils import flagged_points
from Utils import is_number
from Utils import network_cost_attributes
from Utils import select_edges_from_network
from Utils import write_rows_to_csv


def main():
    # tool inputs
    INPUT_NETWORK = argv[1]
    INPUT_POINTS = argv[2]
    INPUT_ORIGINS_FIELD = argv[3]
    INPUT_DESTINATIONS_FIELD = argv[4]
    INPUT_COEFF = float(argv[5])
    INPUT_SEARCH_RADIUS = float(argv[6]) if is_number(
        argv[6]) else float('inf')
    INPUT_OUTPUT_DIRECTORY = argv[7]
    INPUT_OUTPUT_FEATURE_CLASS_NAME = argv[8]
    INPUT_COMPUTE_WAYFINDING = argv[9] == "true"
    INPUT_VISUALIZATION = argv[10]

    # check that network has "Length" attribute
    if "Length" not in network_cost_attributes(INPUT_NETWORK):
        AddError("Network <%s> does not have Length attribute" % INPUT_NETWORK)
        return

    # check that coeff is at least 1
    if INPUT_COEFF < 1:
        AddError("Redundancy coefficient <%s> must be at least 1" %
                 INPUT_COEFF)
        return

    # extract origin and destination ids
    origin_ids = flagged_points(INPUT_POINTS, INPUT_ORIGINS_FIELD)
    if len(origin_ids) != 1:
        AddError("Number of origins <%s> must be 1" % len(origin_ids))
        return
    origin_id = origin_ids[0]
    destination_ids = flagged_points(INPUT_POINTS, INPUT_DESTINATIONS_FIELD)
    if len(destination_ids) == 0 or origin_ids == destination_ids:
        AddWarning("No OD pair found, no computation will be done")
        return

    # check that the output file does not already exist
    output_feature_class = "%s.shp" % join(INPUT_OUTPUT_DIRECTORY,
                                           INPUT_OUTPUT_FEATURE_CLASS_NAME)
    if Exists(output_feature_class):
        AddError("Output feature class <%s> already exists" %
                 output_feature_class)
        return

    # obtain visualization method
    visualize_segments = visualize_polylines = False
    if INPUT_VISUALIZATION == "Unique Segments":
        visualize_segments = True
    elif INPUT_VISUALIZATION == "Path Polylines":
        visualize_polylines = True
    elif INPUT_VISUALIZATION != "None":
        AddError("Visualization method <%s> must be one of 'Unique Segments', "
                 "'Path Polylines', or 'None'" % INPUT_VISUALIZATION)
        return

    # setup
    env.overwriteOutput = True

    # construct network and points
    network, points, edge_to_points = construct_network_and_load_buildings(
        INPUT_POINTS, INPUT_NETWORK)

    # find redundant paths for each origin-destination
    AddMessage("Computing redundant paths ...")
    progress_bar = Progress_Bar(len(destination_ids), 1, "Finding paths ...")
    # build output table one row at a time, starting from header row
    answers = [["OrigID", "DestID", "NumPaths", "Redundancy"]]
    if INPUT_COMPUTE_WAYFINDING:
        answers[0].append("Wayfinding")
    # visualization state
    if visualize_polylines:
        polylines = []
        polyline_data = []
    elif visualize_segments:
        all_unique_segment_counts = defaultdict(int)
    for destination_id in destination_ids:
        if origin_id != destination_id:
            all_paths = find_all_paths(network, points, INPUT_COEFF, origin_id,
                                       destination_id, INPUT_SEARCH_RADIUS, INPUT_COMPUTE_WAYFINDING)
            if all_paths is not None:
                if INPUT_COMPUTE_WAYFINDING:
                    (all_path_points, unique_segment_counts, num_paths,
                        redundancy, waypoint) = all_paths
                    answers.append([origin_id, destination_id, num_paths, redundancy,
                                    waypoint])
                else:
                    (all_path_points, unique_segment_counts, num_paths,
                        redundancy) = all_paths
                    answers.append(
                        [origin_id, destination_id, num_paths, redundancy])
                if visualize_polylines:
                    for i, path_points in enumerate(all_path_points):
                        polylines.append(Polyline(Array([Point(*coords) for coords in
                                                         path_points])))
                        polyline_data.append((origin_id, destination_id, i))
                elif visualize_segments:
                    for edge_id in unique_segment_counts:
                        all_unique_segment_counts[edge_id] += unique_segment_counts[
                            edge_id]
        progress_bar.step()
    AddMessage("\tDone.")

    # write out results
    if len(answers) > 1:
        AddMessage("Writing out results ...")
        # write out to a table
        write_rows_to_csv(answers, INPUT_OUTPUT_DIRECTORY,
                          INPUT_OUTPUT_FEATURE_CLASS_NAME)
        # visualize
        if visualize_polylines:
            CopyFeatures_management(polylines, output_feature_class)
            data_fields = ["OrigID", "DestID", "PathID"]
            for field in data_fields:
                AddField_management(in_table=output_feature_class, field_name=field,
                                    field_type="INTEGER")
            rows = UpdateCursor(output_feature_class, data_fields)
            for j, row in enumerate(rows):
                row[0], row[1], row[2] = polyline_data[j]
                rows.updateRow(row)
            # create a layer of the polylines shapefile and symbolize
            polylines_layer_name = "%s_layer" % INPUT_OUTPUT_FEATURE_CLASS_NAME
            polylines_layer = "%s.lyr" % join(INPUT_OUTPUT_DIRECTORY,
                                              INPUT_OUTPUT_FEATURE_CLASS_NAME)
            MakeFeatureLayer_management(
                output_feature_class, polylines_layer_name)
            SaveToLayerFile_management(polylines_layer_name, polylines_layer,
                                       "ABSOLUTE")
            ApplySymbologyFromLayer_management(polylines_layer, join(path[0],
                                                                     "Symbology_Layers",
                                                                     "sample_polylines_symbology.lyr"))
            add_layer_to_display(polylines_layer)
        elif visualize_segments:
            id_mapping, edges_file = select_edges_from_network(INPUT_NETWORK,
                                                               list(all_unique_segment_counts.keys(
                                                               )), INPUT_OUTPUT_DIRECTORY,
                                                               "%s_edges" % INPUT_OUTPUT_FEATURE_CLASS_NAME)
            AddField_management(in_table=edges_file, field_name="PathCount",
                                field_type="INTEGER")
            rows = UpdateCursor(edges_file, ["OID@", "PathCount"])
            for row in rows:
                row[1] = all_unique_segment_counts[id_mapping[row[0]]]
                rows.updateRow(row)
        AddMessage("\tDone.")
    else:
        AddMessage("No results to write out.")
