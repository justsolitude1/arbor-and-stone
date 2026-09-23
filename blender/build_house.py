# Modern Sanctuary - procedural Blender build (Blender 5.x)
# Run:  blender -b --python build_house.py -- [render]
# Units: meters. +X east, +Y north. Front of house faces south (-Y).
import bpy, bmesh, math, random, os, sys
from mathutils import Vector

OUT = os.path.dirname(os.path.abspath(__file__))
random.seed(7)

# ---------------------------------------------------------------- reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

def coll(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

C_SHELL = coll("Shell"); C_GLASS = coll("Glazing"); C_ROOF = coll("Roofs")
C_INT = coll("Interior"); C_SITE = coll("Site"); C_TREES = coll("Trees"); C_LIGHT = coll("Lighting")

# ---------------------------------------------------------------- materials
def mat(name, color, rough=0.5, metal=0.0, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for k, v in kw.items():
        b.inputs[k].default_value = v
    return m

def world_xy_z(nt):
    """returns (u, z) sockets: u = x+y in world space (works for walls on both axes)."""
    n = nt.nodes; l = nt.links
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sep.inputs[0])
    add = n.new("ShaderNodeMath"); add.operation = 'ADD'
    l.new(sep.outputs[0], add.inputs[0]); l.new(sep.outputs[1], add.inputs[1])
    return tc, sep, add

def wood_mat(name, c1, c2, board=0.14):
    m = mat(name, c1, 0.55)
    nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n["Principled BSDF"]
    tc, sep, add = world_xy_z(nt)
    # vertical boards: color per board via snapping u
    div = n.new("ShaderNodeMath"); div.operation = 'DIVIDE'; div.inputs[1].default_value = board
    l.new(add.outputs[0], div.inputs[0])
    flo = n.new("ShaderNodeMath"); flo.operation = 'FLOOR'; l.new(div.outputs[0], flo.inputs[0])
    wn = n.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = '1D'
    l.new(flo.outputs[0], wn.inputs["W"])
    # grain
    comb = n.new("ShaderNodeCombineXYZ")
    mulu = n.new("ShaderNodeMath"); mulu.operation = 'MULTIPLY'; mulu.inputs[1].default_value = 40
    l.new(add.outputs[0], mulu.inputs[0]); l.new(mulu.outputs[0], comb.inputs[0]); l.new(sep.outputs[2], comb.inputs[1])
    noi = n.new("ShaderNodeTexNoise"); noi.inputs["Scale"].default_value = 3; noi.inputs["Detail"].default_value = 8
    l.new(comb.outputs[0], noi.inputs["Vector"])
    mix = n.new("ShaderNodeMath"); mix.operation = 'MULTIPLY_ADD'
    mix.inputs[1].default_value = 0.6
    l.new(wn.outputs["Value"], mix.inputs[0]); l.new(noi.outputs["Fac"], mix.inputs[2])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c2, 1); ramp.color_ramp.elements[1].color = (*c1, 1)
    ramp.color_ramp.elements[0].position = 0.25; ramp.color_ramp.elements[1].position = 1.0
    l.new(mix.outputs[0], ramp.inputs[0]); l.new(ramp.outputs[0], b.inputs["Base Color"])
    # groove bump between boards
    frac = n.new("ShaderNodeMath"); frac.operation = 'FRACT'; l.new(div.outputs[0], frac.inputs[0])
    gr = n.new("ShaderNodeValToRGB")
    gr.color_ramp.elements[0].position = 0.0; gr.color_ramp.elements[0].color = (0, 0, 0, 1)
    gr.color_ramp.elements[1].position = 0.06; gr.color_ramp.elements[1].color = (1, 1, 1, 1)
    l.new(frac.outputs[0], gr.inputs[0])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.4
    l.new(gr.outputs[0], bump.inputs["Height"]); l.new(bump.outputs[0], b.inputs["Normal"])
    return m

def stone_mat(name):
    m = mat(name, (0.45, 0.44, 0.42), 0.85)
    nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n["Principled BSDF"]
    tc, sep, add = world_xy_z(nt)
    comb = n.new("ShaderNodeCombineXYZ")
    l.new(add.outputs[0], comb.inputs[0]); l.new(sep.outputs[2], comb.inputs[1])
    br = n.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = 0.45
    br.inputs["Row Height"].default_value = 0.075
    br.inputs["Mortar Size"].default_value = 0.006
    br.inputs["Color1"].default_value = (0.55, 0.54, 0.52, 1)
    br.inputs["Color2"].default_value = (0.30, 0.29, 0.28, 1)
    br.inputs["Mortar"].default_value = (0.12, 0.12, 0.12, 1)
    br.offset = 0.37
    l.new(comb.outputs[0], br.inputs["Vector"])
    noi = n.new("ShaderNodeTexNoise"); noi.inputs["Scale"].default_value = 30
    l.new(comb.outputs[0], noi.inputs["Vector"])
    mixc = n.new("ShaderNodeMix"); mixc.data_type = 'RGBA'; mixc.blend_type = 'OVERLAY'
    mixc.inputs["Factor"].default_value = 0.5
    l.new(br.outputs["Color"], mixc.inputs["A"]); l.new(noi.outputs["Color"], mixc.inputs["B"])
    l.new(mixc.outputs["Result"], b.inputs["Base Color"])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.8
    hm = n.new("ShaderNodeMath"); hm.operation = 'ADD'
    l.new(br.outputs["Fac"], hm.inputs[0]); l.new(noi.outputs["Fac"], hm.inputs[1])
    l.new(hm.outputs[0], bump.inputs["Height"]); l.new(bump.outputs[0], b.inputs["Normal"])
    return m

