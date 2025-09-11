bl_info = {
    "name": "invert_armature",
    "blender":(3,6,0),
    "category": "Object",
    "description": "Matches mesh post pose to pre-pose mesh",
    "location": "View3D -> Right Sidebar -> Tools Tab",
    "author": "uninvitedCalamity"
}

import bpy
from bpy.props import *
from bpy.types import *
import mathutils
from mathutils import Vector
from bpy.types import ArmatureModifier
import math
import collections

from multiprocessing import Pool
#import interpolate_func as i_func

class vector3():
    x = 0
    y = 0
    z = 0

def pushVertices(originalObject, copyObject, worldMatrix, axis):
    
    def get_distance(pointIndex):
        point = originalObject.data.vertices[pointIndex]
        CopyGlobalMatrix = worldMatrix @ copyObject.data.vertices[point.index].co
        BaseGlobalMatrix = worldMatrix @ mesh_eval[point.index].co
        return (CopyGlobalMatrix - BaseGlobalMatrix).length
    
    dict = {'init':'lol'}    
    PointStore = collections.namedtuple('Point', ['x','y','z'])    
    mesh_eval = get_evaluated(originalObject)

    for point in originalObject.data.vertices:
        OG = PointStore(x=point.co.x,y=point.co.y,z=point.co.z)
        dict[point.index] = {
            'ogPoint': OG,
            'shortestDistance' : get_distance(point.index),
            'closestCo':{'x':point.co.x,'y':point.co.y,'z':point.co.z},
            'direction':1,
            'runCount':1
        }

    i = len(originalObject.data.vertices)
    run1 = True
    while i != 0:        
        mesh_eval = get_evaluated(originalObject)
        i2 = 0
        for point in originalObject.data.vertices:
            if point.index in dict:
                modify = True
                i2 += 1
                point_dict = dict[point.index]
                if run1 == False:
                    distance = get_distance(point.index)
                    if distance < point_dict['shortestDistance']:
                        point_dict['shortestDistance'] = distance
                        point_dict['closestCo']['x'] = point.co.x
                        point_dict["closestCo"]['y'] = point.co.y
                        point_dict["closestCo"]['z'] = point.co.z
                    elif point_dict['direction'] > 0:
                        point_dict['direction'] *= -1
                        point_dict['runCount'] = 1
                    else:
                        modify = False
                        point.co.x = point_dict['closestCo']['x']
                        point.co.y = point_dict['closestCo']['y']
                        point.co.z = point_dict['closestCo']['z']
                        del dict[point.index]

                if modify:
                    originalPos = Vector()
                    originalPos.x = point_dict['ogPoint'].x
                    originalPos.y = point_dict['ogPoint'].y
                    originalPos.z = point_dict['ogPoint'].z
                    targetPos = originalPos + (axis * point_dict['direction'] * point_dict['runCount'])  
                    point_dict['runCount'] += 1   
                    point.co = targetPos        

        run1 = False
        i = i2
    return 0

def interpolate3(objectName, copyName, armatureName, step):
    originalObject = bpy.data.objects[objectName]    
    copyObject = bpy.data.objects[copyName]
    modifier = bpy.data.objects[armatureName]
    worldMatrix = modifier.matrix_world @ originalObject.matrix_local

    axis = Vector()
    axis.x = 1 * step
    axis.y = 0
    axis.z = 0
    pushVertices(originalObject, copyObject, worldMatrix, axis)
    axis.x = 0
    axis.y = 1 * step
    axis.z = 0
    pushVertices(originalObject, copyObject, worldMatrix, axis)
    axis.x = 0
    axis.y = 0
    axis.z = 1 * step
    pushVertices(originalObject, copyObject, worldMatrix, axis)

    return 0


def get_evaluated(originalObject):
    dg = bpy.context.evaluated_depsgraph_get()
    evaled = originalObject.evaluated_get(dg)
    mesh_eval = evaled.to_mesh().vertices
    return mesh_eval  


