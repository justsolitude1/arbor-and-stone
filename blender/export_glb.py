# Export ModernSanctuary.blend -> viewer/house.glb (web-light: decimated trees, joined per collection+material)
# Run: blender -b ModernSanctuary.blend --python export_glb.py
import bpy, os
from collections import defaultdict

OUT = os.path.join(os.path.dirname(bpy.data.filepath), "viewer")
os.makedirs(OUT, exist_ok=True)

for o in list(bpy.data.objects):
    if o.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(o)

# lighter foliage
for o in bpy.data.collections["Trees"].objects:
    if any(m.type == 'DISPLACE' for m in o.modifiers):
        d = o.modifiers.new("Dec", 'DECIMATE'); d.ratio = 0.22

# apply modifiers
dg = bpy.context.evaluated_depsgraph_get()
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.modifiers:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        o.modifiers.clear(); o.data = me

# flat materials (viewer re-dresses by name)
for m in bpy.data.materials:
    if not m.use_nodes: continue
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type not in ('BSDF_PRINCIPLED', 'OUTPUT_MATERIAL'):
            nt.nodes.remove(n)
    if "Principled BSDF" not in nt.nodes:
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(b.outputs[0], nt.nodes["Material Output"].inputs[0])

# join per collection + material
for c in bpy.data.collections:
    groups = defaultdict(list)
    for o in c.objects:
        if o.type == 'MESH' and o.data.materials:
            groups[o.data.materials[0].name].append(o)
    for mname, objs in groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1:
            bpy.ops.object.join()
        objs[0].name = f"{c.name}__{mname}"

bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "house.glb"), export_format='GLB',
                          export_apply=True, export_yup=True, export_texcoords=False,
                          export_normals=True, export_materials='EXPORT')
print("EXPORTED", os.path.getsize(os.path.join(OUT, "house.glb")))