def noisy_mat(name, c1, c2, scale=2.0, rough=0.8):
    m = mat(name, c1, rough)
    nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord")
    noi = n.new("ShaderNodeTexNoise"); noi.inputs["Scale"].default_value = scale; noi.inputs["Detail"].default_value = 10
    l.new(tc.outputs["Object"], noi.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c2, 1); ramp.color_ramp.elements[1].color = (*c1, 1)
    l.new(noi.outputs["Fac"], ramp.inputs[0]); l.new(ramp.outputs[0], b.inputs["Base Color"])
    return m

def paver_mat(name):
    m = mat(name, (0.6, 0.6, 0.6), 0.7)
    nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord")
    br = n.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = 1.2
    br.inputs["Row Height"].default_value = 0.6
    br.inputs["Mortar Size"].default_value = 0.01
    br.inputs["Color1"].default_value = (0.62, 0.63, 0.65, 1)
    br.inputs["Color2"].default_value = (0.52, 0.53, 0.55, 1)
    br.inputs["Mortar"].default_value = (0.35, 0.35, 0.36, 1)
    l.new(tc.outputs["Object"], br.inputs["Vector"])
    l.new(br.outputs["Color"], b.inputs["Base Color"])
    return m

def emit_mat(name, color, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*color, 1); e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs[0])
    return m

M = {
    "wood":   wood_mat("Cedar Siding", (0.36, 0.17, 0.08), (0.16, 0.07, 0.03)),
    "soffit": wood_mat("Wood Ceiling", (0.55, 0.34, 0.18), (0.33, 0.19, 0.09), 0.11),
    "floor":  wood_mat("Oak Floor", (0.62, 0.46, 0.30), (0.42, 0.29, 0.17), 0.2),
    "cab":    wood_mat("Walnut Millwork", (0.40, 0.24, 0.13), (0.22, 0.12, 0.06), 0.3),
    "stone":  stone_mat("Ledgestone"),
    "black":  mat("Black Metal", (0.015, 0.015, 0.016), 0.35, 0.6),
    "roof":   mat("Roof Membrane", (0.02, 0.02, 0.02), 0.6),
    "glass":  mat("Glass", (0.9, 0.95, 0.95), 0.0, 0.0, **{"Transmission Weight": 1.0, "IOR": 1.45}),
    "tint":   mat("Tinted Glass", (0.02, 0.02, 0.025), 0.05, 0.3),
    "white":  mat("Plaster", (0.85, 0.82, 0.77), 0.8),
    "conc":   noisy_mat("Concrete", (0.62, 0.61, 0.59), (0.5, 0.49, 0.47), 6, 0.8),
    "paver":  paver_mat("Pavers"),
    "grass":  noisy_mat("Lawn", (0.10, 0.30, 0.04), (0.05, 0.18, 0.02), 0.3, 0.9),
    "fabric": mat("Linen", (0.70, 0.63, 0.53), 0.9),
    "fabric2":mat("Olive Fabric", (0.22, 0.24, 0.14), 0.9),
    "quartz": noisy_mat("Quartz", (0.86, 0.83, 0.78), (0.72, 0.68, 0.62), 4, 0.25),
    "birch":  noisy_mat("Birch Bark", (0.85, 0.84, 0.80), (0.2, 0.2, 0.2), 8, 0.7),
    "bark":   mat("Bark", (0.12, 0.08, 0.05), 0.9),
    "leaf":   noisy_mat("Leaves", (0.16, 0.36, 0.08), (0.06, 0.16, 0.03), 3, 0.7),
    "pine":   noisy_mat("Pine Needles", (0.05, 0.16, 0.06), (0.02, 0.08, 0.03), 3, 0.8),
    "shrub":  noisy_mat("Shrub", (0.08, 0.25, 0.06), (0.03, 0.12, 0.02), 5, 0.8),
    "lamp":   emit_mat("Lamp Glow", (1.0, 0.8, 0.55), 12),
    "fire":   emit_mat("Fire", (1.0, 0.45, 0.1), 40),
    "tub":    mat("Porcelain", (0.93, 0.92, 0.9), 0.15),
}

# ---------------------------------------------------------------- primitives
def box(name, x0, y0, z0, x1, y1, z1, m, c=C_SHELL, bevel=0.0):
    x0, x1 = min(x0, x1), max(x0, x1); y0, y1 = min(y0, y1), max(y0, y1); z0, z1 = min(z0, z1), max(z0, z1)
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 + (v.co.x + 0.5) * (x1 - x0)
        v.co.y = y0 + (v.co.y + 0.5) * (y1 - y0)
        v.co.z = z0 + (v.co.z + 0.5) * (z1 - z0)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); c.objects.link(o)
    me.materials.append(m)
    if bevel:
        bv = o.modifiers.new("Bevel", 'BEVEL'); bv.width = bevel; bv.segments = 2
    return o

