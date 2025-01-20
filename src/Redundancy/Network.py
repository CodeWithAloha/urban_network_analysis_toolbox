"""
TODO(raul_kalvo, mikemeko): add docstring describing what this script contains.
Classes in this script:
  csNetwork
    addConnection(Origin : (X:flaot,Y:float,Z:float), Destination :
        (X:flaot,Y:float, Z:Float))
  csEdge
  csNode
    ID
    p : Point : (x:float,y:float,z:flaot)
"""

__author__ = 'raul_kalvo, mikemeko'
__date__ = 'May 24, 2013'

from arcpy import AddMessage
from arcpy.da import SearchCursor
from collections import defaultdict
from math import sqrt
from time import time
from .Utils import arcGISPointAsTuple
from .Utils import calculate_network_locations
from .Utils import fields
from .Utils import getEdgePathFromNetwork
from .Utils import network_locations_calculated
from .Utils import polyline_points


class csNetwork(object):
    """
    DESCRIPTION
    PARAMETERS:
        None
    Nodes : [csNodes]
    Edges : [csEdge]
    """
    N = None  # : [csNode]
    E = None  # : [csEdge]
    t = None  # : float < tolerance
    ts = None  # : int
    PE = None  # : [int/string < edge id] Pseudo Edges
    PN = None  # : [int/string < node id] Pseudo Nodes
    HE = None  # : [int/string < edge id] Hidden Edges
    LastUniqueEId = None  # : float

    def __init__(self):
        self.N = {}
        self.E = {}
        self.Tolerance = 0.001
        self.PE = set()
        self.PN = set()
        self.HE = set()
        self.LastUniqueEId = 0

    # Methods
    def addConnections(self, start_point, end_point, all_points, length=None,
                       name=None):
        """
        DESCRIPTION:
            Points are re-maped with network tolerance.
            Example: point.x = 3.413423 > 3.41 (if tolerance = 0.01)
            These points are collected as tuple and used as dictionary key.
            This key is used to find if there is already node in this location
                or not.
            If yes then edge is joined to found node
            If not then new node is created.
        PARAMETERS:
            start_point  : (x:float,y:float,z:flaot)
            end_point    : (x:float,y:float,z:flaot)
            all_points   : an arcpy Array of all the points on this edge
            length       : float = None
            name         : String = None < name is optional
        INTERNALS:
            self.t       : float < tolerance
        RETURN:
            None
        MODIFIES:
            self.N
            self.E
        """

        def pointToIndex(point):
            return (round(point[0], self.ts), round(point[1], self.ts), round(
                point[2], self.ts))

        start_point_index = pointToIndex(start_point)
        end_point_index = pointToIndex(end_point)
        if start_point_index not in self.N:
            n = csNode()
            n.Point = start_point  # it is not too necessary
            self.N[start_point_index] = n
        if end_point_index not in self.N:
            n = csNode()
            n.Point = end_point
            self.N[end_point_index] = n
        e = csEdge()
        if name is None:
            edge_index = len(self.E)
        else:
            edge_index = int(name)
        self.LastUniqueEId = edge_index
        e.Start = start_point_index
        e.End = end_point_index
        e.Points = all_points
        e.Length = length
        self.N[start_point_index].addEdge(edge_index)
        self.N[end_point_index].addEdge(edge_index)
        self.E[edge_index] = e

    def printNodes(self):
        AddMessage("")
        AddMessage("printNodes:")
        AddMessage("")
        AddMessage("%6s %10s %10s %10s \t %s" % ("ID", "X", "Y", "Z", "Edges"))
        for n in self.N:
            AddMessage("%6s %10.2f %10.2f %10.2f \t %s" % (n,
                                                           self.N[n].Point[0],
                                                           self.N[n].Point[1],
                                                           self.N[n].Point[2],
                                                           self.N[n].Edges))
        AddMessage("")

    def printEdges(self):
        AddMessage("")
        AddMessage("printEdges:")
        AddMessage("")
        AddMessage(f"{'ID':>6} {'Length':>10} {'tag':>10} \t{'Nodes'}")
        AddMessage("")
        for e in self.E:
            tag = ""
            if self.E[e].Hidden:
                tag = "hidden"
            AddMessage(
                f"{e:>6} {self.E[e].Length:10.2f} {tag:>10} \t{self.E[e].Nodes}")

    def edgeIDbyNodes(self, node1, node2):
        for e1 in self.N[node1].Edges:
            for e2 in self.N[node2].Edges:
                if e1 == e2:
                    return e1

    def printAdjacencyMatrix(self, print_out=True):
        """
        0    Origin
        1    Destination
        2    Length
        3    EDGE ID
        """
        output_table = []
        for k in self.E:
            e = self.E[k]
            s1 = f"{e.Start} \t {e.End} \t {e.Length} \t {k}"
            s2 = f"{e.End} \t {e.Start} \t {e.Length} \t {k}"
            AddMessage(s1)
            AddMessage(s2)
            output_table.append(s1)
            output_table.append(s2)
        return output_table

    def remap(self):
        """
        DESCRIPTION:
            Since we are using point based node ids these are long and not very
                compact. I just change node indices.
        MODIFIES:
            self.N
            self.E
        """
        clean_nodes = {}
        i = 0
        for k in list(self.N.keys()):
            n = self.N[k]
            clean_nodes[i] = csNode()
            clean_nodes[i].Edges = n.Edges
            clean_nodes[i].Point = n.Point
            for edge_index in n.Edges:
                e = self.E[edge_index]
                if e.Start == k:
                    e.Start = i
                if e.End == k:
                    e.End = i
            i = i + 1
        self.N = clean_nodes

    # Getters and Setters
    def getUniqueEdgeId(self):
        self.LastUniqueEId = self.LastUniqueEId + 1
        return self.LastUniqueEId

    def addPseudoNode(self, t_value, edge_id, name, point):
        """
        DESCRIPTION:
            This function adds new point to network
        PARAMETERS:
            t_value       : float < value between 0 an 1
            SEGMENT_ID    : int
            name          : Name for a new point
        TODO(raul_kalvo):
            Add functionality where two points can be on same segment
            What happens when i add point to beginning?
        """
        # There would be problem, if node is added to beginning or end.
        # Two nodes can not be at same place.
        if t_value == 0:
            t_value = self.Tolerance
        if t_value == 1:
            t_value = 1 - self.Tolerance
        if self.E[edge_id].Hidden:
            # This edge already has pseudo node
            # Collect all valid nodes:
            tN = []
            s = self.E[edge_id].Start
            e = self.E[edge_id].End
            tN.append((0, s))
            tN.append((1, e))
            tN.append((t_value, name))  # New point
            for nid in self.PN:
                n = self.N[nid]
                if n.OriginalEdge == edge_id:
                    if n.TValue == t_value:
                        AddMessage("@addPseudoNode: Two nodes are exactly same"
                                   " place")
                    tN.append((n.TValue, nid))
            tN.sort()
            # Find adjacent node names:
            index = tN.index((t_value, name))
            # Start and End node ids:
            s = tN[index - 1][1]
            e = tN[index + 1][1]
            # Find edge between two nodes:
            edgeId = self.edgeIDbyNodes(s, e)
            self.N[s].removeEdge(edgeId)
            self.N[e].removeEdge(edgeId)
            # Compute new edge points
            points1, points2 = _split_points(self.E[edgeId].Points, point)
            # Current edge is pseudo edge and this can be removed from network.
            del self.E[edgeId]
            self.PE.remove(edgeId)
            # Two new edges are created
            # First edge between start node and new node is created
            edge_index_start_to_new_point = self.getUniqueEdgeId()
            edge = csEdge()
            edge.Start = s
            edge.End = name
            edge.Points = points1
            s_tvalue = self.N[s].TValue if self.N[s].TValue is not None else 0
            edge.Length = self.E[edge_id].Length * (t_value - s_tvalue)
            self.E[edge_index_start_to_new_point] = edge
            self.N[s].addEdge(edge_index_start_to_new_point)
            self.PE.add(edge_index_start_to_new_point)
            # Second edge between new node and end node is created
            edge_index_new_point_to_end = self.getUniqueEdgeId()
            edge = csEdge()
            edge.Start = name
            edge.End = e
            edge.Points = points2
            e_tvalue = self.N[e].TValue if self.N[e].TValue is not None else 1
            edge.Length = self.E[edge_id].Length * (e_tvalue - t_value)
            self.E[edge_index_new_point_to_end] = edge
            self.N[e].addEdge(edge_index_new_point_to_end)
            self.PE.add(edge_index_new_point_to_end)
            # New point is added
            node = csNode()
            node.addEdge(edge_index_start_to_new_point)
            node.addEdge(edge_index_new_point_to_end)
            node.TValue = t_value
            node.e = edge_id
            if point is not None:
                node.Point = point
            self.N[name] = node
            self.PN.add(name)
        else:
            self.E[edge_id].hide()
            self.HE.add(edge_id)
            # Compute new edge points
            points1, points2 = _split_points(self.E[edge_id].Points, point)
            # Segment is removed from end and start node
            s = self.E[edge_id].Start
            e = self.E[edge_id].End
            self.N[s].removeEdge(edge_id)
            self.N[e].removeEdge(edge_id)
            # New edge segment is calculated and added to network
            # There is two new segments
            # Fist new segments:
            edge_index_start_to_new_point = self.getUniqueEdgeId()
            edge = csEdge()
            edge.Start = s
            edge.End = name
            edge.Points = points1
            edge.Length = self.E[edge_id].Length * t_value
            self.E[edge_index_start_to_new_point] = edge
            self.N[s].addEdge(edge_index_start_to_new_point)
            self.PE.add(edge_index_start_to_new_point)
            # Second new segments:
            edge_index_new_point_to_end = self.getUniqueEdgeId()
            edge = csEdge()
            edge.Start = name
            edge.End = e
            edge.Points = points2
            edge.Length = self.E[edge_id].Length * (1 - t_value)
            self.E[edge_index_new_point_to_end] = edge
            self.N[e].addEdge(edge_index_new_point_to_end)
            self.PE.add(edge_index_new_point_to_end)
            # New node is created and added to network
            node = csNode()
            node.addEdge(edge_index_start_to_new_point)
            node.addEdge(edge_index_new_point_to_end)
            node.TValue = t_value
            node.e = edge_id
            if point is not None:
                node.Point = point
            self.N[name] = node
            self.PN.add(name)
            return True

    def clearPsudoNodes(self):
        # take all edges and unlink them from nodes
        for eid in self.PE:
            if eid in self.E:
                for nid in self.E[eid].Nodes:
                    self.N[nid].removeEdge(eid)
                del self.E[eid]
        self.PE.clear()
        # Removing pseudo nodes from network
        for nid in self.PN:
            if nid in self.N:
                del self.N[nid]
        self.PN.clear()
        for eid in self.HE:
            self.E[eid].unhide()
            self.N[self.E[eid].Start].addEdge(eid)
            self.N[self.E[eid].End].addEdge(eid)
        self.HE.clear()

    def isPseudoEdge(self, edge_id):
        return edge_id in self.PE

    def isPseudoNode(self, node_id):
        return node_id in self.PN

    def originalEdgeForPseudoEdge(self, edge_id):
        assert self.isPseudoEdge(edge_id)
        edge = self.E[edge_id]
        if self.isPseudoNode(edge.Start):
            return self.N[edge.Start].OriginalEdge
        elif self.isPseudoNode(edge.End):
            return self.N[edge.End].OriginalEdge
        else:
            raise Exception('Invalid pseudo edge in network')

    def originalEdge(self, edge_id):
        return (self.originalEdgeForPseudoEdge(edge_id) if self.isPseudoEdge(
            edge_id) else edge_id)

    def getEdges(self):
        return self.E

    def getNodes(self):
        return self.N

    def getTolerance(self):
        return self.t

    def setTolerance(self, TOLERANCE):
        self.t = TOLERANCE
        if TOLERANCE > 0:
            self.ts = 0
        else:
            self.ts = max(len(str(TOLERANCE).split(".")[1]) - 1, 0)
        self.ts = len(str(TOLERANCE))

    Tolerance = property(getTolerance, setTolerance)
    Nodes = property(getNodes)
    Edges = property(getEdges)


