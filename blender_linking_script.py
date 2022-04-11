import bpy
import os

filename = os.path.join(r"C:\Users\mattt\OneDrive - UBC\UBCO Files\Year 5\Masters Project\Software\BlenderScripts", r"main.py")
exec(compile(open(filename).read(), filename, 'exec'))