def cyl(name, x, y, z0, z1, r, m, c=C_INT, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=z1 - z0, location=(x, y, (z0 + z1) / 2))
    o = bpy.context.active_object; o.name = name
    for cc in o.users_collection: cc.objects.unlink(o)
    c.objects.link(o); o.data.materials.append(m)
    return o

def sphere(name, loc, r, m, c=C_INT, sub=3):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    o = bpy.context.active_object; o.name = name
    for cc in o.users_collection: cc.objects.unlink(o)
    c.objects.link(o); o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o

def wall_box(axis, pc, t, s0, s1, z0, z1, m, name):
    if axis == 'x':  # runs along x at y = pc
        return box(name, s0, pc - t / 2, z0, s1, pc + t / 2, z1, m)
    return box(name, pc - t / 2, s0, z0, pc + t / 2, s1, z1, m)

def glazing(axis, pc, s0, s1, z0, z1, nv=1, transoms=(), gm=None, name="Glazing", fw=0.07, depth=0.12):
    """Curtain-wall unit: black frame + mullions + glass pane."""
    gm = gm or M["glass"]
    fm = M["black"]
    def fb(a0, a1, b0, b1, dd=depth, off=0.0):
        if axis == 'x':
            return box(name + "_frame", a0, pc - dd / 2 + off, b0, a1, pc + dd / 2 + off, b1, fm, C_GLASS)
        return box(name + "_frame", pc - dd / 2 + off, a0, b0, pc + dd / 2 + off, a1, b1, fm, C_GLASS)
    fb(s0, s1, z0, z0 + fw); fb(s0, s1, z1 - fw, z1)
    fb(s0, s0 + fw, z0, z1); fb(s1 - fw, s1, z0, z1)
    for i in range(1, nv):
        s = s0 + (s1 - s0) * i / nv
        fb(s - fw / 2, s + fw / 2, z0, z1)
    for tz in transoms:
        fb(s0, s1, tz - fw / 2, tz + fw / 2)
    if axis == 'x':
        box(name + "_glass", s0, pc - 0.012, z0, s1, pc + 0.012, z1, gm, C_GLASS)
    else:
        box(name + "_glass", pc - 0.012, s0, z0, pc + 0.012, s1, z1, gm, C_GLASS)

def wall(axis, pc, s0, s1, z0, z1, m, openings=(), t=0.3, name="Wall"):
    """Axis-aligned wall with rectangular openings, each opening = dict(s0,s1,z0,z1,nv,tr,gm)."""
    ops = sorted(openings, key=lambda o: o["s0"])
    cur = s0
    for o in ops:
        if o["s0"] > cur:
            wall_box(axis, pc, t, cur, o["s0"], z0, z1, m, name)
        if o["z0"] > z0:
            wall_box(axis, pc, t, o["s0"], o["s1"], z0, o["z0"], m, name)
        if o["z1"] < z1:
            wall_box(axis, pc, t, o["s0"], o["s1"], o["z1"], z1, m, name)
        glazing(axis, pc, o["s0"], o["s1"], o["z0"], o["z1"], o.get("nv", 1), o.get("tr", ()), o.get("gm"), name + "_win")
        cur = o["s1"]
    if cur < s1:
        wall_box(axis, pc, t, cur, s1, z0, z1, m, name)

def op(s0, s1, z0, z1, nv=1, tr=(), gm=None):
    return dict(s0=s0, s1=s1, z0=z0, z1=z1, nv=nv, tr=tr, gm=gm)

def roof(name, x0, y0, x1, y1, z, th=0.35):
    """Flat roof: black membrane + fascia, wood soffit underneath."""
    box(name, x0, y0, z + 0.04, x1, y1, z + th, M["roof"], C_ROOF)
    box(name + "_soffit", x0 + 0.02, y0 + 0.02, z, x1 - 0.02, y1 - 0.02, z + 0.04, M["soffit"], C_ROOF)

FL = 0.3     # finished ground-floor level
H1 = 3.6     # ground floor plate
H2 = 7.2     # upper plate

# ================================================================ SLABS
box("Foundation", 0.3, 2.0, 0, 30.4, 21.0, FL, M["conc"])
box("Floor_Main", 0.5, 2.1, FL, 30.2, 20.9, FL + 0.015, M["floor"], C_INT)
box("Garage_Slab", 0.0, 0.0, 0, 10.0, 8.0, 0.15, M["conc"])

# ================================================================ GARAGE  (x 0-10, y 0-8)
wall('x', 0.15, 0, 10, 0, 3.4, M["wood"],
     [op(0.7, 5.5, 0.15, 2.9, nv=4, tr=(0.8, 1.5, 2.2), gm=M["tint"]),
      op(6.0, 9.3, 0.15, 2.9, nv=3, tr=(0.8, 1.5, 2.2), gm=M["tint"])], name="Garage_S")
