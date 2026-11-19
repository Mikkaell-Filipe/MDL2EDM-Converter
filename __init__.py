bl_info = {
    'name': 'MDL (FSX/P3D/MSFS) importer for DCS EDM workflow',
    'author': 'Filipe + Claude',
    'version': (0, 1, 0),
    'blender': (4, 2, 0),
    'location': 'File > Import > MDL (.mdl)',
    'description': 'Importa .mdl com pecas separadas e animacao, pronto para exportar com io_scene_edm_custom',
    'category': 'Import-Export',
}

import importlib

import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from . import mdl_reader
from . import import_mdl as _imp


class IMPORT_OT_mdl(bpy.types.Operator, ImportHelper):
    """Importa um .mdl (FSX/P3D/MSFS) com pecas separadas e animacao"""
    bl_idname = 'import_scene.mdl_dcs'
    bl_label = 'Import MDL (for DCS EDM)'
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = '.mdl'
    filter_glob: StringProperty(default='*.mdl', options={'HIDDEN'})
    scale: FloatProperty(name='Escala', default=1.0, min=0.0001, max=1000.0,
                         description='O MDL ja esta em metros; 1.0 mantem o tamanho')
    tex_dir: StringProperty(name='Pasta de texturas', default='',
                            description='Pasta com .dds/.png/.tga do modelo (opcional)')
    first_arg: IntProperty(name='Primeiro argumento', default=0, min=0, max=9999,
                           description='Os pivos recebem args sequenciais a partir deste; troque depois')
    with_anim: BoolProperty(name='Importar animacao', default=True)
    normalize_time: BoolProperty(name='Ultima chave = arg 1', default=True,
                                 description='Normaliza o tempo das chaves de cada animacao para 0..1')
    invert_rot: BoolProperty(name='Inverter sentido das rotacoes', default=False,
                             description='Use se as pecas girarem ao contrario do esperado')
    edm_parent: StringProperty(name='Empty do EDM (opcional)', default='',
                               description='Nome do empty de no de um EDM ja importado sob o qual o MDL sera pendurado')

    def execute(self, context):
        importlib.reload(mdl_reader)
        importlib.reload(_imp)
        try:
            rep = _imp.import_mdl(context, self.filepath, scale=self.scale, tex_dir=self.tex_dir,
                                  first_arg=self.first_arg, with_anim=self.with_anim,
                                  normalize_time=self.normalize_time, edm_parent=self.edm_parent,
                                  invert_rot=self.invert_rot)
        except mdl_reader.MdlError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        self.report({'INFO'}, 'MDL: %d pecas, %d animacoes (veja o Text MDL_Import_Report)' % (rep['parts'], rep['anims']))
        return {'FINISHED'}


def _menu(self, context):
    self.layout.operator(IMPORT_OT_mdl.bl_idname, text='MDL FSX/P3D/MSFS (.mdl) -> DCS')


def register():
    bpy.utils.register_class(IMPORT_OT_mdl)
    bpy.types.TOPBAR_MT_file_import.append(_menu)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(_menu)
    bpy.utils.unregister_class(IMPORT_OT_mdl)