class csEdge(object):
    s = None  # : int < Node index
    e = None  # : int < None index
    p = None  # : array of points
    l = None  # : float
    n = None  # : String < name of the line
    h = None  # : boolean < if edge is hidden or not

    def __init__(self, start_index=None, end_index=None, points=None,
                 length=None, name=None):
        self.s = start_index
        self.e = end_index
        self.p = points
        self.l = length
        self.n = name
        self.h = False

    def hide(self):
        self.h = True

    def unhide(self):
        self.h = False

    def otherEnd(self, node_id):
        if self.s == node_id:
            return self.e
        else:
            return self.s

    def getStart(self):
        return self.s

    def setStart(self, index):
        self.s = index

    def getEnd(self):
        return self.e

    def setEnd(self, index):
        self.e = index

    def getPoints(self):
        return self.p

    def setPoints(self, points):
        self.p = points

    def getLength(self):
        return self.l

    def setLenght(self, length):
        self.l = length

    def getNodes(self):
        return self.s, self.e

    def getName(self):
        return self.n

    def setName(self, name):
        self.n = name

    def getHidden(self):
        return self.h

    Start = property(getStart, setStart)
    End = property(getEnd, setEnd)
    Points = property(getPoints, setPoints)
    Nodes = property(getNodes)
    Length = property(getLength, setLenght)
    Name = property(getName, setName)
    Hidden = property(getHidden)


