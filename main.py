import bpy
import os
import glob
from math import radians, atan2, pi, atan, sqrt, cos, sin
import random
import datetime
import numpy as np

x_render_res = 1920
y_render_res = 1080


def get_calibration_matrix_k_from_blender(cam, mode='simple'):
    scene = bpy.context.scene
    scale = scene.render.resolution_percentage / 100
    width = scene.render.resolution_x * scale  # px
    height = scene.render.resolution_y * scale  # px

    if mode == 'simple':
        print('in here!')
        aspect_ratio = width / height
        k = np.zeros((3, 3), dtype=np.float32)
        k[0][0] = width / 2 / np.tan(cam.angle / 2)
        k[1][1] = height / 2. / np.tan(cam.angle / 2) * aspect_ratio
        k[0][2] = width / 2.
        k[1][2] = height / 2.
        k[2][2] = 1.
        k.transpose()

    elif mode == 'complete':

        focal = cam.lens  # mm
        sensor_width = cam.sensor_width  # mm
        sensor_height = cam.sensor_height  # mm
        pixel_aspect_ratio = scene.render.pixel_aspect_x / scene.render.pixel_aspect_y

        if cam.sensor_fit == 'VERTICAL':
            # the sensor height is fixed (sensor fit is horizontal),
            # the sensor width is effectively changed with the pixel aspect ratio
            s_u = width / sensor_width / pixel_aspect_ratio
            s_v = height / sensor_height
        else:  # 'HORIZONTAL' and 'AUTO'
            # the sensor width is fixed (sensor fit is horizontal),
            # the sensor height is effectively changed with the pixel aspect ratio
            pixel_aspect_ratio = scene.render.pixel_aspect_x / scene.render.pixel_aspect_y
            s_u = width / sensor_width
            s_v = height * pixel_aspect_ratio / sensor_height

        # parameters of intrinsic calibration matrix K
        alpha_u = focal * s_u
        alpha_v = focal * s_v
        u_0 = width / 2
        v_0 = height / 2
        skew = 0  # only use rectangular pixels
        print('fx', alpha_u)
        print('fy', alpha_v)
        print('cx', u_0)
        print('cy', v_0)
        k = np.array([
            [alpha_u, skew, u_0],
            [0, alpha_v, v_0],
            [0, 0, 1]
        ], dtype=np.float32)
    else:
        k = None
    return k


def delete_all_objects(first_delete=False, object_preloaded=False):
    if object_preloaded:
        delete_list_objects = ['LIGHT', 'LIGHT_PROBE', 'CAMERA']
    elif first_delete:
        delete_list_objects = ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'HAIR', 'POINTCLOUD', 'VOLUME', 'GPENCIL',
                               'ARMATURE', 'LATTICE', 'EMPTY', 'LIGHT', 'LIGHT_PROBE', 'CAMERA', 'SPEAKER']
    else:
        delete_list_objects = ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'HAIR', 'POINTCLOUD', 'VOLUME', 'GPENCIL',
                               'ARMATURE', 'LATTICE', 'EMPTY', 'LIGHT', 'LIGHT_PROBE', 'SPEAKER']

    # Select all objects in the scene to be deleted:
    for o in bpy.context.scene.objects:
        for i in delete_list_objects:
            if o.type == i:
                o.select_set(True)
                break
            else:
                o.select_set(False)
    # Deletes all selected objects in the scene:

    bpy.ops.object.delete(use_global=True)


def load_object(source):
    bpy.ops.import_scene.obj(filepath=source)
    # Get selected objects (so)
    so = bpy.context.selected_objects  # Keep in mind this returns a list, and needs to be converted into one object

    obj = so[0]  # Getting just one object
    return obj


def object_scaling_and_centering(obj=None, max_size=1):
    obj.select_set(True)
    max_dim = float(max(obj.dimensions))
    scale_factor = 1 / max_dim * max_size
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    bpy.ops.transform.resize(value=(scale_factor, scale_factor, scale_factor), orient_type='GLOBAL',
                             orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                             orient_matrix_type='GLOBAL', mirror=False, use_proportional_edit=False,
                             proportional_edit_falloff='SMOOTH', proportional_size=1,
                             use_proportional_connected=False,
                             use_proportional_projected=False)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')
    obj_height = obj.dimensions[2]
    obj.location = [0, 0, obj_height / 2]


def configure_camera():
    scn = bpy.context.scene
    cam = bpy.data.cameras.new("Camera")
    cam.lens = 50
    cam_obj = bpy.data.objects.new("Camera", cam)
    cam_obj.location = (0, 0, 0)
    cam_obj.rotation_euler = (0, 0, 0)
    scn.collection.objects.link(cam_obj)

    bpy.context.scene.render.resolution_x = x_render_res
    bpy.context.scene.render.resolution_y = y_render_res

    get_calibration_matrix_k_from_blender(cam)
    return cam_obj