class invert_armature(bpy.types.Operator):
    """Armature inverter"""
    bl_idname = "object.invert_armature"
    bl_label = "Invert active armature"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):   
        was_original:bool = False
        def Info(string):
            self.report({"INFO"},str(string))

        def breakLog():
            Info("--------------------------------")
            Info("--------------------------------")

        def JoinAsShape(target1, target2):
            tarOb1 = bpy.data.objects.get(target1)
            tarOb2 = bpy.data.objects.get(target2)
            bpy.ops.object.select_all(action='DESELECT')
            tarOb1.select_set(True)
            tarOb2.select_set(True)
            bpy.context.view_layer.objects.active = tarOb1
            bpy.ops.object.join_shapes()

        #Converts point's local position to bone in pose to local point relative to bone at rest
        def calculate(boneDictionary, groupName, weight, modifier):
            Bbone = boneDictionary[groupName]["BaseBone"]
            if(Bbone.use_deform):
                worldMatrix = modifier.object.matrix_world
                BaseGlobalMatrix = worldMatrix @ Bbone.matrix_local
                Pbone = boneDictionary[groupName]["PoseBone"]
                altDif = Pbone.matrix @ BaseGlobalMatrix.inverted()
                returnable = (Pbone.matrix @ altDif @ Pbone.bone.matrix_local.inverted()) * weight
                return (returnable @ point.co)
            return False

        originalObject = context.view_layer.objects.active
        secondaryObject = context.view_layer.objects.active

        selectedObjects = context.selected_objects
        for object in selectedObjects:
            Info(object.name)
            if object == context.active_object:
                Info("Primary = " + object.name)
                originalObject = object
            else:
                Info("Secondary = " + object.name)
                secondaryObject = object


        originalVertices = originalObject.data.vertices
        originalGroups = originalObject.vertex_groups
        groupDictionary = {}
        for group in originalGroups:
            groupDictionary[group.index] = group.name
            
        
        
        if(len(originalVertices) >= 1):
            context.view_layer.objects.active = originalObject
            bpy.ops.object.duplicate_move(
                OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'}, 
                TRANSFORM_OT_translate={
                    "value":(0, 0, 0), 
                    "orient_type":'GLOBAL', 
                    "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), 
                    "orient_matrix_type":'GLOBAL', 
                    "constraint_axis":(False, False, False), 
                    "mirror":True, 
                    "use_proportional_edit":False, 
                    "proportional_edit_falloff":'SMOOTH', 
                    "proportional_size":1, 
                    "use_proportional_connected":False, 
                    "use_proportional_projected":False, 
                    "snap":False, 
                    "snap_target":'CLOSEST', 
                    "snap_point":(0, 0, 0), 
                    "snap_align":False, 
                    "snap_normal":(0, 0, 0), 
                    "gpencil_strokes":False, 
                    "cursor_transform":False, 
                    "texture_space":False, 
                    "remove_on_cancel":False, 
                    "release_confirm":False, 
                    "use_accurate":False}
                )
            modifyObject = context.view_layer.objects.active
            modifyObject.name= originalObject.name + "Modify"
            Info(modifyObject.name)
            if(modifyObject.data.shape_keys != None):
                shapes_length = len(modifyObject.data.shape_keys.key_blocks)
                Info(shapes_length - 1)
                shapes_iterator = shapes_length - 1

                if shapes_length > 0:
                    while shapes_iterator >= 0:
                        modifyObject.data.shape_keys.key_blocks[shapes_iterator].lock_shape = False
                        shapes_iterator -= 1
                    modifyObject.shape_key_clear()

            copyObject = secondaryObject
            if secondaryObject == originalObject:
                was_original = True
                Info("Secondary is Original")
                bpy.ops.object.duplicate_move(
                    OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'}, 
                    TRANSFORM_OT_translate={
                        "value":(0, 0, 0), 
                        "orient_type":'GLOBAL', 
                        "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), 
                        "orient_matrix_type":'GLOBAL', 
                        "constraint_axis":(False, False, False), 
                        "mirror":True, 
                        "use_proportional_edit":False, 
                        "proportional_edit_falloff":'SMOOTH', 
                        "proportional_size":1, 
                        "use_proportional_connected":False, 
                        "use_proportional_projected":False, 
                        "snap":False, 
                        "snap_target":'CLOSEST', 
                        "snap_point":(0, 0, 0), 
                        "snap_align":False, 
                        "snap_normal":(0, 0, 0), 
                        "gpencil_strokes":False, 
                        "cursor_transform":False, 
                        "texture_space":False, 
                        "remove_on_cancel":False, 
                        "release_confirm":False, 
                        "use_accurate":False}
                    )
                copyObject = context.view_layer.objects.active
                copyObject.name = originalObject.name + "Copy"
            copyVertices = copyObject.data.vertices
            context.view_layer.objects.active = modifyObject

            
            for modifier in copyObject.modifiers:
                if modifier.type == 'ARMATURE':
                    modifier.show_viewport = False

            for modifier in modifyObject.modifiers:
                if modifier.type == 'ARMATURE':
                    modifier.show_viewport = True
                    Info(modifier)
                    boneDictionary = {}
                    for bone in modifier.object.data.bones:
                        boneDictionary[bone.name] = {"BaseBone":bone}  

                    for bone in modifier.object.pose.bones:
                        if boneDictionary[bone.name]:
                            boneDictionary[bone.name]["PoseBone"] = bone
                        else:
                            boneDictionary[bone.name] = {"PoseBone":bone}
                    if context.scene.invert_tool.localise:
                        for point in originalVertices:
                            localPointList:vector3 = []
                            groupWeight = 0
                            for group in point.groups:
                                if(groupDictionary[group.group]):
                                    groupName = groupDictionary[group.group]
                                    weight = group.weight
                                    groupWeight += weight
                                    if(boneDictionary.get(groupName)):
                                        if(boneDictionary[groupName]["BaseBone"]):
                                            output = calculate(boneDictionary=boneDictionary,groupName=groupName,weight=weight,modifier=modifier)
                                            if output:
                                                localPointList.append(output)
                            if groupWeight > 0:
                                newPoint:vector3 = localPointList[0]
                                i = 1
                                while i < len(localPointList):
                                    newPoint += localPointList[i]
                                    i +=1
                                point.co = newPoint

                    baseStep = context.scene.invert_tool.step_size
                    progStep = baseStep
                    while progStep > context.scene.invert_tool.min_step_size:
                        interpolate3(modifyObject.name, copyObject.name, modifier.object.name, progStep)
                        progStep /= 2
                    interpolate3(modifyObject.name, copyObject.name, modifier.object.name, context.scene.invert_tool.min_step_size)       
            Info("FINISHED MODIFY STAGE")
            for modifier in originalObject.modifiers:
                if modifier.type == 'ARMATURE':
                    modifier.show_viewport=False
            for modifier in modifyObject.modifiers:
                if modifier.type == 'ARMATURE':
                    modifier.show_viewport=False
            JoinAsShape(originalObject.name,modifyObject.name)
            for modifier in originalObject.modifiers:
                if modifier.type == 'ARMATURE':
                    modifier.show_viewport=True
            
            bpy.ops.object.select_all(action='DESELECT')
            modifyObject.select_set(True)
            if not was_original:
                copyObject.select_set(True)
            context.view_layer.objects.active = modifyObject
            bpy.ops.object.delete(use_global=False, confirm=False)

        Info("FINISHED")
        return{'FINISHED'}
    
    