class csNode(object):
    p = None  # : ( x:float, y:float, z:float )
    E = None  # : [ edge index : int ]
    t = None  # : float < t value.
    e = None  # : int/string < original segment/edge id. Use it only for pseudo

    #     nodes
    def __init__(self):
        self.E = []  # Edges
        self.p = None
        self.t = None

    # Methods
    def addEdge(self, edge_index):
        self.E.append(edge_index)

    def removeEdge(self, edge_index):
        if edge_index in self.E:
            self.E.remove(edge_index)

    def distanceTo(self, point):
        """
        PARAMETER:
            POINT : (x:float,y:float,z:flaot)
        RETURN:
            Distance : float
        """
        d = sqrt((point[0] - self.p[0]) * (point[0] - self.p[0]) + (point[1] -
                                                                    self.p[1]) * (point[1] - self.p[1]) + (
            point[2] - self.p[2]) * (
            point[2] - self.p[2]))
        return d

    # Properties
    def setPoint(self, point):
        """
        PARAMETERS:
            point :  (x:float,y:float,z:flaot)
        """
        self.p = point

    def getPoint(self):
        return self.p

    def getEdges(self):
        return self.E

    def setEdges(self, edges):
        self.E = edges

    def getTValue(self):
        return self.t

    def setTValue(self, tvalue):
        self.t = tvalue

    def getOriginalEdge(self):
        return self.e

    def setOriginalEdge(self, edge_id):
        self.e = edge_id

    Point = property(getPoint, setPoint)
    Edges = property(getEdges, setEdges)  # Returns list of edge indices
    TValue = property(getTValue, setTValue)
    OriginalEdge = property(getOriginalEdge, setOriginalEdge)


