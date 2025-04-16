# ------------------------------------------------------------------------------
# Urban Network Analysis Toolbox for ArcGIS10
# Credits: Michael Mekonnen, Andres Sevtsuk
# MIT City Form Research Group
# Usage: Creative Commons Attribution - NonCommercial - ShareAlike 3.0 Unported
#   License
# License: http://creativecommons.org/licenses/by-nc-sa/3.0/
# ------------------------------------------------------------------------------

"""
Script for the computation of the five centrality metrics.
"""

from arcpy import AddWarning
from src.Common.Utils.Progress_Bar import Progress_Bar
from src.Centrality.Constants import BETWEENNESS
from src.Centrality.Constants import CLOSENESS
from src.Centrality.Constants import GRAVITY
from src.Centrality.Constants import LOCATION
from src.Centrality.Constants import NEIGHBORS
from src.Centrality.Constants import NORM_BETWEENNESS
from src.Centrality.Constants import NORM_CLOSENESS
from src.Centrality.Constants import NORM_GRAVITY
from src.Centrality.Constants import NORM_REACH
from src.Centrality.Constants import NORM_STRAIGHTNESS
from src.Centrality.Constants import PROGRESS_NORMALIZATION
from src.Centrality.Constants import REACH
from src.Centrality.Constants import STEP_4
from src.Centrality.Constants import STRAIGHTNESS
from src.Centrality.Constants import WARNING_NO_BETWEENNESS_NORMALIZATION
from src.Centrality.Constants import WEIGHT
from heapq import heapify
from heapq import heappop
from heapq import heappush
from math import exp
from operator import add
from src.Centrality.Utils import dist
from src.Centrality.Utils import eq_tol
from src.Centrality.Utils import Invalid_Parameters_Exception
from src.Centrality.Utils import lt_tol
from src.Centrality.Utils import merge_maps