class properties(bpy.types.PropertyGroup):
    step_size : bpy.props.FloatProperty(name= "Max step size", soft_min= 0.000001, default=1)
    min_step_size : bpy.props.FloatProperty(name= "Min step size", soft_min= 0.000001, default=1)
    localise : bpy.props.BoolProperty(name= "localise")
    
#Based on https://github.com/CGArtPython/blender_plus_python/blob/main/add-ons/simple_custom_panel/simple_custom_panel.py
class VIEW3D_PT_invert_armature_panel(bpy.types.Panel):
    bl_space_type = "VIEW_3D" 
    bl_region_type = "UI"

    bl_category = "Tools"
    bl_label = "Armature Inverter"

    def draw(self, context):
        """define the layout of the panel"""
        layout = self.layout
        scene = context.scene
        invertTool = scene.invert_tool
        layout.prop(invertTool, "step_size")
        layout.prop(invertTool, "min_step_size")
        layout.prop(invertTool, "localise")
        
        row = self.layout.row()
        row.operator("object.invert_armature", text="Invert Armature")


classes = [properties, VIEW3D_PT_invert_armature_panel, invert_armature]

def menu_func(self, context):
    self.layout.operator(invert_armature.bl_idname)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        bpy.types.Scene.invert_tool = bpy.props.PointerProperty(type=properties)
    #bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
        del bpy.types.Scene.invert_tool

if __name__ == "__main__":
    register()