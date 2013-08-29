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
from Utils import arcGISPointAsTuple
from Utils import calculate_network_locations
from Utils import fields
from Utils import getEdgePathFromNetwork
from Utils import network_locations_calculated
from Utils import polyline_points

class csNetwork(object):
    '''
    DESCRIPTION
    PARAMETERS:
        None
    Nodes : [csNodes]
    Edges : [csEdge]
    '''
    N               = None  # : [csNode]
    E               = None  # : [csEdge]
    t               = None # : float < tolerance
    ts              = None # : int
    PE              = None  # : [int/string < edge id] Pseudo Edges
    PN              = None  # : [int/string < node id] Pseudo Nodes
    HE              = None  # : [int/string < edge id] Hidden Edges
    LastUniqueEId   = None  # : float
    def __init__(self):
        self.N = {}
        self.E = {}
        self.Tolerance = 0.001
        self.PE = set()
        self.PN = set()
        self.HE = set()
        self.LastUniqueEId = 0
    # Methods
    def addConnections(self, START_POINT, END_POINT, ALL_POINTS, LENGTH=None,
        NAME=None):
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
            START_POINT  : (x:float,y:float,z:flaot)
            END_POINT    : (x:float,y:float,z:flaot)
            ALL_POINTS   : an arcpy Array of all the points on this edge
            LENGTH       : float = None
            NAME         : String = None < name is optional
        INTERNALS:
            self.t       : float < tolerance
        RETURN:
            None
        MODIFIES:
            self.N
            self.E
        """

        def pointToIndex(POINT):
            return (round(POINT[0], self.ts), round(POINT[1], self.ts), round(
                POINT[2], self.ts )   )

        StartPointIndex     = pointToIndex( START_POINT )
        EndPointIndex       = pointToIndex( END_POINT )
        if StartPointIndex not in self.N:
            n = csNode()
            n.Point =  START_POINT # it is not too necessary
            self.N[ StartPointIndex ] = n
        if EndPointIndex not in self.N:
            n = csNode()
            n.Point = END_POINT
            self.N[ EndPointIndex ] = n
        e = csEdge()
        if NAME == None:
            EdgeIndex           = len(self.E)
        else:
            EdgeIndex           = int(NAME)
        self.LastUniqueEId  = EdgeIndex
        e.Start     = StartPointIndex
        e.End       = EndPointIndex
        e.Points    = ALL_POINTS
        e.Length    = LENGTH
        self.N[ StartPointIndex ].addEdge( EdgeIndex )
        self.N[ EndPointIndex ].addEdge( EdgeIndex )
        self.E[EdgeIndex] = e
    def printNodes(self):
        AddMessage("")
        AddMessage("printNodes:")
        AddMessage("")
        AddMessage("%6s %10s %10s %10s \t %s" % ("ID", "X", "Y", "Z", "Edges" ))
        for n in self.N :
            AddMessage("%6s %10.2f %10.2f %10.2f \t %s" % (n,
                self.N[n].Point[0], self.N[n].Point[1], self.N[n].Point[2],
                self.N[n].Edges ))
        AddMessage("")
    def printEdges(self):
        AddMessage("")
        AddMessage("printEdges:")
        AddMessage("")
        AddMessage("%6s %10s %10s \t%s" % ('ID', 'Length', 'tag', 'Nodes') )
        AddMessage("")
        for e in self.E:
            tag = ""
            if self.E[e].Hidden:
                tag = "hidden"
            AddMessage("%6s %10.2f %10s \t%s" % (e, self.E[e].Length, tag,
                self.E[e].Nodes) )
    def edgeIDbyNodes(self, NODE1, NODE2):
        for e1 in self.N[NODE1].Edges:
            for e2 in self.N[NODE2].Edges:
                if e1 == e2:
                    return e1
    def printAdjacencyMatrix(self, printOut=True):
        """
        0    Origin
        1    Destination
        2    Length
        3    EDGE ID
        """
        outputTable = []
        for k in self.E:
            e = self.E[k]
            s1 = "%s \t %s \t %s \t %s" % (e.Start, e.End, e.Length, k)
            s2 = "%s \t %s \t %s \t %s" % (e.End, e.Start, e.Length, k)
            AddMessage(s1)
            AddMessage(s2)
            outputTable.append(s1)
            outputTable.append(s2)
        return outputTable
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
        for k in  self.N.keys():
            n = self.N[k]
            clean_nodes[i] = csNode()
            clean_nodes[i].Edges = n.Edges
            clean_nodes[i].Point = n.Point
            for edge_index in n.Edges:
                e = self.E[edge_index]
                if e.Start == k:
                    e.Start =  i
                if e.End == k:
                    e.End = i
            i = i + 1
        self.N = clean_nodes
    # Getters and Setters
    def getUniqueEdgeId(self):
        self.LastUniqueEId =  self.LastUniqueEId + 1
        return self.LastUniqueEId
    def addPseudoNode(self, T_VALUE, EDGE_ID, NAME, POINT):
        """
        DESCRITPION:
            This function adds new point to network
        PARAMETERS:
            T_VALUE       : float < value between 0 an 1
            SEGMENT_ID    : int
            NAME          : Name for a new point
        TODO(raul_kalvo):
            Add functionality where two points can be on same segment
            What happens when i add point to beginning?
        """
        # There would be problem, if node is added to beginning or end.
        # Two nodes can not be at same place.
        if T_VALUE == 0:
            T_VALUE =  self.Tolerance
        if T_VALUE == 1:
            T_VALUE = 1 - self.Tolerance
        if self.E[EDGE_ID].Hidden:
            # This edge already has pseudo node
            # Collect all valid nodes:
            tN = []
            s = self.E[EDGE_ID].Start
            e = self.E[EDGE_ID].End
            tN.append((0, s))
            tN.append((1, e))
            tN.append( (T_VALUE, NAME) ) # New point
            for nid in self.PN:
                n = self.N[nid]
                if n.OriginalEdge == EDGE_ID:
                    if n.TValue == T_VALUE:
                        AddMessage("@addPseudoNode: Two nodes are exactly same"
                            " place")
                    tN.append ( (n.TValue, nid) )
            tN.sort()
            # Find adjacent node names:
            index = tN.index((T_VALUE, NAME))
            # Start and End node ids:
            s     = tN[index-1][1]
            e     = tN[index+1][1]
            # Find edge between two nodes:
            edgeId  = self.edgeIDbyNodes( s, e )
            self.N[s].removeEdge(edgeId)
            self.N[e].removeEdge(edgeId)
            # Compute new edge points
            points1, points2 = _split_points(self.E[edgeId].Points, POINT)
            # Current edge is pseudo edge and this can be removed from network.
            del self.E[edgeId]
            self.PE.remove(edgeId)
            # Two new edges are created
            # First edge between start node and new node is created
            edgeIndexStartToNewPoint = self.getUniqueEdgeId()
            edge        = csEdge()
            edge.Start  = s
            edge.End    = NAME
            edge.Points = points1
            s_tvalue = self.N[s].TValue if self.N[s].TValue is not None else 0
            edge.Length =  self.E[EDGE_ID].Length * (T_VALUE - s_tvalue)
            self.E[ edgeIndexStartToNewPoint ] = edge
            self.N[ s ].addEdge( edgeIndexStartToNewPoint )
            self.PE.add( edgeIndexStartToNewPoint )
            # Second edge between new node and end node is created
            edgeIndexNewPointToEnd = self.getUniqueEdgeId()
            edge        = csEdge()
            edge.Start  = NAME
            edge.End    = e
            edge.Points = points2
            e_tvalue = self.N[e].TValue if self.N[e].TValue is not None else 1
            edge.Length =  self.E[EDGE_ID].Length * (e_tvalue - T_VALUE)
            self.E[ edgeIndexNewPointToEnd ] = edge
            self.N[ e ].addEdge( edgeIndexNewPointToEnd )
            self.PE.add(edgeIndexNewPointToEnd)
            # New point is added
            node = csNode()
            node.addEdge(edgeIndexStartToNewPoint  )
            node.addEdge(edgeIndexNewPointToEnd )
            node.TValue = T_VALUE
            node.OriginalEdge = EDGE_ID
            if POINT != None:
                node.Point = POINT
            self.N[ NAME ] = node
            self.PN.add( NAME )
        else:
            self.E[EDGE_ID].hide()
            self.HE.add(EDGE_ID)
            # Compute new edge points
            points1, points2 = _split_points(self.E[EDGE_ID].Points, POINT)
            # Segment is removed from end and start node
            s = self.E[EDGE_ID].Start
            e = self.E[EDGE_ID].End
            self.N[s].removeEdge(EDGE_ID)
            self.N[e].removeEdge(EDGE_ID)
            # New edge segment is calculated and added to network
            # There is two new segments
            # Fist new segments:
            edgeIndexStartToNewPoint = self.getUniqueEdgeId()
            edge = csEdge()
            edge.Start = s
            edge.End = NAME
            edge.Points = points1
            edge.Length =  self.E[EDGE_ID].Length * T_VALUE
            self.E[ edgeIndexStartToNewPoint ]  = edge
            self.N[ s ].addEdge( edgeIndexStartToNewPoint )
            self.PE.add( edgeIndexStartToNewPoint )
            # Second new segments:
            edgeIndexNewPointToEnd = self.getUniqueEdgeId()
            edge = csEdge()
            edge.Start = NAME
            edge.End = e
            edge.Points = points2
            edge.Length =  self.E[EDGE_ID].Length * (1-T_VALUE)
            self.E[ edgeIndexNewPointToEnd ] = edge
            self.N[ e ].addEdge( edgeIndexNewPointToEnd )
            self.PE.add( edgeIndexNewPointToEnd )
            # New node is created and added to network
            node = csNode()
            node.addEdge(edgeIndexStartToNewPoint  )
            node.addEdge(edgeIndexNewPointToEnd )
            node.TValue = T_VALUE
            node.OriginalEdge = EDGE_ID
            if POINT != None:
                node.Point = POINT
            self.N[ NAME ] = node
            self.PN.add( NAME )
            return True
    def clearPsudoNodes(self):
        # take all edges and unlink them from nodes
        for eid in self.PE:
          if eid in self.E:
            for nid in self.E[eid].Nodes:
                self.N[ nid ].removeEdge( eid )
            del self.E[eid]
        self.PE.clear()
        # Removing pseudo nodes from network
        for nid in self.PN:
            if nid in self.N:
                del self.N[nid]
        self.PN.clear()
        for eid in self.HE:
            self.E[eid].unhide()
            self.N[ self.E[eid].Start ].addEdge( eid )
            self.N[ self.E[eid].End ].addEdge( eid )
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
            self.ts =  0
        else:
            self.ts =  max(  len(str(TOLERANCE).split(".")[1]) - 1, 0)
        self.ts = len(str(TOLERANCE))
    Tolerance = property( getTolerance, setTolerance)
    Nodes           = property( getNodes )
    Edges           = property( getEdges )

class csEdge(object):
    s  = None # : int < Node index
    e  = None # : int < None index
    p = None  # : array of points
    l  = None # : float
    n  = None # : String < name of the line
    h  = None # : boolean < if edge is hidden or not
    def __init__(self, START_INDEX=None, END_INDEX=None, POINTS=None,
        LENGHT=None, NAME=None):
        self.s      = START_INDEX
        self.e      = END_INDEX
        self.p      = POINTS
        self.l      = LENGHT
        self.n      = NAME
        self.h      = False
    def hide(self):
        self.h = True
    def unhide(self):
        self.h = False
    def otherEnd(self, NODE_ID):
        if self.s == NODE_ID:
            return self.e
        else:
            return self.s
    def getStart(self):
        return self.s
    def setStart(self, INDEX):
        self.s =  INDEX
    def getEnd(self):
        return  self.e
    def setEnd(self, INDEX):
        self.e = INDEX
    def getPoints(self):
        return self.p
    def setPoints(self, POINTS):
        self.p = POINTS
    def getLength(self):
        return self.l
    def setLenght(self, LENGHT):
        self.l = LENGHT
    def getNodes(self):
        return (self.s, self.e)
    def getName(self):
        return self.n
    def setName(self, NAME):
        self.n = NAME
    def getHidden(self):
        return self.h
    Start   = property( getStart,  setStart)
    End     = property( getEnd,    setEnd)
    Points  = property( getPoints, setPoints)
    Nodes   = property( getNodes)
    Length  = property( getLength, setLenght)
    Name    = property( getName,   setName)
    Hidden  = property( getHidden )

class csNode(object):
    p = None # : ( x:float, y:float, z:float )
    E = None # : [ edge index : int ]
    t = None # : float < t value.
    e = None # : int/string < original segment/edge id. Use it only for pseudo
             #     nodes
    def __init__(self):
        self.E = [] # Edges
        self.p = None
        self.t = None
    # Methods
    def addEdge(self, EDGEINDEX):
        self.E.append(EDGEINDEX)
    def removeEdge(self, EDGEINDEX):
        if EDGEINDEX in self.E:
            self.E.remove(EDGEINDEX)
    def distanceTo(self, POINT):
        """
        PARAMETER:
            POINT : (x:float,y:float,z:flaot)
        RETURN:
            Distance : float
        """
        d = sqrt((POINT[0] - self.p[0]) * (POINT[0] - self.p[0]) + (POINT[1] -
            self.p[1]) * (POINT[1] - self.p[1]) + (POINT[2] - self.p[2]) * (
            POINT[2] - self.p[2]))
        return d
    # Properties
    def setPoint(self, POINT):
        """
        PARAMETERS:
            POINT :  (x:float,y:float,z:flaot)
        """
        self.p = POINT
    def getPoint(self):
        return self.p
    def getEdges(self):
        return self.E
    def setEdges(self, EDGES):
        self.E = EDGES
    def getTValue(self):
        return self.t
    def setTValue(self, TVALUE):
        self.t =  TVALUE
    def getOriginalEdge(self):
        return self.e
    def setOriginalEdge(self, EDGE_ID):
        self.e = EDGE_ID
    Point        = property(getPoint, setPoint)
    Edges        = property(getEdges, setEdges) # Returns list of edge indices
    TValue       = property(getTValue, setTValue)
    OriginalEdge = property(getOriginalEdge, setOriginalEdge)

class csPoint(object):
    point          = None # : (x, y, z)
    t              = None
    edgeSegment    = None
    weight         = None
    def __init__(self,  T, SEGMENT):
        self.t              = T
        self.edgeSegment    = SEGMENT
        self.point          = None
        self.weight         = None
    def __str__(self):
        #return ("{0:10} {1:25} {2,7}".format (self.edgeSegment, self.t,
        #    self.point[0]))
        #return ("{0:10} {1:25}" % (self.edgeSegment, self.t))
        return(" %10s %7.3f %15.3f %15.3f %15.3f %s" % (self.edgeSegment,
            self.t, self.point[0], self.point[1], self.point[2], self.weight))
    def getPoint(self):
        return self.point
    def setPoint(self, POINT):
        self.point = POINT
    def getTValue(self):
        return self.t
    def getSegment(self):
        return self.edgeSegment
    def getWeight(self):
        return self.weight
    def setWeight(self, weight):
        self.weight = weight
    Point       = property(getPoint, setPoint)
    tValue      = property(getTValue)
    Segment     = property(getSegment)
    Weight      = property(getWeight, setWeight)

def buildNetwork( NETWORK_FILE_PATH ):
    """
    DESCRIPTION:
        This function builds network from ND file.
        ND file has line
    PARAMETERS:
        PATH_ND : String < path to ND file.
    RETURN:
        csNetwork
    """
    DEBUG = False
    tStart = time()
    network = csNetwork()
    featureClassPath    = getEdgePathFromNetwork( NETWORK_FILE_PATH )
    rows                = SearchCursor(featureClassPath,["SHAPE@","OID@" ])
    if DEBUG:
        AddMessage("Delta: " +  str( time() -  tStart ))
    for row in rows:
        featShape   = row[0]
        pFirst      = featShape.firstPoint
        pLast       = featShape.lastPoint
        l           = featShape.length3D
        points = polyline_points(featShape)
        network.addConnections(arcGISPointAsTuple(pFirst), arcGISPointAsTuple(
            pLast), points, l, str(row[1]))
    if DEBUG:
        tEnd = time()
        AddMessage("Delta: " +  str( tEnd -  tStart ))
    network.remap()
    if DEBUG:
        tEnd = time()
        AddMessage("Delta: " +  str( tEnd -  tStart ))
    return network

def loadBuildingsOnNetwork(POINT_FILE_PATH, WEIGHTS_FIELD):
    """
    DESCRIPTION:
        This function reads point locations on network.
    PARAMETERS:
        POINT_FILE_PATH    : String
        WEIGHTS_FIELD      : String
        SourceOID : String
        PosAlong  : String
    RETURN:
        Points    : {Point ID, csPoint}
        Edge to points : {Edge ID, [Point ID]}
    """
    cursor_fields = ["OID@", "SourceOID", "PosAlong", "SnapX", "SnapY"]
    points_have_snap_z = "SnapZ" in fields(POINT_FILE_PATH)
    if points_have_snap_z:
      cursor_fields.append("SnapZ")
    if WEIGHTS_FIELD:
      cursor_fields.append(WEIGHTS_FIELD)
    rows = SearchCursor(POINT_FILE_PATH, cursor_fields)
    points = {}
    edge_to_points = defaultdict(list)
    for row in rows:
        oid, edge_id, t, x, y = row[:5]
        z = row[5] if points_have_snap_z else 0
        p = csPoint(t, edge_id)
        p.Point = (x, y, z)
        if WEIGHTS_FIELD:
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
    u = tuple(points[i][j] - new_point[j] for j in xrange(3))
    u_norm = sum(val * val for val in u)
    assert u_norm > 0
    v = tuple(points[i + 1][j] - new_point[j] for j in xrange(3))
    v_norm = sum(val * val for val in v)
    assert v_norm > 0
    return sum(u[j] * v[j] for j in xrange(3)) / (u_norm * v_norm)
  i = min(range(len(points) - 1), key=cost)
  return points[:i + 1] + [new_point], [new_point] + points[i + 1:]
