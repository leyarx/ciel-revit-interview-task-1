"""Create Walls Elevation"""

from pyrevit import revit, DB
from pyrevit import forms
from math import atan2
from System.Collections.Generic import List

import rpw

curview = revit.active_view

def view_clipping(elevation):
    param = rpw.db.Element(elevation).parameters['Far Clipping']
    
    if param.value != 2:
        if param.IsReadOnly:
            set_param_list = List[DB.ElementId]()
            set_param_list.Add(param.Id)
            
            template = rpw.db.Element.from_id(elevation.ViewTemplateId)
            template.SetNonControlledTemplateParameterIds(set_param_list)
            
        param.value = 2

def create_elevation(wall, elevation_type):
    # ensure wall is straight
    line = wall.Location.Curve
    # determine elevation box
    p = line.GetEndPoint(0)
    q = line.GetEndPoint(1)
    v = q - p
    
    bb = wall.get_BoundingBox(None)
    minZ = bb.Min.Z
    maxZ = bb.Max.Z

    w = v.GetLength()

    d = wall.WallType.Width
    
    midpoint = p + 0.5 * v
    walldir = v.Normalize()
    up = DB.XYZ.BasisZ
     
    elevation_marker = DB.ElevationMarker.CreateElevationMarker(revit.doc, doc_elevation_type, midpoint, 1)
    elevation = elevation_marker.CreateElevation(revit.doc, curview.Id, 0)

    # adjusting elevation crop box 
    elevation_bb = elevation.get_BoundingBox(None)
    elevation_bb.Min = DB.XYZ(midpoint.Y-w/2, minZ, 0)
    elevation_bb.Max = DB.XYZ(midpoint.Y+w/2, maxZ, d/2)
    elevation.CropBox = elevation_bb
    
    # setting far clip offset
    elevation_clipping = elevation.get_Parameter(DB.BuiltInParameter.VIEWER_BOUND_OFFSET_FAR)
    elevation_clipping.Set(d/2)
    
    # rotatting the elevation marker
    # https://stackoverflow.com/questions/5188561/signed-angle-between-two-3d-vectors-with-same-origin-within-the-same-plane
    angle = atan2(DB.XYZ.BasisY.CrossProduct(walldir).DotProduct(up), walldir.DotProduct(DB.XYZ.BasisY))  
    
    l = DB.Line.CreateBound(midpoint, midpoint+up)    
    DB.ElementTransformUtils.RotateElement(revit.doc, elevation_marker.Id, l, angle)
    
    # checking elevation view far clipping
    view_clipping(elevation)

def get_walls():
    """retrieve walls from file"""
    return DB.FilteredElementCollector(revit.doc)\
                   .OfCategory(DB.BuiltInCategory.OST_Walls)\
                   .WhereElementIsNotElementType()

def get_elevation_viewfamily():
    return revit.doc.GetDefaultElementTypeId(
        DB.ElementTypeGroup.ViewTypeElevation
        )
 
# check if active view is a Plan View
forms.check_viewtype(curview, DB.ViewType.FloorPlan, exitscript=True) 

doc_elevation_type = get_elevation_viewfamily()

# Iterate over walls
with revit.Transaction("Create Walls Elevation"):
    for wall in get_walls():
        create_elevation(wall, doc_elevation_type)
