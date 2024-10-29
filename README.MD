# Armature inverter
## What it does
Armature inverter adjusts a mesh so that it's post pose shape matches it's base shape.

## How to use
The armature inverter can be found in the Tools tab on the right sidebar.

A reference object can be used, it must have the same vertex count as the target object.

The target object must have an Armature modifier.

### Operation
- Pose the armature in the desired target pose.
- Select reference object (if using a reference object)
- Select target object
- Set maximum step size
- Set minimum step size
- Enable/Disable localisation
- Click invert armature

## How it works

- If not provided with a reference object the armature inverter will create a copy and use that, this reference is not deleted as the inversion process is destructive.
- The inverter gets the local position of reference vertices relative to the armature's pose bones, and converts this vector to a global position using the armature's base bones. (this stage is optional)
- The inverter then runs a loop until step size is < minimum step size:
    - evaluate the mesh. 
    - for each vertex, until distance starts increasing:  
        - Check distance to desired position on evaluation.
        - adjust vertex position on the x,y,z axis using the step size.
    - Reduce step size.