wall('y', 0.15, 0.3, 8.0, 0, 3.4, M["wood"], name="Garage_W")
wall('x', 7.85, 0.3, 10, 0, 3.4, M["white"], name="Garage_N")
wall('y', 9.85, 0.3, 8.0, 0, 3.4, M["white"], name="Garage_E")
roof("Roof_Garage", -0.6, -1.1, 10.4, 8.3, 3.4)

# ================================================================ WEST WING  (primary suite / mud)  x 0.5-11, y 8-21
wall('y', 0.65, 7.7, 21.0, 0, H1, M["wood"],
     [op(9.6, 11.2, 1.2, 3.1, nv=1),
      op(13.0, 20.0, FL, 3.3, nv=4, tr=(2.4,))], name="West_W")
wall('x', 20.85, 0.5, 11.0, 0, H1, M["wood"],
     [op(2.0, 7.6, FL, 3.3, nv=3, tr=(2.4,))], name="West_N")
roof("Roof_West", -0.1, 7.8, 11.2, 21.6, H1)
# primary suite partitions (interior)
wall('y', 8.0, 12.0, 20.7, FL, H1, M["white"], t=0.15, name="Int_Suite_E")
wall('x', 12.0, 0.8, 8.0, FL, H1, M["white"], t=0.15, name="Int_Suite_S")
wall('x', 9.2, 0.8, 10.0, FL, H1, M["white"], t=0.15, name="Int_Mud")

# ================================================================ CENTRAL TWO-STORY  x 11-22, y 2-21
# ground-floor front: entry glass
wall('x', 2.15, 11.0, 22.0, 0, H1, M["wood"],
     [op(12.4, 15.9, FL, 3.45, nv=3, tr=(2.6,)),
      op(15.9, 18.1, FL, 3.45, nv=2, tr=(2.6,)),           # entry doors
      op(18.1, 20.8, FL, 3.45, nv=2, tr=(2.6,))], name="Center_S_G")
wall('y', 11.15, 2.0, 8.0, 0, H1, M["wood"], name="Center_W_G")
wall('y', 11.15, 8.0, 15.0, FL, H1, M["white"], t=0.15, name="Int_Living_W")
# entry canopy / lower roof plane that projects past the upper volume
roof("Roof_Canopy", 9.9, 0.6, 23.4, 4.3, H1)
# north: double-height living glass + upper bedroom walls
glazing('x', 20.85, 13.6, 19.4, FL, H2 - 0.05, nv=5, transoms=(3.6,), name="Living_N")
wall('x', 20.85, 11.0, 13.6, 0, H1, M["wood"], name="Center_N_Gw")
wall('x', 20.85, 19.4, 22.0, 0, H1, M["wood"], [op(19.8, 21.7, FL, 3.3, nv=1)], name="Center_N_Ge")
# upper floor volume  (x 11-22, y 4-21)
UZ = H1
wall('x', 4.15, 11.0, 22.2, UZ, H2, M["wood"],
     [op(11.5, 13.6, UZ + 0.4, H2 - 0.3, nv=2),
      op(15.0, 18.0, UZ + 0.4, H2 - 0.3, nv=3),
      op(19.2, 21.6, UZ + 0.4, H2 - 0.3, nv=2)], name="Upper_S")
wall('y', 11.15, 4.0, 21.0, UZ, H2, M["wood"],
     [op(6.0, 9.0, UZ + 0.6, H2 - 0.3, nv=2), op(16.0, 19.2, UZ + 0.6, H2 - 0.3, nv=2)], name="Upper_W")
wall('y', 22.05, 4.0, 21.0, 3.8, H2, M["wood"],
     [op(6.5, 9.8, UZ + 0.6, H2 - 0.3, nv=2), op(15.0, 18.4, UZ + 0.6, H2 - 0.3, nv=2)], name="Upper_E")
wall('x', 20.85, 11.0, 13.6, UZ, H2, M["wood"], [op(11.5, 13.2, UZ + 0.6, H2 - 0.3)], name="Upper_Nw")
wall('x', 20.85, 19.4, 22.2, UZ, H2, M["wood"], [op(19.8, 21.8, UZ + 0.6, H2 - 0.3)], name="Upper_Ne")
# stepped upper roofs
roof("Roof_Upper_W", 10.3, 3.2, 17.0, 21.8, H2)
roof("Roof_Upper_E", 16.4, 3.0, 23.0, 22.0, H2 + 0.35)
box("Clerestory_Band", 16.4, 3.7, H2, 17.0, 21.3, H2 + 0.35, M["tint"], C_GLASS)

# upper floor slab with living void + stair void
for i, (a, b, c, d) in enumerate([(11.3, 4.3, 13.6, 20.7), (19.4, 4.3, 21.9, 20.7),
                                  (14.9, 4.3, 19.4, 15.0), (13.6, 9.6, 14.9, 15.0), (13.6, 4.3, 14.9, 5.0)]):
    box(f"Upper_Slab_{i}", a, b, H1, c, d, H1 + 0.3, M["white"], C_INT)
    box(f"Upper_Floor_{i}", a, b, H1 + 0.3, c, d, H1 + 0.32, M["floor"], C_INT)
