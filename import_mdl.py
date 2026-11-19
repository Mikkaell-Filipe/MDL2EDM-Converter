"""MDL (FSX/P3D/MSFS) -> Blender, pronto para exportar para o DCS com o addon io_scene_edm_custom.

Estrutura criada (tudo em coordenadas nativas do EDM: x frente, y cima, z direita):
  * root 'MDL_AXIS_FIX' (permutacao de eixos), ou, se informar um empty de no de um EDM ja
    importado, o root fica sob esse no (sem rotacao extra);
  * 1 empty por no do MDL ('<idx>_node');
  * cada PART do MDL = 1 mesh separado, filho do empty do seu no;
  * cada no ANIMADO = 1 PIVO do addon custom (edm_new_anim=1, edm_anim_kind=CUSTOM, edm_anim_arg=N,
    Action '<N>_<nome>', frame = (arg+1)*100).
  * nos com condicao de visibilidade ganham 'mdl_visible_expr' (texto original, nao convertido).
"""
import math
import os

import bpy
import mathutils

from . import mdl_reader as R


def _perm(v):
    """MDL (x dir, y cima, z frente) -> EDM (x frente, y cima, z dir)."""
    return (v[2], v[1], v[0])


def _node_matrix(rows):
    m = [[float(rows[r][c]) for c in range(4)] for r in range(4)]
    idx = (2, 1, 0)
    out = [[0.0] * 4 for _ in range(4)]
    for r in range(3):
        for c in range(3):
            out[r][c] = m[idx[r]][idx[c]]
    for c in range(3):
        out[3][c] = m[3][idx[c]]
    out[3][3] = 1.0
    return mathutils.Matrix(tuple(tuple(out[c][r] for c in range(4)) for r in range(4)))


def _quat_to_rot3_col(q):
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def _quat_edm(q, invert=False):
    r = _quat_to_rot3_col(q)
    if invert:
        r = [[r[b][a] for b in range(3)] for a in range(3)]
    idx = (2, 1, 0)
    rp = [[r[idx[a]][idx[b]] for b in range(3)] for a in range(3)]
    return mathutils.Matrix(rp).to_quaternion()


def _find_image(name, tex_dir):
    if not tex_dir:
        return None
    base = os.path.splitext(name)[0]
    for ext in ('', '.dds', '.png', '.tga', '.jpg', '.bmp'):
        for cand in (name, base + ext, base.lower() + ext, base.upper() + ext):
            p = os.path.join(tex_dir, cand)
            if os.path.isfile(p):
                return p
    return None


def _make_materials(mdl, tex_dir):
    mats = []
    tex = mdl['textures']
    for mi, dw in enumerate(mdl['materials']):
        flags = dw[0]
        diff = tex[dw[2]] if (flags & 0x2) and dw[2] < len(tex) else None
        bump = tex[dw[4]] if (flags & 0x8) and dw[4] < len(tex) else None
        name = 'mdl_mat%02d_%s' % (mi, os.path.splitext(diff)[0].lstrip('$') if diff else 'notex')
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat['mdl_flags'] = int(flags)
        if diff:
            mat['mdl_diffuse'] = diff
        if bump:
            mat['mdl_bump'] = bump
        nt = mat.node_tree
        bsdf = nt.nodes.get('Principled BSDF')
        if diff and bsdf is not None:
            node = nt.nodes.new('ShaderNodeTexImage')
            iname = os.path.splitext(diff)[0].lstrip('$') + '.dds'
            p = _find_image(diff, tex_dir)
            img = None
            if p:
                try:
                    img = bpy.data.images.load(p, check_existing=True)
                    img.name = iname
                except Exception:
                    img = None
            if img is None:
                img = bpy.data.images.new(iname, 4, 4)
                img.source = 'FILE'
                img.filepath = os.path.join(tex_dir or '', iname)
            node.image = img
            nt.links.new(node.outputs['Color'], bsdf.inputs['Base Color'])
        elif bsdf is not None:
            bsdf.inputs['Base Color'].default_value = (0.6, 0.6, 0.6, 1.0)
        mats.append(mat)
    return mats