def configure_lighting(obj):
    # Setting background default lighting to 0
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[1].default_value = 0

    light_scale = max(obj.dimensions)
    area_light = bpy.data.lights.new(name="Area_light", type='AREA')
    area_light.energy = 50000
    area_light.size = 100 * light_scale
    area_light.cutoff_distance = light_scale * 11

    # Create new object, pass the light data
    light_object = bpy.data.objects.new(name="my-light", object_data=area_light)

    # Link object to collection in context
    bpy.context.collection.objects.link(light_object)
    light_object.location = [0, 0, light_scale * 10]
    light_object.scale = [1, 1, 1]


def orient_camera_towards_target(x, y, z, target):
    bpy.data.objects['Camera'].rotation_euler = [0, 0, radians(-90)]
    bpy.data.objects['Camera'].location = [x, y, z]
    z_target = target.location[2]
    cam_pos = bpy.data.objects['Camera'].location.copy()
    cam_pos *= -1
    z_angle = atan2(cam_pos[1], cam_pos[0]) - radians(90)
    cam_pos *= -1
    x_angle = pi / 2 + atan((z_target - cam_pos[2]) / sqrt(cam_pos[0] ** 2 + cam_pos[1] ** 2))
    bpy.data.objects['Camera'].rotation_euler[0] = x_angle
    bpy.data.objects['Camera'].rotation_euler[2] = z_angle
    """
    For Blender XYZ, simply calculate the angle in the x-y plane CCW about the z axis first, subtract 90 degrees from the
    Z angle, then pitch up the X angle by tan(z/norm(x+y))  
    """


def render_random_views(obj, cam, path, num_views, start_index_at, min_dist, max_dist):
    obj_name = obj.name
    current_time = datetime.datetime.now()
    folder_name = str(obj_name) + '_' + str(num_views) + '_' + str(current_time.year) + '_' + str(
        current_time.month) + '_' + str(current_time.day) + ' ' + str(current_time.hour) + '_' + str(
        current_time.minute) + '_' + str(current_time.second)
    render_folder = path + '/' + folder_name
    os.mkdir(render_folder)

    for view in range(num_views):
        theta = 2 * pi * random.random()
        phi = pi / 2 * random.random()
        r = min_dist + (max_dist - min_dist) * random.random()
        x_pos = r * cos(theta) * sin(phi)
        y_pos = r * sin(theta) * sin(phi)
        z_pos = r * cos(phi)
        orient_camera_towards_target(x_pos, y_pos, z_pos, obj)

        bpy.context.scene.render.image_settings.file_format = 'PNG'
        bpy.context.scene.render.filepath = render_folder + '/' + str(view+start_index_at) + '.png'
        bpy.context.scene.camera = cam
        bpy.ops.render.render(write_still=True)


def main():
    data_path = r"C:\Users\mattt\OneDrive - UBC\UBCO Files\Year 5\Masters Project\Software\BlenderScripts/Input"
    renders_path = r"C:\Users\mattt\OneDrive - UBC\UBCO Files\Year 5\Masters Project\Software\BlenderScripts/Output"
    obj_size = 1
    views_per_object = 1
    starting_image_index = 0
    prototyping = False
    object_preloaded = True

    file = glob.glob(data_path + "/*/*.obj")
    if not prototyping:
        delete_all_objects(first_delete=True, object_preloaded=object_preloaded)
        cam = configure_camera()

        if not object_preloaded:
            obj = load_object(file)
        else:
            obj = bpy.context.collection.objects[0]
        object_scaling_and_centering(obj=obj, max_size=obj_size)

        configure_lighting(obj)

        # Calculating min distance for random camera view so the camera doesn't go inside the object
        sorted_dims = sorted(obj.dimensions, reverse=True)
        min_radius = (sorted_dims[0] ** 2 + sorted_dims[1] ** 2) ** (
                1 / 2)  # Take the two largest dims for min radius
        max_radius = 3 * min_radius  # This will be decided by GSD in the future
        render_random_views(obj, cam, renders_path, views_per_object, starting_image_index, min_radius, max_radius)

        delete_all_objects(object_preloaded=object_preloaded)
    else:
        x, y, z = bpy.data.objects['Camera'].location
        so = bpy.context.selected_objects
        obj = so[0]
        object_scaling_and_centering(obj)
        configure_lighting(obj)
        orient_camera_towards_target(x, y, z, obj)


if __name__ == '__main__':
    main()