# glass balustrade along the open-to-below edge
glazing('x', 15.0, 13.6, 19.4, H1 + 0.32, H1 + 1.4, nv=4, name="Balustrade")
# upper interior partitions (4 bedrooms around the loft)
wall('y', 13.6, 15.0, 20.7, H1 + 0.3, H2, M["white"], t=0.15, name="Int_Up")
wall('y', 19.4, 15.0, 20.7, H1 + 0.3, H2, M["white"], t=0.15, name="Int_Up")
wall('x', 11.0, 11.3, 13.6, H1 + 0.3, H2, M["white"], t=0.15, name="Int_Up")
wall('x', 11.0, 19.4, 21.9, H1 + 0.3, H2, M["white"], t=0.15, name="Int_Up")
wall('y', 13.6, 9.6, 11.0, H1 + 0.3, H2, M["white"], t=0.15, name="Int_Up")
wall('y', 19.4, 4.3, 11.0, H1 + 0.3, H2, M["white"], t=0.15, name="Int_Up")

# ================================================================ EAST WING  (office / kitchen) x 22-30.4, y 3-19
EH = 3.8
wall('x', 3.15, 22.0, 30.4, 0, EH, M["wood"],
     [op(23.2, 29.3, FL, 3.5, nv=5, tr=(2.7,))], name="East_S")
wall('y', 30.25, 3.0, 19.0, 0, EH, M["wood"],
     [op(4.6, 9.2, FL, 3.4, nv=3, tr=(2.6,)), op(11.5, 17.6, FL, 3.4, nv=4, tr=(2.6,))], name="East_E")
wall('x', 18.85, 19.4, 30.4, 0, EH, M["wood"],
     [op(20.0, 22.6, FL, 3.3, nv=2), op(23.2, 29.4, 1.25, 3.3, nv=4)], name="East_N")
wall('x', 9.5, 22.2, 25.0, FL, EH, M["white"], t=0.15, name="Int_Office_N")
wall('x', 9.5, 27.6, 30.1, FL, EH, M["white"], t=0.15, name="Int_Office_N")
roof("Roof_East", 21.6, 1.9, 31.2, 19.9, EH)
# clerestory lantern over the office
glazing('x', 4.6, 24.0, 28.6, EH + 0.35, EH + 1.1, nv=4, name="Lantern_S")
glazing('x', 9.4, 24.0, 28.6, EH + 0.35, EH + 1.1, nv=4, name="Lantern_N")
glazing('y', 24.0, 4.6, 9.4, EH + 0.35, EH + 1.1, nv=2, name="Lantern_W")
glazing('y', 28.6, 4.6, 9.4, EH + 0.35, EH + 1.1, nv=2, name="Lantern_E")
roof("Roof_Lantern", 23.4, 4.0, 29.2, 10.0, EH + 1.1, 0.3)

# ================================================================ STONE PIERS & FIREPLACE
box("Stone_Pier_A", 9.7, -0.4, 0, 11.3, 2.3, 5.0, M["stone"], bevel=0.02)
box("Stone_Pier_B", 21.3, 1.1, 0, 22.9, 3.7, 6.4, M["stone"], bevel=0.02)
box("Stone_Pier_C", 29.6, 2.3, 0, 31.0, 4.8, 4.5, M["stone"], bevel=0.02)
# double-height fireplace column in the living room, chimney through roof
box("Fireplace_Column", 11.3, 15.3, FL, 12.7, 19.9, H2 + 1.1, M["stone"], C_INT, bevel=0.02)
box("Fireplace_Firebox", 12.68, 16.2, 0.75, 12.72, 19.0, 1.25, M["black"], C_INT)
box("Fireplace_Flame", 12.71, 16.35, 0.8, 12.73, 18.85, 1.05, M["fire"], C_INT)
box("Fireplace_Hearth", 11.3, 15.3, FL, 13.2, 19.9, FL + 0.4, M["stone"], C_INT)

# ================================================================ COVERED PATIO (north)
box("Patio_Slab", 11.6, 21.0, 0, 20.4, 26.0, FL - 0.05, M["conc"], C_SITE)
roof("Roof_Patio", 11.2, 20.8, 20.8, 26.4, 3.4, 0.3)
for (px, py) in [(11.5, 26.1), (20.5, 26.1)]:
    box("Patio_Post", px - 0.12, py - 0.12, FL - 0.05, px + 0.12, py + 0.12, 3.4, M["black"], C_SITE)
cyl("Fire_Pit", 16.0, 23.6, FL - 0.05, FL + 0.35, 0.65, M["conc"], C_SITE)
cyl("Fire_Pit_Flame", 16.0, 23.6, FL + 0.35, FL + 0.37, 0.45, M["fire"], C_SITE)
for a in (0, 1, 2, 3):
    ang = a * math.pi / 2 + math.pi / 4
    x, y = 16 + 1.9 * math.cos(ang), 23.6 + 1.6 * math.sin(ang)
    box("Patio_Chair", x - 0.4, y - 0.4, FL, x + 0.4, y + 0.4, FL + 0.42, M["fabric"], C_SITE, 0.05)