def _build_part_mesh(name, mdl, part, scale):
    vb = mdl['vertex_buffers'][part['vbuf']]
    v = vb[part['base']:part['base'] + part['nverts']]
    ix = mdl['indices'][part['istart']:part['istart'] + part['icount']]
    if len(ix) < 3 or len(v) == 0 or int(ix.max()) >= len(v):
        return None
    used = sorted(set(int(i) for i in ix))
    remap = {o: n for n, o in enumerate(used)}
    pos = [(float(v[o][2]) * scale, float(v[o][1]) * scale, float(v[o][0]) * scale) for o in used]
    nor = [(float(v[o][5]), float(v[o][4]), float(v[o][3])) for o in used]
    uv = [(float(v[o][6]), 1.0 - float(v[o][7])) for o in used]
    tris = [(remap[int(ix[i])], remap[int(ix[i + 1])], remap[int(ix[i + 2])]) for i in range(0, len(ix) - 2, 3)]
    agree = 0
    for a, b, c in tris[:400]:
        pa, pb, pc = (mathutils.Vector(pos[k]) for k in (a, b, c))
        fn = (pb - pa).cross(pc - pa)
        vn = mathutils.Vector(nor[a]) + mathutils.Vector(nor[b]) + mathutils.Vector(nor[c])
        agree += 1 if fn.dot(vn) >= 0 else -1
    flip = agree < 0
    if flip:
        tris = [(a, c, b) for a, b, c in tris]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(pos, [], tris)
    mesh.validate()
    mesh.update()
    try:
        mesh.normals_split_custom_set_from_vertices(nor)
    except Exception:
        pass
    layer = mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            layer.data[li].uv = uv[mesh.loops[li].vertex_index]
    return mesh, flip


def _set_linear(obj):
    ad = obj.animation_data
    action = ad.action if ad else None
    if action is None:
        return
    try:
        fcs = list(action.fcurves)
    except Exception:
        fcs = []
        try:
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        fcs.extend(bag.fcurves)
        except Exception:
            pass
    for fc in fcs:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'


