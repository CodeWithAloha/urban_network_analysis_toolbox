"""
Utility methods.
"""

__author__ = 'Michael Mekonnen (mike22meko@gmail.com)'

from arcpy import ApplySymbologyFromLayer_management
from arcpy import CalculateLocations_na
from arcpy import CheckInExtension
from arcpy import CheckOutExtension
from arcpy import Describe
from arcpy import ListFields
from arcpy import MakeFeatureLayer_management
# from arcpy import RefreshCatalog
from arcpy import RefreshLayer
from arcpy import SaveToLayerFile_management
from arcpy import Select_analysis
from arcpy.da import SearchCursor
# from arcpy.mapping import AddLayer
# from arcpy.mapping import Layer
# from arcpy.mapping import ListDataFrames
# from arcpy.mapping import MapDocument
from arcpy import mp
from collections.abc import Hashable
from csv import writer
from os.path import join
from sys import path


class memoized:
    """
    Decorator. Stores function's return value and uses stored value if function is
        called again with the same argument.
    """

    def __init__(self, f):
        self.f = f
        self.cache = {}

    def __call__(self, *args):
        if not isinstance(args, Hashable):
            return self.f(*args)
        if args not in self.cache:
            self.cache[args] = self.f(*args)
        return self.cache[args]


def add_layer_to_display(layer):
    """
    Adds the given |layer| to the list of ArcMap layers so that it is visible.
    Returns True on success and False on failure.
    """
    try:
        # data_frame = ListDataFrames(MapDocument("CURRENT"), "Layers")[0]
        # AddLayer(data_frame, Layer(layer), "AUTO_ARRANGE")

        aprx = mp.ArcGISProject("CURRENT")
        active_map = aprx.activeMap
        active_map.addLayer(layer, "AUTO_ARRANGE")

        return True
    except:
        return False


@memoized
def fields(dataset):
    """
    Returns a set of the fields in the attribute table of the given |dataset|.
    """
    return set([field.name for field in ListFields(dataset)])


def network_features(network):
    """
    Returns the junction and edge feature names of the given |network| dataset if
        they are both present. Raises an Exception otherwise.
    """
    edge_feature = None
    junction_feature = None
    for source in Describe(network).sources:
        if source.sourceType == "EdgeFeature":
            edge_feature = source.name
        elif source.sourceType in ("JunctionFeature", "SystemJunction"):
            junction_feature = source.name
    if edge_feature is None:
        raise Exception(
            "Input Network %s does not have edge feature" % network)
    if junction_feature is None:
        raise Exception(
            "Input Network %s does not have junction feature" % network)
    return junction_feature, edge_feature


def network_locations_calculated(points):
    """
    Returns True if network locations have been calculated for the given |points|
        file, False otherwise.
    """
    points_fields = fields(points)
    network_location_fields = {"SourceID", "SourceOID", "PosAlong", "SideOfEdge",
                               "SnapX", "SnapY", "Distance"}
    return all(field in points_fields for field in network_location_fields)


def calculate_network_locations(points, network):
    """
    Computes the locations of |points| in |network|.
    |points|: a feature class (points or polygons).
    |network|: a network dataset.
    """
    CheckOutExtension("Network")
    CalculateLocations_na(in_point_features=points,
                          in_network_dataset=network,
                          search_tolerance="5000 Meters",
                          search_criteria=f"{network_features(network)} SHAPE; %s SHAPE;",
                          exclude_restricted_elements="INCLUDE")
    CheckInExtension("Network")


@memoized
def network_cost_attributes(network):
    """
    Returns a set of the cost attributes for the given |network|.
    """
    return set([attribute.name for attribute in Describe(network).attributes if
                attribute.usageType == "Cost"])


def edge_building_weight_sum(network, edge_to_points, edge_id):
    """
    Returns the sum of the weights of the buildings on the given edge, assuming
        that buildings have weights.
    """
    assert edge_id in network.Edges
    if network.isPseudoEdge(edge_id):
        edge = network.Edges[edge_id]
        t_min, t_max = (network.Nodes[edge.Start].TValue,
                        network.Nodes[edge.End].TValue)
        if t_min is None:
            t_min = 0
        if t_max is None:
            t_max = 1
        return sum([point.Weight for point in edge_to_points[
            network.originalEdgeForPseudoEdge(edge_id)]
            if t_min < point.tValue < t_max])
    else:
        return sum([point.Weight for point in edge_to_points[edge_id]])


def is_number(s):
    """
    Returns True if the string |s| represents a number, False otherwise.
    """
    try:
        float(s)
        return True
    except:
        return False


def flagged_points(input_points, field):
    """
    Returns a list of the ids of the points in |input_points| such that the
        respective values of the |field| attribute are numbers greater than 0.
        If |field| is invalid, ids of all points are returned.
    """
    if field in fields(input_points):
        return [int(oid) for oid, flag in SearchCursor(input_points,
                                                       ["OID@", field]) if is_number(flag) and float(flag) > 0]
    else:
        return [int(oid) for oid, in SearchCursor(input_points, ["OID@"])]


def polyline_points(polyline):
    """
    Returns an (ordered) list of the points in the given |polyline|.
    """
    points = polyline.getPart(0)
    return [arcGISPointAsTuple(points.getObject(i)) for i in range(points.count)]


def arcGISPointAsTuple(point):
    if point.Z is None:
        return point.X, point.Y, 0.0
    else:
        return point.X, point.Y, point.Z


def write_rows_to_csv(rows, output_dir, output_name):
    """
    Writes the given |rows| of data to a cvs file in the given location.
    """
    file_name = f"{join(output_dir, output_name)}.csv"
    c = writer(open(file_name, "wb"))
    c.writerows(rows)
    # RefreshCatalog(file_name)
    RefreshLayer(file_name)


def getEdgePathFromNetwork(network_file_path):
    desc = Describe(network_file_path)
    assert desc.dataType in ("NetworkDataset", "NetworkDatasetLayer")
    assert len(desc.edgeSources) > 0
    feature_class_path = join(desc.path, desc.edgeSources[0].name)
    if len(desc.extension) > 0:
        # it is file
        feature_class_path = feature_class_path + ".shp"
    return feature_class_path


def select_edges_from_network(network, edges, directory, name):
    """
    Selects the edges in the given |network| path whose edge ids are in the given
        |edges| set, and saves a shapefile of the selected edges at the given
        location. Also saves a symbolized layer of the shapefile. Returns a
        mapping from the ids in the created file to ids in the original edges
        file, as recorded in the |edges| set. Also returns the path to the created
        shape file.
    """
    network_edges = getEdgePathFromNetwork(network)
    id_name = ("FID" if Describe(network_edges).extension == "shp" else
               "OBJECTID")
    query = ' OR '.join([f'"{id_name}" = {edge_id}' for edge_id in edges])
    selected_edges = f"{join(directory, name)}.shp"
    Select_analysis(network_edges, selected_edges, query)
    edges_layer = f"{join(directory, name)}.lyr"
    MakeFeatureLayer_management(in_features=selected_edges, out_layer=name)
    SaveToLayerFile_management(name, edges_layer, "ABSOLUTE")
    ApplySymbologyFromLayer_management(edges_layer,
                                       join(path[0],
                                            "Symbology_Layers",
                                            "sample_edges_symbology.lyr"))
    add_layer_to_display(edges_layer)
    # TODO(mikemeko): this is a bit hacky, relies on the fact that ids appear in
    #     sorted order in tables, and that ids for shape files start from 0
    id_mapping = dict(list(zip(list(range(len(edges))), sorted(edges))))
    return id_mapping, selected_edges
