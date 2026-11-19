"""Leitor de .mdl do FSX / P3D / MSFS 2020 (formato RIFF 'MDLX', sem criptografia).

Python puro + numpy (sem bpy): pode ser testado fora do Blender.
Tudo fica nas coordenadas ORIGINAIS do MDL (x direita, y cima, z frente,
mao esquerda, matrizes em convencao de LINHA com translacao na 4a linha).
A conversao para os eixos do EDM/Blender e feita em import_mdl.py.
"""
import struct

import numpy as np


class MdlError(Exception):
    pass


def _chunks(d, off, end):
    while off + 8 <= end:
        tag = d[off:off + 4].decode('latin1')
        sz = struct.unpack_from('<I', d, off + 4)[0]
        if off + 8 + sz > len(d):
            raise MdlError('chunk %r em %d passa do fim do arquivo' % (tag, off))
        yield tag, off + 8, sz
        off += 8 + sz


def _cstr(b):
    return bytes(b).split(b'\0')[0].decode('latin1')


def read_mdl(path):
    with open(path, 'rb') as f:
        d = f.read()
    if d[:4] != b'RIFF' or d[8:12] != b'MDLX':
        raise MdlError('Nao e um MDL (RIFF/MDLX). Arquivos MDL criptografados ou de outro formato nao sao suportados.')
    top = {t: (o, s) for t, o, s in _chunks(d, 12, len(d))}
    if 'MDLD' not in top:
        raise MdlError('chunk MDLD ausente')
    mo, ms = top['MDLD']
    c = {}
    for t, o, s in _chunks(d, mo, mo + ms):
        c.setdefault(t, (o, s))
    for need in ('TEXT', 'MATE', 'INDE', 'VERB', 'TRAN', 'SCEN', 'AMAP', 'SGAL', 'SGVL', 'LODT'):
        if need not in c:
            raise MdlError('chunk %s ausente' % need)
    m = {'name': ''}
    if 'MDLN' in top:
        m['name'] = _cstr(d[top['MDLN'][0]:top['MDLN'][0] + top['MDLN'][1]])
    if 'BBOX' in top:
        o, s = top['BBOX']
        m['bbox'] = struct.unpack_from('<6f', d, o)
    o, s = c['TEXT']
    m['textures'] = [_cstr(d[o + 64 * i:o + 64 * i + 64]) for i in range(s // 64)]
    o, s = c['MATE']
    m['materials'] = [struct.unpack_from('<30I', d, o + 120 * i) for i in range(s // 120)]
    o, s = c['INDE']
    m['indices'] = np.frombuffer(d, dtype='<u2', count=s // 2, offset=o)
    o, s = c['VERB']
    vb = []
    for t, oo, ss in _chunks(d, o, o + s):
        if t == 'VERT':
            vb.append(np.frombuffer(d, dtype='<f4', count=ss // 4, offset=oo).reshape(-1, 8))
    m['vertex_buffers'] = vb                      # x y z nx ny nz u v
    o, s = c['TRAN']
    m['matrices'] = [np.frombuffer(d, dtype='<f4', count=16, offset=o + 64 * i).reshape(4, 4).astype(float)
                     for i in range(s // 64)]
    o, s = c['SCEN']
    n = s // 8
    m['scene'] = [struct.unpack_from('<hhI', d, o + 8 * i) for i in range(n)]   # (filho, irmao, offset)
    o, s = c['AMAP']
    m['amap'] = [struct.unpack_from('<II', d, o + 8 * i) for i in range(n)]    # (tipo 1=estatico 2=animado, idx TRAN)

    def arr(tag):
        oo, ss = c[tag]
        return struct.unpack_from('<%dh' % (ss // 2), d, oo)
    m['sg_anim'] = arr('SGAL')
    m['sg_vis'] = arr('SGVL')
    parent = [-1] * n
    stack = [(0, -1)]
    while stack:
        i, p = stack.pop()
        while i != -1:
            parent[i] = p
            ch = m['scene'][i][0]
            if ch != -1:
                stack.append((ch, i))
            i = m['scene'][i][1]
    m['parent'] = parent
    o, s = c['LODT']
    parts = []
    for t, oo, ss in _chunks(d, o, o + s):
        if t == 'LODE':
            for t2, o2, s2 in _chunks(d, oo + 4, oo + ss):
                if t2 == 'PART' and s2 >= 36:
                    f = struct.unpack_from('<9i', d, o2)
                    parts.append({'node': f[1], 'material': f[2], 'vbuf': f[3], 'base': f[4], 'nverts': f[5],
                                  'istart': f[6], 'icount': f[7], 'raw': f})
            break
    m['parts'] = parts
    vis = []
    if 'VISL' in c:
        o, s = c['VISL']
        for t, oo, ss in _chunks(d, o, o + s):
            if t == 'VISC':
                vis.append(_cstr(d[oo:oo + ss]))
    m['vis_conditions'] = vis
    m['animations'] = _read_anims(d, c) if 'ANIB' in c else {}
    return m


def _read_anims(d, c):
    """{id: {'kind': 'ROT'|'POS', 'keys': [(t, valor)], 'var','units','code','duration'}}"""
    o, s = c['ANIB']
    base = o
    if d[base:base + 4] != b'RIFF':
        return {}
    rs = struct.unpack_from('<I', d, base + 4)[0]
    out = {}
    xanl = None
    i = base + 8
    end = base + 8 + rs
    while i + 8 <= end:
        t = d[i:i + 4]
        sz = struct.unpack_from('<I', d, i + 4)[0]
        if t == b'XANL':
            xanl = (i + 8, i + 8 + sz)
            break
        i += 8 + sz
    if not xanl:
        return {}
    i, e = xanl
    while i + 8 <= e:
        if d[i:i + 4] != b'XANI':
            break
        sz = struct.unpack_from('<I', d, i + 4)[0]
        o2, e2 = i + 8, i + 8 + sz
        i += 8 + sz
        dur = struct.unpack_from('<f', d, o2 + 16)[0]
        q = o2 + 16 + 4 + 16 + 9
        var = units = code = ''
        while q + 8 <= e2:
            t = d[q:q + 4]
            ssz = struct.unpack_from('<I', d, q + 4)[0]
            pl = d[q + 8:q + 8 + ssz]
            if t == b'XAPS':
                parts = _cstr(pl).split('#')
                var = parts[0]
                units = parts[1] if len(parts) > 1 else ''
            elif t == b'XAPC':
                code = _cstr(pl)
            elif t == b'XANS':
                kind_code, aid, sdur = struct.unpack_from('<IIf', pl, 0)
                keys = []
                r = 12
                while r + 8 <= len(pl):
                    kt = pl[r:r + 4]
                    ks = struct.unpack_from('<I', pl, r + 4)[0]
                    kp = pl[r + 8:r + 8 + ks]
                    if kt == b'XANK':
                        ktype = kp[0]
                        tt = struct.unpack_from('<f', kp, 1)[0]
                        if ktype == 4 and ks >= 21:
                            keys.append((tt, struct.unpack_from('<4f', kp, 5)))
                        elif ktype == 3 and ks >= 17:
                            keys.append((tt, struct.unpack_from('<3f', kp, 5)))
                    r += 8 + ks
                out[aid] = {'kind': 'ROT' if kind_code == 0 else ('POS' if kind_code == 2 else 'K%d' % kind_code),
                            'keys': keys, 'var': var, 'units': units, 'code': code,
                            'duration': sdur, 'xani_duration': dur}
            q += 8 + ssz
    return out
