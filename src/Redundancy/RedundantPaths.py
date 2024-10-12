"""
Script to find all redundant paths between a given pair of points in a network.
"""

__author__ = 'mikemeko'
__date__ = 'August 12, 2013'

from arcpy import AddMessage
from collections import defaultdict
from .Dijkstra import find_shortest_path


def find_all_paths(network, points, coeff, origin_id, destination_id,
                   search_radius, compute_wayfinding):
  """
  Returns all paths from |origin_id| to |destination_id|. Paths are returned as
      lists of 3D point tuples. |network| is the network in which the paths are
      to be computed. |points| is a mapping from point ids to csPoint objects.
      |coeff| is the redundancy coefficient, assumed to be at least 1. Also
      returns a mapping from the network segments invloved in all of the paths
      to the number of times each segment used, the number of paths, the
      redundancy index, and the wayfinding index (if requested as per
      |compute_wayfinding|). Returns None if the shortest path between the two
      points is greater than |search_radius| or there is no network path between
      the two points.
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
    AddMessage(f"Shortest path distance <{shortest_path_dist}> larger than search radius <{search_radius}>")
    network.clearPsudoNodes()
    return None
  available_dist = shortest_path_dist * coeff
  paths = get_paths(csPath(["O"], [], {"O"}, 1.0), available_dist, "D",
                    network.Nodes["D"], network)
  # find the points along the path
  path_points = [all_points_on_path(network, path_obj.Edges) for path_obj in
                 paths]
  # compute wayfinding index: the probability that a person starting at O and
  #     moving about randomly at each junction (such that he never repeats a
  #     junction) reaches D without exceeding the quota
  if compute_wayfinding:
    wayfinding = sum(path_obj.Prob for path_obj in paths)
  # compute redundancy index and unique network segment counts
  unique_segments = set()
  unique_network_segment_counts = defaultdict(int)
  for path_obj in paths:
    for edge_id in path_obj.Edges:
      unique_segments.add(edge_id)
      unique_network_segment_counts[network.originalEdge(edge_id)] += 1
  unique_segments_total_dist = sum(network.Edges[edge_id].Length for edge_id in
                                   unique_segments)
  # TODO(mikemeko, raul_kalvo): think of better ideas for what to do when
  #     redundancy index denominator is 0
  redundancy = (unique_segments_total_dist / shortest_path_dist if
                shortest_path_dist > 0 else 1)
  # result
  results = [f"Number of paths={len(paths)}", f"Redundancy={redundancy:.5f}"]
  if compute_wayfinding:
    results.append(f"Wayfinding={wayfinding:.5f}")
  AddMessage(", ".join(results))
  network.clearPsudoNodes()
  output = [path_points, unique_network_segment_counts, len(paths), redundancy]
  if compute_wayfinding:
    output.append(wayfinding)
  return output


def get_paths(path, available_length, destination_id, destination_node, network,
              shortest_path_memo=None):
  """
  Returns all paths (represented as csPath objects) that can be obtained by
      extending the current |path| and that reach the |destination_node| (whose
      id is |destination_id|), whithout exceeding the |available_length|. All
      paths are found in the given |network|. |shortest_path_memo| is used to
      memoize the shortest path distances in the network.
  """
  if shortest_path_memo is None:
    shortest_path_memo = {}
  output = []
  possible_ways = []
  # count the number of edges that we can take without repeating visited nodes
  #     and without exceeding the quota (at the moment of taking the edge)
  num_valid_edges = 0
  for edge_id in network.Nodes[path.End].Edges:
    edge = network.Edges[edge_id]
    if not edge.Hidden:
      otherEnd = edge.otherEnd(path.End)
      if otherEnd in path.VisitedNodes:
        continue
      num_valid_edges += 1
      new_available_length = available_length - edge.Length
      if new_available_length < 0:
        continue
      # some heuristics to reduce search space
      birds_eye_critical_dist = destination_node.distanceTo(
        network.Nodes[otherEnd].Point)
      if new_available_length < birds_eye_critical_dist:
        continue
      shortest_path_key = (path.End, otherEnd, destination_id)
      if shortest_path_key not in shortest_path_memo:
        sp = find_shortest_path(network, otherEnd, destination_id,
                                {path.End, otherEnd})
        shortest_path_memo[shortest_path_key] = (float('inf') if sp is None
                                                 else sp[1])
      if new_available_length < shortest_path_memo[shortest_path_key]:
        continue
      possible_ways.append((otherEnd, edge_id, new_available_length))
  for new_end, edge_id, new_available_length in possible_ways:
    newPath = csPath(path.Path + [new_end], path.Edges + [edge_id],
                     path.VisitedNodes | {new_end}, path.Prob / num_valid_edges)
    if new_end == destination_id:
      output.append(newPath)
    else:
      output.extend(get_paths(newPath, new_available_length, destination_id,
                              destination_node, network, shortest_path_memo))
  return output


class csPath(object):
  def __init__(self, PATH, EDGES, VISITED_NODES, PROB):
    # path: [NODE ID : int] List of nodes. There is no duplicates only
    #     unique nodes.
    # edges: [EDGE ID: int] List of edges.
    # visitedNodes: set([Node ID]). For quick look-up.
    # prob: probability of taking this simple path
    self.path = PATH
    self.edges = EDGES
    self.visitedNodes = VISITED_NODES
    self.prob = PROB

  def getPath(self):
    return self.path

  def getEdges(self):
    return self.edges

  def getVisitedNodes(self):
    return self.visitedNodes

  def getEnd(self):
    return self.path[-1]

  def getProb(self):
    return self.prob

  def setProb(self, PROB):
    self.prob = PROB

  Edges = property(getEdges)
  Path = property(getPath)
  VisitedNodes = property(getVisitedNodes)
  End = property(getEnd)
  Prob = property(getProb, setProb)


def all_points_on_path(network, path):
  """
  Returns the list of points on the |path|, which is a list of connected edges
      in the |network|.
  """
  if not path:
    return []
  points = network.Edges[path[0]].Points[:]
  for edge_id in path[1:]:
    edge_points = network.Edges[edge_id].Points[:]
    if points[0] == edge_points[0] or points[0] == edge_points[-1]:
      points.reverse()
    if points[-1] == edge_points[-1]:
      edge_points.reverse()
    assert points[-1] == edge_points[0]
    points.extend(edge_points[1:])
  return points