class csPoint(object):
    point = None  # : (x, y, z)
    t = None
    edgeSegment = None
    weight = None

    def __init__(self, T, segment):
        self.t = T
        self.edgeSegment = segment
        self.point = None
        self.weight = None

    def __str__(self):
        # return ("{0:10} {1:25} {2,7}".format (self.edgeSegment, self.t,
        #    self.point[0]))
        # return ("{0:10} {1:25}" % (self.edgeSegment, self.t))
        return (" %10s %7.3f %15.3f %15.3f %15.3f %s" % (self.edgeSegment,
                                                         self.t, self.point[0],
                                                         self.point[1],
                                                         self.point[2],
                                                         self.weight))

    def getPoint(self):
        return self.point

    def setPoint(self, point):
        self.point = point

    def getTValue(self):
        return self.t

    def getSegment(self):
        return self.edgeSegment

    def getWeight(self):
        return self.weight

    def setWeight(self, weight):
        self.weight = weight

    Point = property(getPoint, setPoint)
    tValue = property(getTValue)
    Segment = property(getSegment)
    Weight = property(getWeight, setWeight)


def buildNetwork(network_file_path):
    """
    DESCRIPTION:
        This function builds network from ND file.
        ND file has line
    PARAMETERS:
        network_file_path : String < path to ND file.
    RETURN:
        csNetwork
    """
    DEBUG = False
    tStart = time()
    network = csNetwork()
    feature_class_path = getEdgePathFromNetwork(network_file_path)
    rows = SearchCursor(feature_class_path, ["SHAPE@", "OID@"])
    if DEBUG:
        AddMessage("Delta: " + str(time() - tStart))
    for row in rows:
        feat_shape = row[0]
        pFirst = feat_shape.firstPoint
        pLast = feat_shape.lastPoint
        l = feat_shape.length3D
        points = polyline_points(feat_shape)
        network.addConnections(arcGISPointAsTuple(pFirst), arcGISPointAsTuple(
            pLast), points, l, str(row[1]))
    if DEBUG:
        tEnd = time()
        AddMessage("Delta: " + str(tEnd - tStart))
    network.remap()
    if DEBUG:
        tEnd = time()
        AddMessage("Delta: " + str(tEnd - tStart))
    return network