# ================================================================ ENTRY STEPS
box("Entry_Step_1", 15.4, 0.4, 0, 18.6, 2.0, 0.1, M["conc"], C_SITE)
box("Entry_Step_2", 15.4, 1.2, 0.1, 18.6, 2.0, 0.2, M["conc"], C_SITE)

# ================================================================ INTERIOR FURNISHINGS
I = C_INT
# floating stair (open treads, stringer, glass rail)
for i in range(12):
    y = 5.2 + i * 0.35; z = FL + (i + 1) * 0.3
    box("Stair_Tread", 13.7, y, z - 0.06, 14.8, y + 0.33, z, M["cab"], I)
box("Stair_Stringer", 13.62, 5.1, FL, 13.72, 9.5, H1 + 0.3, M["black"], I)
# living: L sofa, coffee table, rug
box("Rug_Living", 13.8, 15.8, FL, 18.6, 20.2, FL + 0.01, M["fabric"], I)
box("Sofa_A", 14.2, 16.2, FL, 18.2, 17.1, FL + 0.75, M["fabric"], I, 0.08)
box("Sofa_B", 14.2, 16.2, FL, 15.1, 19.6, FL + 0.75, M["fabric"], I, 0.08)
for x in (15.5, 16.4, 17.3):
    box("Cushion", x, 16.3, FL + 0.45, x + 0.5, 16.5, FL + 0.95, M["fabric2"], I, 0.06)
cyl("Coffee_Table", 16.6, 18.4, FL, FL + 0.38, 0.65, M["black"], I)
# dining
box("Dining_Table", 15.6, 11.2, FL + 0.72, 18.6, 12.3, FL + 0.77, M["cab"], I)
box("Dining_Leg", 16.0, 11.6, FL, 16.2, 11.9, FL + 0.72, M["black"], I)
box("Dining_Leg", 18.0, 11.6, FL, 18.2, 11.9, FL + 0.72, M["black"], I)
for x in (15.9, 16.8, 17.7):
    for y, d in ((10.6, 0), (12.5, 0)):
        box("Dining_Chair", x, y, FL, x + 0.5, y + 0.5, FL + 0.48, M["fabric"], I, 0.04)
        box("Dining_Chair_Back", x, y + (0.42 if y < 11 else 0), FL + 0.48, x + 0.5, y + (0.5 if y < 11 else 0.08), FL + 0.9, M["fabric"], I, 0.03)
for (x, y, h) in [(16.3, 11.75, 4.6), (17.9, 11.75, 4.2), (16.8, 18.2, 5.2), (17.4, 17.6, 4.8)]:
    sphere("Pendant", (x, y, h), 0.32, M["lamp"], I)
    cyl("Pendant_Cord", x, y, h, H2 if y > 15 else H1, 0.006, M["black"], I, 8)
# kitchen (east wing north)
box("Kitchen_Island", 24.2, 13.2, FL, 28.4, 14.4, FL + 0.92, M["cab"], I)
box("Island_Top", 24.1, 13.1, FL + 0.92, 28.5, 14.5, FL + 0.97, M["quartz"], I)
box("Kitchen_Tall", 29.5, 10.2, FL, 30.1, 18.6, FL + 2.6, M["cab"], I)
box("Kitchen_Base", 23.2, 18.1, FL, 29.4, 18.7, FL + 0.9, M["cab"], I)
box("Kitchen_Counter", 23.2, 18.05, FL + 0.9, 29.4, 18.7, FL + 0.95, M["quartz"], I)
for x in (24.8, 25.9, 27.0, 28.0):
    cyl("Stool", x, 12.7, FL, FL + 0.72, 0.22, M["fabric"], I, 20)
box("Pantry_Wall", 22.2, 10.2, FL, 23.0, 14.0, FL + 2.6, M["cab"], I)
# office
box("Desk", 25.2, 6.0, FL + 0.72, 27.4, 6.9, FL + 0.76, M["cab"], I)
box("Desk_Base", 25.3, 6.1, FL, 25.6, 6.8, FL + 0.72, M["black"], I)
box("Desk_Base", 27.0, 6.1, FL, 27.3, 6.8, FL + 0.72, M["black"], I)
box("Bookcase", 22.4, 4.0, FL, 22.9, 9.2, FL + 2.8, M["cab"], I)
# primary suite
box("Bed_Primary", 2.8, 15.0, FL, 5.0, 17.2, FL + 0.55, M["fabric"], I, 0.05)
box("Bed_Primary_Head", 0.9, 14.8, FL, 1.1, 17.4, FL + 1.3, M["fabric"], I, 0.03)
box("Bed_Primary_Throw", 3.8, 14.95, FL + 0.55, 4.5, 17.25, FL + 0.6, M["fabric2"], I)
box("Bench", 5.1, 15.3, FL, 5.6, 16.9, FL + 0.45, M["cab"], I)
cyl("Tub", 4.0, 10.2, FL, FL + 0.6, 0.8, M["tub"], I).scale.x = 1.4
box("Vanity", 6.2, 8.4, FL, 7.8, 9.0, FL + 0.9, M["cab"], I)
# upstairs bedrooms
for (x0, y0) in [(11.6, 17.0), (19.8, 17.0), (11.6, 6.0), (19.9, 6.5)]:
    box("Bed_Upper", x0, y0, H1 + 0.32, x0 + 1.6, y0 + 2.0, H1 + 0.85, M["fabric"], I, 0.05)