def import_mdl(context, filepath, scale=1.0, tex_dir='', first_arg=0, with_anim=True,
               normalize_time=True, edm_parent='', invert_rot=False):
    mdl = R.read_mdl(filepath)
    base = os.path.splitext(os.path.basename(filepath))[0]
    coll = bpy.data.collections.new(base)
    context.scene.collection.children.link(coll)
    coll['mdl_source_path'] = filepath
    report = {'parts': 0, 'skipped_parts': 0, 'anims': 0, 'flipped': 0, 'warnings': [], 'table': []}

    root = bpy.data.objects.new('MDL_AXIS_FIX', None)
    root.empty_display_type = 'ARROWS'
    root.empty_display_size = 0.5
    coll.objects.link(root)
    attach = bpy.data.objects.get(edm_parent) if edm_parent else None
    if edm_parent and attach is None:
        report['warnings'].append("empty '%s' nao encontrado: MDL_AXIS_FIX ficou solto na cena" % edm_parent)
    if attach is not None:
        root.parent = attach
        root.matrix_basis = mathutils.Matrix.Identity(4)
    else:
        root.matrix_basis = mathutils.Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))

    mats = _make_materials(mdl, tex_dir)
    n = len(mdl['scene'])
    node_obj = [None] * n
    arg_counter = first_arg

    def make_node(i):
        nonlocal arg_counter
        typ, ti = mdl['amap'][i]
        aid = mdl['sg_anim'][i]
        rest = _node_matrix(mdl['matrices'][ti]) if ti < len(mdl['matrices']) else mathutils.Matrix.Identity(4)
        par = node_obj[mdl['parent'][i]] if mdl['parent'][i] != -1 else root
        anim = mdl['animations'].get(aid) if (with_anim and aid != -1) else None
        e = bpy.data.objects.new('%03d_node' % i, None)
        e.empty_display_type = 'PLAIN_AXES'
        e.empty_display_size = 0.05
        e.rotation_mode = 'QUATERNION'
        coll.objects.link(e)
        e.parent = par
        e['mdl_node_index'] = i
        e['mdl_node_type'] = int(typ)
        vi = mdl['sg_vis'][i]
        if vi != -1 and 0 <= vi < len(mdl['vis_conditions']):
            e['mdl_visible_expr'] = mdl['vis_conditions'][vi].strip()
        if anim is None or not anim['keys']:
            e.matrix_basis = rest
            return e
        arg = arg_counter
        arg_counter += 1
        e.name = '%03d_anim%d' % (i, arg)
        e.matrix_parent_inverse = rest
        e['edm_new_anim'] = 1
        e['edm_anim_kind'] = 'CUSTOM'
        e['edm_anim_arg'] = int(arg)
        e['edm_anim_name'] = e.name
        e['mdl_sim_var'] = anim['var']
        e['mdl_sim_units'] = anim['units']
        e['mdl_sim_code'] = anim['code'].strip()
        keys = anim['keys']
        tmax = max(t for t, _ in keys) or 1.0
        norm = tmax if normalize_time else (anim['duration'] or 100.0)
        e['mdl_time_max'] = float(norm)
        e.animation_data_create()
        e.animation_data.action = bpy.data.actions.new('%d_%s' % (arg, e.name))
        prev_q = None
        for t, val in keys:
            a = t / norm
            frame = (a + 1.0) * 100.0
            if frame < 0 or frame > 200 + 1e-6:
                report['warnings'].append("no %d: chave em arg %.2f fora de -1..1 foi ignorada" % (i, a))
                continue
            if anim['kind'] == 'ROT':
                q = _quat_edm(val, invert_rot)
                if prev_q is not None and q.dot(prev_q) < 0:
                    q.negate()
                prev_q = q
                e.rotation_quaternion = q
                e.keyframe_insert('rotation_quaternion', frame=frame)
            else:
                v = _perm(val)
                e.location = (v[0] * scale, v[1] * scale, v[2] * scale)
                e.keyframe_insert('location', frame=frame)
        _set_linear(e)
        report['anims'] += 1
        report['table'].append((arg, e.name, anim['kind'], anim['var'], anim['units'], anim['code'].strip()))
        return e

    order, seen = [], set()
    for i0 in range(n):
        stack, i = [], i0
        while i != -1 and i not in seen:
            stack.append(i)
            i = mdl['parent'][i]
        for k in reversed(stack):
            if k not in seen:
                seen.add(k)
                order.append(k)
    for i in order:
        node_obj[i] = make_node(i)
    if scale != 1.0:
        for i in range(n):
            o = node_obj[i]
            if o.get('edm_new_anim'):
                m = o.matrix_parent_inverse.copy()
                m.translation *= scale
                o.matrix_parent_inverse = m
            else:
                m = o.matrix_basis.copy()
                m.translation *= scale
                o.matrix_basis = m

    for pi, part in enumerate(mdl['parts']):
        node = part['node']
        if not (0 <= node < n):
            report['skipped_parts'] += 1
            continue
        res = _build_part_mesh('%03d_part%03d' % (node, pi), mdl, part, scale)
        if res is None:
            report['skipped_parts'] += 1
            continue
        mesh, flipped = res
        report['flipped'] += 1 if flipped else 0
        if 0 <= part['material'] < len(mats):
            mesh.materials.append(mats[part['material']])
        ob = bpy.data.objects.new(mesh.name, mesh)
        coll.objects.link(ob)
        ob.parent = node_obj[node]
        ob['mdl_part_index'] = pi
        ob['mdl_material_index'] = part['material']
        report['parts'] += 1
    context.scene.frame_set(100)

    txt = bpy.data.texts.new('MDL_Import_Report')
    txt.write('MDL: %s (%s)\nnos: %d  partes: %d (ignoradas %d, faces reordenadas pela normal: %d)\n'
              'animacoes (pivos): %d  args %d..%d\n\n' % (
                  os.path.basename(filepath), mdl['name'], n, report['parts'], report['skipped_parts'],
                  report['flipped'], report['anims'], first_arg, arg_counter - 1))
    for w in report['warnings'][:200]:
        txt.write('AVISO: %s\n' % w)
    txt.write('\nTABELA DE ARGUMENTOS (arg sequencial -> variavel original do simulador)\n'
              'Troque edm_anim_arg de cada pivo pelo argumento real do DCS.\n')
    for arg, name, kind, var, units, code in report['table']:
        txt.write('arg %3d | %-14s | %s | %s | %s\n' % (arg, name, kind, (var or code or '-').replace('\n', ' ')[:70],
                                                       units))
    return report