def loadBuildingsOnNetwork(point_file_path, weights_field):
    """
    DESCRIPTION:
        This function reads point locations on network.
    PARAMETERS:
        point_file_path    : String
        weights_field      : String
        SourceOID : String
        PosAlong  : String
    RETURN:
        Points    : {Point ID, csPoint}
        Edge to points : {Edge ID, [Point ID]}
    """
    cursor_fields = ["OID@", "SourceOID", "PosAlong", "SnapX", "SnapY"]
    points_have_snap_z = "SnapZ" in fields(point_file_path)
    if points_have_snap_z:
        cursor_fields.append("SnapZ")
    if weights_field:
        cursor_fields.append(weights_field)
    rows = SearchCursor(point_file_path, cursor_fields)
    points = {}
    edge_to_points = defaultdict(list)
    for row in rows:
        oid, edge_id, t, x, y = row[:5]
        z = row[5] if points_have_snap_z else 0
        p = csPoint(t, edge_id)
        p.point = (x, y, z)
        if weights_field:
            p.Weight = float(row[5 + points_have_snap_z])
        points[oid] = p
        edge_to_points[edge_id].append(p)
    return points, edge_to_points


def construct_network_and_load_buildings(points_file, network_file,
                                         building_weights_field=None):
    """
    First constructs a network representation using the |network_file|, and then
        load the buildings in the |points_file| onto the network representation.
        |building_weights_field|, if available, is the field for building weights.
        Returns the network representation, the points, and a mapping from edges
        to the points on the respective edges. Prints console messages.
    """
    # build network
    AddMessage("Building network representation ...")
    network = buildNetwork(network_file)
    AddMessage("\tDone.")
    # calculate network locations if not already calculated
    if not network_locations_calculated(points_file):
        AddMessage("Calculating Network Locations ...")
        calculate_network_locations(points_file, network_file)
        AddMessage("\tDone.")
    # load buildings on the network
    AddMessage("Loading buildings on network representation ...")
    points, edge_to_points = loadBuildingsOnNetwork(points_file,
                                                    building_weights_field)
    AddMessage("\tDone.")
    return network, points, edge_to_points


def _split_points(points, new_point):
    """
    Returns two lists of points by putting the |new_point| at an index in the
        given |points| such that the |new_point| is in the "middle". This is only
        an attempt at the task, 100% correct only if we assume that the segments
        that interconnect |points| are straight line segments. There should be at
        least 2 |points|.
    """
    assert len(points) >= 2
    if new_point in points:
        i = points.index(new_point)
        return points[:i + 1], points[i:]

    def cost(i):
        assert 0 <= i < len(points) - 1
        u = tuple(points[i][j] - new_point[j] for j in range(3))
        u_norm = sum(val * val for val in u)
        assert u_norm > 0
        v = tuple(points[i + 1][j] - new_point[j] for j in range(3))
        v_norm = sum(val * val for val in v)
        assert v_norm > 0
        return sum(u[j] * v[j] for j in range(3)) / (u_norm * v_norm)

    i = min(list(range(len(points) - 1)), key=cost)
    return points[:i + 1] + [new_point], [new_point] + points[i + 1:]