def compute_centrality(nodes, origins, compute_r, compute_g, compute_b,
                       compute_c, compute_s, radius, network_radius, beta, measures_to_normalize,
                       accumulator_fields):
    """
    Computes reach, gravity, betweenness, closeness, and straightness on a graph.
    |nodes|: graph representation; dictionary mapping node id's to |Node| objects
    |origins|: subset of nodes that will be used as sources of shortest path trees
    |compute_r|: compute reach?
    |compute_g|: compute gravity type index?
    |compute_b|: compute betweenness?
    |compute_c|: compute closeness?
    |compute_s|: compute straightness?
    |radius|: for each node, only consider other nodes that can be reached within
        this distance
    |network_radius|: use network radius or birds-eye radius?
    |beta|: parameter for gravity type index
    |measures_to_normalize|: a list of measures to normalize
    |accumulator_fields|: a list of cost attributes to accumulate
    """

    # Number of nodes in the graph
    N = len(nodes)
    O = len(origins)
    if O > N:
        raise Invalid_Parameters_Exception(
            "size of origins exceeds size of nodes")
    elif O == 0:
        return

    # Preprocessing
    have_accumulations = len(accumulator_fields) > 0
    if have_accumulations:
        def empty_accumulations(): return dict((field, 0.0) for field in
                                               accumulator_fields)
    have_locations = hasattr(list(nodes.values())[0], LOCATION)
    if compute_s and not have_locations:
        # We cannot compute straightness without node locations
        compute_s = False
    if compute_b:
        # Initialize betweenness values
        for id in nodes:
            setattr(nodes[id], BETWEENNESS, 0.0)

    # Initialize the sum of all node weights (normalization)
    sum_weights = 0.0

    # Computation
    progress = Progress_Bar(O, 1, STEP_4)
    for s in origins:
        if s not in nodes:
            continue
        weight_s = getattr(nodes[s], WEIGHT)
        if have_locations:
            location_s = getattr(nodes[s], LOCATION)

        sum_weights += weight_s

        # Initialize reach (weighted and unweighted) computation for |s|
        #     (normalization)
        reach_s = -1
        weighted_reach_s = -weight_s

        # Initialize measures
        if compute_g:
            gravity_s = 0.0
        if compute_b:
            P = {s: []}  # Predecessors
            S = []  # Stack containing nodes in the order they are extended
            # Number of shortest paths from |s| to other nodes
            sigma = {s: 1.0}
            delta = {}  # Dependency of |s| on other nodes
        if compute_c:
            d_sum_s = 0.0
        if compute_s:
            straightness_s = 0.0
        if have_accumulations:
            accumulations_s = {s: empty_accumulations()}

        d = {s: 0.0}  # Shortest distance from |s| to other nodes
        # Queue for Dijkstra
        Q = [(0.0, s)] if network_radius else [(0.0, s, 0.0)]

        # If we use euclidean radius, make a list of all reachable nodes
        if not network_radius:
            reachable_s = set()
            for t in nodes:
                location_t = getattr(nodes[t], LOCATION)
                if dist(location_s, location_t) <= radius:
                    reachable_s.add(t)

        # Dijkstra
        while Q and (True if network_radius else reachable_s):
            # Pop the closest node to |s| from |Q|
            if network_radius:
                d_sv, v = heappop(Q)
            else:
                d_sv, v, dist_sv = heappop(Q)
                if v in reachable_s:
                    reachable_s.remove(v)
            weight_v = getattr(nodes[v], WEIGHT)
            if have_locations:
                location_v = getattr(nodes[v], LOCATION)

            compute = network_radius or dist_sv <= radius
            if compute:
                reach_s += 1
                weighted_reach_s += weight_v
                if d_sv > 0:
                    if compute_g:
                        gravity_s += weight_v * exp(-d_sv * beta)
                    if compute_c:
                        d_sum_s += weight_v * d_sv
                    if compute_s:
                        straightness_s += (weight_v *
                                           dist(location_s, location_v) / d_sv)
                if compute_b:
                    S.append(v)

            for w, d_vw, accumulations_vw in getattr(nodes[v], NEIGHBORS):
                # s ~ ... ~ v ~ w
                d_sw = d_sv + d_vw
                if not network_radius:
                    # Use Euclidean distance
                    location_w = getattr(nodes[w], LOCATION)
                    dist_sw = dist(location_s, location_w)

                if compute_b:
                    b_refresh = False

                add_w_to_Q = False

                if not w in d:  # Found a path from |s| to |w| for the first time
                    if d_sw <= radius or not network_radius:
                        add_w_to_Q = True
                    d[w] = d_sw
                    if compute_b:
                        b_refresh = True

                elif lt_tol(d_sw, d[w]):  # Found a better path from |s| to |w|
                    if d_sw <= radius or not network_radius:
                        if d[w] <= radius or not network_radius:
                            longer_path_node = (d[w], w) if network_radius else (d[w], w,
                                                                                 dist_sw)
                            Q.remove(longer_path_node)
                            heapify(Q)
                        add_w_to_Q = True
                    d[w] = d_sw
                    if compute_b:
                        b_refresh = True

                if add_w_to_Q:
                    new_node = (d_sw, w) if network_radius else (
                        d_sw, w, dist_sw)
                    heappush(Q, new_node)
                    if have_accumulations:
                        accumulations_s[w] = merge_maps(accumulations_s[v],
                                                        dict(accumulations_vw), add)

                if compute_b:
                    if b_refresh:
                        sigma[w] = 0.0
                        P[w] = []
                    if eq_tol(d_sw, d[w]):  # Count all shortest paths from |s| to |w|
                        # Update the number of shortest paths
                        sigma[w] += sigma[v]
                        P[w].append(v)  # |v| is a predecessor of |w|
                        delta[v] = 0.0  # Recognize |v| as a predecessor

        if compute_r:
            setattr(nodes[s], REACH, weighted_reach_s)
        if compute_g:
            setattr(nodes[s], GRAVITY, gravity_s)
        if compute_b:
            while S:  # Revisit nodes in reverse order of distance from |s|
                w = S.pop()
                # Dependency of |s| on |w|
                delta_w = delta[w] if w in delta else 0.0
                for v in P[w]:
                    weight_w = getattr(nodes[w], WEIGHT)
                    delta[v] += sigma[v] / sigma[w] * (weight_w + delta_w)
                if w != s:
                    between_w = getattr(nodes[w], BETWEENNESS)
                    setattr(nodes[w], BETWEENNESS, between_w + delta_w)
        if compute_c:
            setattr(nodes[s], CLOSENESS, (1.0 / d_sum_s if d_sum_s > 0
                                          else 0.0))
        if compute_s:
            setattr(nodes[s], STRAIGHTNESS, straightness_s)

        nodes[s].reach = reach_s
        nodes[s].weighted_reach = weighted_reach_s

        if have_accumulations:
            total_accumulations_s = empty_accumulations()
            for v in accumulations_s:
                total_accumulations_s = merge_maps(total_accumulations_s,
                                                   accumulations_s[v], add)
            for field in accumulator_fields:
                setattr(nodes[s], field, total_accumulations_s[field])

        progress.step()

    # Normalization
    if BETWEENNESS in measures_to_normalize and O < N:
        measures_to_normalize.remove(BETWEENNESS)
        AddWarning(WARNING_NO_BETWEENNESS_NORMALIZATION)
    if measures_to_normalize:
        norm_progress = Progress_Bar(O, 1, PROGRESS_NORMALIZATION)
        for s in origins:
            if s not in nodes:
                continue
            reach_s = nodes[s].reach
            weighted_reach_s = nodes[s].weighted_reach

            # Normalize reach
            if compute_r and REACH in measures_to_normalize:
                weight_s = getattr(nodes[s], WEIGHT)
                try:
                    setattr(nodes[s], NORM_REACH, reach_s /
                            (sum_weights - weight_s))
                except:
                    setattr(nodes[s], NORM_REACH, 0.0)

            # Normalize gravity
            if compute_g and GRAVITY in measures_to_normalize:
                gravity_s = getattr(nodes[s], GRAVITY)
                try:
                    setattr(nodes[s], NORM_GRAVITY,
                            (exp(beta) * gravity_s / weighted_reach_s))
                except:
                    setattr(nodes[s], NORM_GRAVITY, 0.0)

            # Normalize betweenness
            if compute_b and BETWEENNESS in measures_to_normalize:
                betweenness_s = getattr(nodes[s], BETWEENNESS)
                try:
                    setattr(nodes[s], NORM_BETWEENNESS,
                            (betweenness_s / (weighted_reach_s * (reach_s - 1))))
                except:
                    setattr(nodes[s], NORM_BETWEENNESS, 0.0)

            # Normalize closeness
            if compute_c and CLOSENESS in measures_to_normalize:
                closeness_s = getattr(nodes[s], CLOSENESS)
                try:
                    setattr(nodes[s], NORM_CLOSENESS,
                            closeness_s * weighted_reach_s)
                except:
                    setattr(nodes[s], NORM_CLOSENESS, 0.0)

            # Normalize straightness
            if compute_s and STRAIGHTNESS in measures_to_normalize:
                straightness_s = getattr(nodes[s], STRAIGHTNESS)
                try:
                    setattr(nodes[s], NORM_STRAIGHTNESS,
                            (straightness_s / weighted_reach_s))
                except:
                    setattr(nodes[s], NORM_STRAIGHTNESS, 0.0)

            norm_progress.step()
