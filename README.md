# Urban Network Analysis Toolbox for ArcGIS

The City Form Lab has released a state-of-the-art toolbox for urban network analysis. As the first of its kind, the Centrality Tools this ArcGIS toolbox can be used to compute five types of graph analysis measures on spatial networks: Reach; Gravity; Betweenness; Closeness; and Straightness. Redundancy Redundancy Tools additionally calculate the Redundancy Index, Redundant Paths, and the Wayfinding Index.

- **Project Homepage:** http://cityform.mit.edu/projects/urban-network-analysis
- **Source Code:** https://bitbucket.org/cityformlab/-urban-network-analysis-toolbox/src/master/
- **Help Doc:** http://media.voog.com/0000/0036/2451/files/20160120_UNA_help_v1_1.pdf
- **Forum:** https://groups.google.com/g/urban-network-analysis

© City Form Lab
Andres Sevtsuk; Michael Mekonnen, Raul Kalvo
Contact: cityformlab@mit.edu
Singapore University of Technology & Design in collaboration with MIT
20 Dover Drive. Singapore, 138682

---
## EVALUATION
*2025-02-04 - Frank Mancini, GISP*

Aloha all, here as my evaluation notes as promised...

The original python package and ArcGIS Toolbox was developed with ArcMap 10.0-10.2 between 2011-2013 and has been unsupported for over a decade. The deprecation of ArcMap in 2024 and migration to ArcGIS Pro introduced several breaking changes to both the generic python and ArcGIS (arcpy) specific code. 

I have no experience with this type of spatial analysis and am not able to evaluate the workflow. I am concerned that even if we can coerce the tools to produce results in ArcGIS Pro, the logic might be outdated and generate misleading or inaccurate results. Will need subject matter expert input to upgrade this toolbox successfully.

I recommend researching modern network analysis tools before sinking any significant effort into this task.

A recent [forum post](https://groups.google.com/g/urban-network-analysis/c/MSAsBV9uEbA) by a moderator (and presumably a project lead) confirms the UNA toolbox is no longer maintained and recommends these other tools instead:
- **Rhino 3d UNA toolbox**: https://unatoolbox.notion.site
- **Python Madina UNA toolbox**: https://madinadocs.readthedocs.io/en/latest/

```
Andres
Dec 7, 2024, 9:43:26 PM
to Urban Network Analysis

we do not consistently maintain the UNA GIS toolbox anymore. I suggest
either running the analysis in Rhino 3d UNA toolbox with a graphic user
interface (https://unatoolbox.notion.site), or in the Python Madina UNA
toolbox  https://madinadocs.readthedocs.io/en/latest/
best, Andres
```

It also looks possible to perform some of these analyses out of the box now in **ArcGIS Pro**:

- [Link Analysis in ArcGIS Pro](https://pro.arcgis.com/en/pro-app/latest/help/analysis/link-charts/link-analysis-with-arcgis-pro.htm)
- [Link Chart Analysis](https://pro.arcgis.com/en/pro-app/latest/help/analysis/link-charts/analysis.htm)
- [Compute centrality scores to measure the importance of entities](https://pro.arcgis.com/en/pro-app/latest/help/data/knowledge/compute-centrality-scores-to-measure-the-importance-of-link-chart-entities.htm)

The following are the primary types of analysis that can be performed in the context of a link chart in ArcGIS Pro:
- **Centrality**—Represents basic statistics in a network. There are three centrality metrics implemented for a link chart. These metrics are **_betweenness, closeness, and degree_**.
- **Cluster**—Partitions the network into like areas based on differing factors determined by the specific algorithm. The four types of clusters implemented for a link chart are Biconnected Component, Edge Betweenness, Hierarchical, and K-Means.
- **Neighborhood**—Identifies direct connections from a given node out to a certain radius.
- **Path**—Finds how entities are connected and returns the specific set of entities that will connect given nodes.

---
## UPGRADE EFFORTS
**GITHUB REPO: https://github.com/CodeWithAloha/urban_network_analysis_toolbox**

##### 2024-10-12 - Suchandra Thapa - suchandra@gmail.com
- Auto-Converted python 2 to 3
- Converted old-style % string formatting to f-strings

##### 2025-02-04 - Frank Mancini, GISP - frankmancini3@gmail.com
- Upgraded ArcGIS Toolbox from .tbx to .atbx
- Resolved assorted python and arcpy errors
- Auto-Formatted to PEP 8

*NOTE: Updated and tested with ArcGIS Pro 3.4.0 (Python 3.11.10, arcpy 3.4) and ArcGIS Advanced User License.*

---
## CURRENT STATE
**MINIMUM REQUIREMENTS:**
- ArcGIS Pro User License (Level = TBD)
- ArcGIS Network Analyst Extension

**STATUS:**
- 6x included Centrality Computation unit tests pass `.\urban_network_analysis_toolbox\src\Centrality\Centrality_Computation_Unittest.py`
- Centrality and Redundancy Tools execute from within ArcGIS Pro session, but do not succeed. 
*NOTE: Unclear if issues with the provided sample data, underlying code, or user error in choosing analysis parameters. Need expert guidance to proceed.*

- Analysis uses deprecated ArcGIS Network Analyst tools:
  - [Make OD Cost Matrix Layer (Network Analyst)](https://pro.arcgis.com/en/pro-app/latest/tool-reference/network-analyst/make-od-cost-matrix-layer.htm)
from arcpy import AddLocations
from arcpy import CalculateLocations_na
from arcpy import Solve_na

---
## TO DO
- Need expert guidance on valid test input parameters and expected results.
- Replace [Make OD Cost Matrix Layer (Network Analyst)](https://pro.arcgis.com/en/pro-app/latest/tool-reference/network-analyst/make-od-cost-matrix-layer.htm) with [Make OD Cost Matrix Analysis Layer (Network Analyst)](https://pro.arcgis.com/en/pro-app/latest/tool-reference/network-analyst/make-od-cost-matrix-analysis-layer.htm)
- [Migrating from arcpy.mapping to ArcGIS Pro](https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/migratingfrom10xarcpymapping.htm)