box("Loft_Sofa", 15.4, 12.8, H1 + 0.32, 18.4, 13.7, H1 + 1.0, M["fabric2"], I, 0.08)
# indoor planters
for (x, y) in [(13.2, 19.8), (19.0, 20.2), (21.5, 14.6), (12.5, 3.0)]:
    cyl("Planter", x, y, FL, FL + 0.5, 0.25, M["conc"], I, 16)
    sphere("Plant", (x, y, FL + 1.1), 0.45, M["leaf"], I, 2)

# ================================================================ SITE
bpy.ops.mesh.primitive_plane_add(size=240, location=(15, 10, 0))
g = bpy.context.active_object; g.name = "Lawn"
for cc in g.users_collection: cc.objects.unlink(g)
C_SITE.objects.link(g); g.data.materials.append(M["grass"])

def catmull(pts, n=12):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = [Vector(p) for p in P[i - 1:i + 3]]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(Vector(pts[-1]))
    return out

def strip(name, pts, width, z, m):
    path = catmull(pts)
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    L, R = [], []
    for i, p in enumerate(path):
        a = path[max(i - 1, 0)]; b = path[min(i + 1, len(path) - 1)]
        tng = (b - a).normalized(); nrm = Vector((-tng.y, tng.x))
        L.append(bm.verts.new((p.x + nrm.x * width / 2, p.y + nrm.y * width / 2, z)))
        R.append(bm.verts.new((p.x - nrm.x * width / 2, p.y - nrm.y * width / 2, z)))
    for i in range(len(path) - 1):
        bm.faces.new((L[i], R[i], R[i + 1], L[i + 1]))
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); C_SITE.objects.link(o); me.materials.append(m)
    return o

strip("Driveway", [(17, -60), (17, -30), (15, -17), (10, -9.5), (5, -4.6)], 6.0, 0.03, M["paver"])
box("Garage_Apron", -0.4, -8.2, 0, 10.4, 0.0, 0.04, M["paver"], C_SITE)
box("Entry_Walk", 14.8, -9.0, 0, 19.2, 0.4, 0.04, M["paver"], C_SITE)

# ---------------------------------------------------------------- vegetation
def blob(name, loc, r, m, c=C_TREES, noise=0.35):
    o = sphere(name, loc, r, m, c, 3)
    tex = bpy.data.textures.get("FoliageNoise") or bpy.data.textures.new("FoliageNoise", 'CLOUDS')
    tex.noise_scale = 0.35
    d = o.modifiers.new("Displace", 'DISPLACE'); d.texture = tex; d.strength = r * noise
    d.texture_coords = 'GLOBAL'
    return o

def birch(x, y, h=None):
    h = h or random.uniform(9, 13)
    t = cyl("Birch_Trunk", x, y, 0, h, 0.14, M["birch"], C_TREES, 10)
    t.rotation_euler = (random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), 0)
    for i in range(12):
        z = random.uniform(h * 0.3, h * 0.97)
        blob("Birch_Leaves", (x + random.uniform(-1.8, 1.8), y + random.uniform(-1.8, 1.8), z),
             random.uniform(0.7, 1.3), M["leaf"], noise=0.6)

def pine(x, y, h=None):
    h = h or random.uniform(14, 22)
    cyl("Pine_Trunk", x, y, 0, h, 0.25, M["bark"], C_TREES, 8)
    layers = 7
    for i in range(layers):
        z0 = h * 0.35 + i * (h * 0.62 / layers)
        r = (1 - i / layers) * random.uniform(2.2, 3.0) + 0.4
        bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=r, radius2=0.1, depth=h * 0.2, location=(x, y, z0 + h * 0.1))
        o = bpy.context.active_object; o.name = "Pine_Tier"
        for cc in o.users_collection: cc.objects.unlink(o)
        C_TREES.objects.link(o); o.data.materials.append(M["pine"])
        o.rotation_euler.z = random.uniform(0, 6.28)

def decid(x, y, h=None):
    h = h or random.uniform(10, 15)
    cyl("Tree_Trunk", x, y, 0, h * 0.6, 0.3, M["bark"], C_TREES, 8)
    for i in range(10):
        blob("Tree_Canopy", (x + random.uniform(-2.6, 2.6), y + random.uniform(-2.6, 2.6),
                             h * random.uniform(0.5, 0.95)), random.uniform(1.4, 2.4), M["leaf"], noise=0.55)

def ok(x, y):
    if -3 < x < 34 and -2 < y < 29: return False            # house + patio
    if 11 < x < 21 and y < 0: return False                    # driveway corridor
    if -1 < x < 12 and -10 < y < 0: return False              # apron
    return True

