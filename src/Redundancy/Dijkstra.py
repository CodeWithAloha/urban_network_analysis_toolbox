"""
Implementation of Dijkstra's algorithm for our Network representation.
"""

__author__ = 'mikemeko'
__date__ = 'August 8, 2013'

from collections import defaultdict
from Common.Data_Structures.PriorityQueue import PriorityQueue
from .Network import csNetwork
from .Utils import memoized


def _path(parent, node):
    """
    Returns a list of the edge ids of the path from the root to the given |node|,
        where |parent| is a dictionary of child->(parent, edge_id) mappings. The
        root node should have parent None.
    """
    assert node in parent
    backward_path = []
    while parent[node] is not None:
        node_parent, edge_id = parent[node]
        backward_path.append(edge_id)
        node = node_parent
    return list(reversed(backward_path))


def find_shortest_path(network, origin, destination=None, nodes_to_avoid=None,
                       max_dist=float('inf')):
    """
    Returns the shortest path(s) from |origin| in |network|. If |destination| is
        given, returns a list of the edge ids for the path as well as the shortest
        path distance, or None if no path could be found. If |destination| is not
        given, returns parent and distance dictionaries from which all shortest
        paths from |origin| can be obtained. Uses Dijkstra's algorithm. If
        |nodes_to_avoid| is given, the path(s) is/are searched so as not to
        include any of the nodes in that set. No path whose distance exceeds
        |max_dist| is found.
    TODO(mikemeko): what if there are multiple shortest paths?
    """
    assert isinstance(network, csNetwork)
    if nodes_to_avoid is None:
        nodes_to_avoid = set()
    if origin not in network.Nodes:
        raise Exception("Unexpected node: %s" % origin)
    if destination is not None and destination not in network.Nodes:
        raise Exception("Unexpected node: %s" % destination)

    @memoized
    def _heuristic(node_id):
        """
        Use buird's eye distance for heuristic.
        """
        return (network.Nodes[node_id].distanceTo(network.Nodes[destination].Point)
                if destination is not None else 0)
    parent = {origin: None}
    distance = defaultdict(lambda: float('inf'))
    distance[origin] = 0
    agenda = PriorityQueue([(0, origin)])
    discovered = set()
    while len(agenda) > 0:
        u = agenda.pop()
        discovered.add(u)
        if u == destination:
            return _path(parent, destination), distance[u]
        else:
            for edge_id in network.Nodes[u].Edges:
                edge = network.Edges[edge_id]
                if not edge.Hidden:
                    v = edge.otherEnd(u)
                    if v not in discovered and v not in nodes_to_avoid:
                        dist_v_through_u = distance[u] + edge.Length
                        if dist_v_through_u < distance[v] and dist_v_through_u <= max_dist:
                            distance[v] = dist_v_through_u
                            parent[v] = (u, edge_id)
                            if agenda.contains(v):
                                agenda.remove(v)
                            agenda.push(v, distance[v] + _heuristic(v))
    return (parent, distance) if destination is None else None
