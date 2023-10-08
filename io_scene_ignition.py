"""
This is a Blender plugin that adds an importer for Ignition track meshes.

Texture loading does not currently work (it kinda loads them, but doesn't apply them).

Patches welcome!
"""

from os.path import splitext
from itertools import chain
import bpy
import struct
from bpy_extras.io_utils import unpack_list
from bpy.props import (
    StringProperty,
)

from bpy_extras.io_utils import (
    ImportHelper,
    path_reference_mode,
)
from bpy_extras.image_utils import load_image
from bpy_extras import node_shader_utils


bl_info = {
    "name": "Ignition Track Importer",
    "author": "Luke Benstead",
    "version": (1, 0, 20220430),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "description": "Import a track from the game Ignition",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"
}


class ImportIgnitionTrack(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.ignition_track"
    bl_label = 'Import Ignition Track'
    bl_options = {'PRESET'}
    filename_ext = ".MSH"
    filter_glob = StringProperty(
        default="*.MSH",
        options={'HIDDEN'}
    )
    path_mode = path_reference_mode
    check_extension = True

    def _read_palette(self, filename):
        with open(filename, "rb") as f:
            data = f.read()

        data = data[8:]  # Skip file-length, and unknown

        colours = []
        for i in range(256):
            buffer, data = data[:3], data[3:]
            colour = struct.unpack("<BBB", buffer)
            colours.append(
                (colour[0], colour[1], colour[2], 0 if i == 0 else 255)
            )

        return colours

    def _read_textures(self, filename, palette):
        with open(filename, "rb") as f:
            data = f.read()

        textures = []

        for i in range(16):
            texture = []
            for j in range(256 * 256):
                buffer, data = data[:1], data[1:]
                idx = struct.unpack("<B", buffer)[0]
                colour = palette[idx]
                texture.append(colour)
            textures.append(texture)

        scale = 1.0 / 255.0
        for i, texture in enumerate(textures):
            tex = bpy.data.images.new("Texture{}".format(i), 256, 256, alpha=True)
            tex.pixels = list(chain(*[
                (r * scale, g * scale, b * scale, a * scale) for r,g,b,a in texture
            ]))
            mat = bpy.data.materials.new("Material{}".format(i))
            mat.use_nodes = True

            bsdf = bsdf = mat.node_tree.nodes["Principled BSDF"]
            base_color_texture = mat.node_tree.nodes.new('ShaderNodeTexImage')
            base_color_texture.image = tex
            mat.node_tree.links.new(bsdf.inputs['Base Color'], base_color_texture.outputs['Color'])

    def _read_mesh(self, filename, mesh_count, places):
        vertices = []
        faces = []

        with open(filename, "rb") as f:
            data = f.read()

        msh = bpy.data.meshes.new("TrackMesh")
        obj = bpy.data.objects.new("Track", msh)

        scale = 1.0 / 10.0

        for j in range(mesh_count):
            buffer, data = data[:4], data[4:]
            vertex_count = struct.unpack("<i", buffer)[0]

            buffer, data = data[:4], data[4:]
            poly_count = struct.unpack("<i", buffer)[0]

            voffset = len(vertices)
            for i in range(vertex_count):
                buffer, data = data[:12], data[12:]  # 3 ints
                vertex = struct.unpack("<iii", buffer)

                x = vertex[0] + places[j][2]
                y = vertex[1] - places[j][3]
                z = vertex[2] + places[j][4]

                vertices.append((x * scale, z * scale, -y * scale))

            for i in range(poly_count):
                buffer, data = data[:44], data[44:]
                poly = struct.unpack("<iiiiiiiiiihH", buffer)

                faces.append((poly[1] + voffset, poly[2] + voffset, poly[3] + voffset))

        msh.from_pydata(vertices, [], faces)
        msh.update(calc_edges=True)

        print("Read %d vertices from %d meshes\n" % (len(vertices), mesh_count))
        return obj

    def _read_places(self, filename):
        with open(filename, "rb") as f:
            data = f.read()

        buffer, data = data[:4], data[4:]
        mesh_count = struct.unpack("<i", buffer)[0]

        places = []
        for i in range(mesh_count):
            size = 8 + (3 * 4)
            buffer, data = data[:size], data[size:]
            place = struct.unpack("<iiiii", buffer)
            places.append(place)

        return mesh_count, places

    def execute(self, context):
        mesh_name = self.filepath
        basename = splitext(self.filepath)[0]
        place_name = basename + ".PLC"
        pal_name = basename + ".COL"
        tex_name = basename + ".TEX"

        mesh_count, places = self._read_places(place_name)
        obj = self._read_mesh(mesh_name, mesh_count, places)
        palette = self._read_palette(pal_name)
        self._read_textures(tex_name, palette)

        context.view_layer.active_layer_collection.collection.objects.link(obj)

        return {'FINISHED'}


def menu_func_import_mesh(self, context):
    self.layout.operator(
        ImportIgnitionTrack.bl_idname, text="Ignition Track (.MSH)")


def make_annotations(cls):
    """Converts class fields to annotations if running with Blender 2.8"""
    if bpy.app.version < (2, 80):
        return cls
    bl_props = {k: v for k, v in cls.__dict__.items() if isinstance(v, tuple)}
    if bl_props:
        if '__annotations__' not in cls.__dict__:
            setattr(cls, '__annotations__', {})
        annotations = cls.__dict__['__annotations__']
        for k, v in bl_props.items():
            annotations[k] = v
            delattr(cls, k)
    return cls


def register():
    make_annotations(ImportIgnitionTrack)
    bpy.utils.register_class(ImportIgnitionTrack)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_mesh)


def unregister():
    bpy.utils.unregister_class(ImportIgnitionTrack)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_mesh)
