"""
Script to comput the redundancy index for a given pair of points in a network.
"""

__author__ = 'raul_kalvo, mikemeko'
__date__ = 'May 4, 2013'

from arcpy import AddMessage
from src.Redundancy.Dijkstra import find_shortest_path
from src.Redundancy.Utils import edge_building_weight_sum


def find_redundancy_index(network, points, edge_to_points, coeff, origin_id,
                          destination_id, search_radius, weights_available):
    """
    Returns the redundancy index and unique segments for the given pair of points
        |origin_id| and |destination_id|. |network| is the csNetwork in which the
        points reside. |points| is a mapping from point ids to csPoint objects.
        |edge_to_points| is a mapping from edge ids to lists of the csPoints that
        reside on the respective edge. |coeff| is the redundancy coefficient,
        assumed to be at least 1. |weights_available| should be True if the points
        have weights so that the redundancy index can be computed appropriately.
        Returns None if the shortest path between the two points is larger than
        |search_radius| or there is no network path between the two points.
    """
    # print current OD pair
    AddMessage(f"O={origin_id} D={destination_id}")
    # add origin and destination pseudo nodes to network
    o_point = points[origin_id]
    network.addPseudoNode(o_point.tValue, o_point.Segment, "O", o_point.Point)
    d_point = points[destination_id]
    network.addPseudoNode(d_point.tValue, d_point.Segment, "D", d_point.Point)
    # find the shortest path distance between origin and destination
    search_result = find_shortest_path(network, "O", "D")
    if search_result is None:
        AddMessage("No path found")
        network.clearPsudoNodes()
        return None
    shortest_path, shortest_path_dist = search_result
    if shortest_path_dist > search_radius:
        AddMessage(
            f"Shortest path distance <{shortest_path_dist}> larger than search radius <{search_radius}>")
        network.clearPsudoNodes()
        return None
    # compute unique segments
    unique_segments = _redundant_unique_segments(network,
                                                 shortest_path_dist * coeff)
    # compute redundancy
    # TODO(mikemeko, raul_kalvo): think of better ideas for what to do when
    #     redundancy index denominator is 0
    if weights_available:
        shortest_path_weight_sum = sum(edge_building_weight_sum(network,
                                                                edge_to_points, edge_id) for edge_id in shortest_path)
        unique_segments_weight_sum = sum(edge_building_weight_sum(network,
                                                                  edge_to_points, edge_id) for edge_id in unique_segments)
        redundancy = (unique_segments_weight_sum / shortest_path_weight_sum if
                      shortest_path_weight_sum > 0 else 1)
    else:
        unique_segments_total_dist = sum(network.Edges[edge_id].Length for
                                         edge_id in unique_segments)
        redundancy = (unique_segments_total_dist / shortest_path_dist if
                      shortest_path_dist > 0 else 1)
    # compute unique network segments
    unique_network_segments = set(map(network.originalEdge, unique_segments))
    # result
    AddMessage(f"Redundancy={redundancy:.5f}")
    network.clearPsudoNodes()
    return redundancy, unique_network_segments


def _redundant_unique_segments(network, dist_quota):
    """
    Returns a set of the edge ids in the |network| involved in redundant paths
        from "O" to "D" at the given |dist_quota|.
    TODO(mikemeko): note well that this algorithm allows repeating edges in paths.
        This algorithm does NOT enforce the restriction of having simple paths. It
        would be great to have proofs of (1) our problem being NP-complete (if so)
        and (2) this algorithm finding ALL solutions when non-simple paths are
        allowed.
    """
    # find all shortest paths from "O" at a max distance of the quota
    o_parent, o_distance = find_shortest_path(
        network, "O", max_dist=dist_quota)
    # find all shortest paths from "D" at a max distance of the quota
    d_parent, d_distance = find_shortest_path(
        network, "D", max_dist=dist_quota)
    # find all nodes within reach
    nodes_in_reach = set(o_parent.keys()) | set(d_parent.keys())
    # track successful and unsuccessful segments
    valid_segments = set()
    invalid_segments = set()

    def _validate_path(parent, node):
        """
        Validates all the eges from the root of |parent| to the given |node|.
        """
        while parent[node] is not None:
            node_parent, edge_id = parent[node]
            valid_segments.add(edge_id)
            node = node_parent
    # go through all edges within reach
    for node_id in nodes_in_reach:
        for edge_id in network.Nodes[node_id].Edges:
            if edge_id not in valid_segments and edge_id not in invalid_segments:
                edge = network.Edges[edge_id]
                success = False
                # trial 1: O --- [S-E] --- D
                d_1 = o_distance[edge.Start] + \
                    edge.Length + d_distance[edge.End]
                if d_1 <= dist_quota:
                    _validate_path(o_parent, edge.Start)
                    _validate_path(d_parent, edge.End)
                    success = True
                # trial 2: O --- [E-S] --- D
                d_2 = o_distance[edge.End] + \
                    edge.Length + d_distance[edge.Start]
                if d_2 <= dist_quota:
                    _validate_path(o_parent, edge.End)
                    _validate_path(d_parent, edge.Start)
                    success = True
                if success:
                    valid_segments.add(edge_id)
                else:
                    invalid_segments.add(edge_id)
    return valid_segments