# forest behind and around
for _ in range(70):
    x, y = random.uniform(-40, 70), random.uniform(28, 75)
    kind = random.choice([pine, pine, decid, birch])
    if 0 < x < 34 and y < 44: continue                        # keep rear view open
    kind(x, y)
for _ in range(26):
    side = random.choice([-1, 1])
    x = random.uniform(-40, -8) if side < 0 else random.uniform(40, 70)
    y = random.uniform(-20, 30)
    random.choice([pine, decid, birch])(x, y)
# feature birches in front (as in the elevation)
for (x, y) in [(-4.5, -3.0), (34.5, -2.0), (26.0, -3.5), (-6.5, 6.0), (35.5, 10.0)]:
    birch(x, y)
# foundation shrubs
for x in list(range(0, 10, 1)):
    blob("Shrub", (x + 0.5, -8.8 if x < 2 else -8.8, 0.4), 0.55, M["shrub"], C_TREES, 0.2) if False else None
for (x, y) in [(10.6, -2.0), (12.0, -0.8), (13.4, -0.8), (20.4, -0.8), (21.8, -0.6), (23.5, 1.9), (25.0, 2.1),
               (27.0, 2.1), (28.8, 2.0), (-1.2, 1.0), (-1.2, 3.0), (-1.2, 5.0), (8.5, -9.4), (6.0, -9.2),
               (19.9, -3.5), (14.2, -6.0), (31.5, 6.0), (31.5, 9.0), (31.4, 13.0)]:
    blob("Shrub", (x, y, 0.35), random.uniform(0.5, 0.9), M["shrub"], C_TREES, 0.25)

# ================================================================ LIGHTING / WORLD
world = bpy.data.worlds.new("Sky"); scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes; wl = world.node_tree.links
sky = wn.new("ShaderNodeTexSky")
sky.sky_type = 'MULTIPLE_SCATTERING'
try:
    sky.sun_disc = False
    sky.sun_elevation = math.radians(38); sky.sun_rotation = math.radians(210)
    sky.altitude = 300
except Exception as e:
    print("sky opts", e)
wl.new(sky.outputs[0], wn["Background"].inputs[0])
wn["Background"].inputs[1].default_value = 0.5

sun_d = bpy.data.lights.new("Sun", 'SUN'); sun_d.energy = 4.5; sun_d.angle = math.radians(1.5)
sun_d.color = (1.0, 0.95, 0.88)
sun = bpy.data.objects.new("Sun", sun_d); C_LIGHT.objects.link(sun)
sun.rotation_euler = (math.radians(52), 0, math.radians(-150))

def area(name, loc, size, energy, color=(1.0, 0.78, 0.55)):
    d = bpy.data.lights.new(name, 'AREA'); d.size = size; d.energy = energy; d.color = color
    o = bpy.data.objects.new(name, d); o.location = loc; C_LIGHT.objects.link(o)
    return o

for (x, y, z) in [(16.5, 18, H2 - 0.4), (17, 11.5, H1 - 0.3), (26, 14, EH - 0.3), (26, 6.5, EH - 0.3),
                  (4, 16, H1 - 0.3), (16.8, 6, H1 - 0.3), (12.5, 18, H2 - 0.4), (20.5, 18, H2 - 0.4),
                  (12.5, 7, H2 - 0.4), (20.7, 7, H2 - 0.4), (16, 23.6, 3.1)]:
    area("Interior_Light", (x, y, z), 2.0, 180)

# ================================================================ CAMERAS
def camera(name, loc, target, lens=30):
    d = bpy.data.cameras.new(name); d.lens = lens; d.clip_end = 500
    o = bpy.data.objects.new(name, d); o.location = loc; C_LIGHT.objects.link(o)
    direction = Vector(target) - Vector(loc)
    o.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return o

cams = {
    "front":  camera("Cam_Front", (15.5, -40, 3.2), (15.5, 6, 3.8), 34),
    "corner": camera("Cam_Corner", (-24, -30, 9), (13, 8, 2.5), 32),
    "aerial": camera("Cam_Aerial", (55, -38, 42), (15, 10, 0), 32),
    "rear":   camera("Cam_Rear", (27, 42, 3.0), (15, 17, 3.6), 28),
    "living": camera("Cam_Living", (19.0, 13.0, 1.9), (12.0, 19.5, 2.4), 20),
}
scene.camera = cams["front"]

# ================================================================ RENDER SETTINGS
r = scene.render
r.engine = 'CYCLES'
r.resolution_x, r.resolution_y = 1920, 1080
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'HIP'
    prefs.get_devices()
    for dv in prefs.devices: dv.use = True
    scene.cycles.device = 'GPU'
except Exception as e:
    print("GPU setup failed, using CPU:", e)
scene.view_settings.view_transform = 'AgX'
try: scene.view_settings.look = 'AgX - Punchy'
except Exception: pass
scene.view_settings.exposure = 0.0

blend = os.path.join(OUT, "ModernSanctuary.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
print("SAVED", blend)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if argv:
    which = argv[0].split(",")
    if len(argv) > 1: scene.cycles.samples = int(argv[1])
    for k in which:
        scene.camera = cams[k]
        r.filepath = os.path.join(OUT, "renders", f"{k}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", r.filepath)



