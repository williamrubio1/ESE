import copy
import unittest

import pandas as pd

from modules.motor_logico import (
    aplicar_cambios_bc_json,
    aplicar_clasificacion_df_bc,
    aplicar_clasificacion_df_pyp,
)
from modules.tabla_unica_compuestos import aplicar_cambios_compuestos_json
from modules.tabla_unica_pyp import aplicar_sustituciones_pyp_json


def _json_con_servicios(servicios):
    return {
        'usuarios': [
            {
                'numDocumentoIdentificacion': '123',
                'tipoDocumentoIdentificacion': 'CC',
                'fechaNacimiento': '1990-01-01',
                'servicios': servicios,
            }
        ]
    }


class RegresionBCJsonTests(unittest.TestCase):
    def test_consulta_bc_z_pyp_invalido_se_sustituye(self):
        datos = _json_con_servicios(
            {
                'consultas': [
                    {
                        'codConsulta': '890201',
                        'codDiagnosticoPrincipal': 'Z300',
                        'finalidadTecnologiaSalud': '',
                        'causaMotivoAtencion': '',
                    }
                ]
            }
        )

        corregido = aplicar_cambios_bc_json(copy.deepcopy(datos))
        consulta = corregido['usuarios'][0]['servicios']['consultas'][0]

        self.assertEqual(consulta['codDiagnosticoPrincipal'], 'Z718')
        self.assertEqual(consulta['finalidadTecnologiaSalud'], '44')
        self.assertEqual(consulta['causaMotivoAtencion'], '38')

    def test_consulta_bc_trauma_asigna_causa_26(self):
        datos = _json_con_servicios(
            {
                'consultas': [
                    {
                        'codConsulta': '890201',
                        'codDiagnosticoPrincipal': 'S061',
                        'finalidadTecnologiaSalud': '',
                        'causaMotivoAtencion': '',
                    }
                ]
            }
        )

        corregido = aplicar_cambios_bc_json(copy.deepcopy(datos))
        consulta = corregido['usuarios'][0]['servicios']['consultas'][0]

        self.assertEqual(consulta['finalidadTecnologiaSalud'], '44')
        self.assertEqual(consulta['causaMotivoAtencion'], '26')


class RegresionBCDataFrameTests(unittest.TestCase):
    def test_consulta_bc_dataframe_reproduce_logica_json(self):
        df_consultas = pd.DataFrame(
            [
                {
                    'numDocumento_usuario': '123',
                    'tipoDocumento_usuario': 'CC',
                    'consecutivo_consulta': 1,
                    'codConsulta': '890201',
                    'codDiagnosticoPrincipal': 'Z300',
                    'finalidadTecnologiaSalud': '',
                    'causaMotivoAtencion': '',
                }
            ]
        )
        df_procedimientos = pd.DataFrame(columns=['codProcedimiento', 'codDiagnosticoPrincipal', 'finalidadTecnologiaSalud'])
        df_medicamentos = pd.DataFrame(columns=['codDiagnosticoPrincipal'])

        consultas, _, _, cambios = aplicar_clasificacion_df_bc(df_consultas, df_procedimientos, df_medicamentos)
        fila = consultas.iloc[0]

        self.assertEqual(fila['codDiagnosticoPrincipal'], 'Z718')
        self.assertEqual(fila['finalidadTecnologiaSalud'], '44')
        self.assertEqual(fila['causaMotivoAtencion'], '38')
        self.assertTrue(cambios)


class RegresionPyPTests(unittest.TestCase):
    def test_consulta_pyp_json_clasifica_z34(self):
        datos = _json_con_servicios(
            {
                'consultas': [
                    {
                        'codConsulta': '890201',
                        'codDiagnosticoPrincipal': 'Z340',
                        'finalidadTecnologiaSalud': '11',
                        'causaMotivoAtencion': '40',
                    }
                ]
            }
        )

        corregido = aplicar_sustituciones_pyp_json(copy.deepcopy(datos))
        consulta = corregido['usuarios'][0]['servicios']['consultas'][0]

        self.assertEqual(consulta['finalidadTecnologiaSalud'], '23')
        self.assertEqual(consulta['causaMotivoAtencion'], '42')

    def test_procedimiento_pyp_dataframe_997_llena_z012_y_finalidad_14(self):
        df_consultas = pd.DataFrame(columns=['codConsulta', 'codDiagnosticoPrincipal', 'finalidadTecnologiaSalud', 'causaMotivoAtencion'])
        df_procedimientos = pd.DataFrame(
            [
                {
                    'numDocumento_usuario': '123',
                    'tipoDocumento_usuario': 'CC',
                    'consecutivo_procedimiento': 1,
                    'codProcedimiento': '997999',
                    'codDiagnosticoPrincipal': '',
                    'finalidadTecnologiaSalud': '',
                }
            ]
        )

        _, procedimientos, cambios = aplicar_clasificacion_df_pyp(df_consultas, df_procedimientos)
        fila = procedimientos.iloc[0]

        self.assertEqual(fila['codDiagnosticoPrincipal'], 'Z012')
        self.assertEqual(fila['finalidadTecnologiaSalud'], '14')
        self.assertTrue(cambios)


class RegresionCompuestosJsonTests(unittest.TestCase):
    def test_consulta_compuestos_vacia_890203_asigna_z012(self):
        datos = _json_con_servicios(
            {
                'consultas': [
                    {
                        'fechaInicioAtencion': '2026-04-01 08:00',
                        'codConsulta': '890203',
                        'codDiagnosticoPrincipal': '',
                        'finalidadTecnologiaSalud': '',
                        'causaMotivoAtencion': '',
                    }
                ],
                'procedimientos': [],
            }
        )

        corregido = aplicar_cambios_compuestos_json(copy.deepcopy(datos))
        consulta = corregido['usuarios'][0]['servicios']['consultas'][0]

        self.assertEqual(consulta['codDiagnosticoPrincipal'], 'Z012')
        self.assertEqual(consulta['finalidadTecnologiaSalud'], '11')
        self.assertEqual(consulta['causaMotivoAtencion'], '40')

    def test_consulta_compuestos_vacia_890703_asigna_k021(self):
        datos = _json_con_servicios(
            {
                'consultas': [
                    {
                        'fechaInicioAtencion': '2026-04-01 08:00',
                        'codConsulta': '890703',
                        'codDiagnosticoPrincipal': '',
                        'finalidadTecnologiaSalud': '',
                        'causaMotivoAtencion': '',
                    }
                ],
                'procedimientos': [],
            }
        )

        corregido = aplicar_cambios_compuestos_json(copy.deepcopy(datos))
        consulta = corregido['usuarios'][0]['servicios']['consultas'][0]

        self.assertEqual(consulta['codDiagnosticoPrincipal'], 'K021')
        self.assertEqual(consulta['finalidadTecnologiaSalud'], '38')

    def test_procedimiento_compuestos_vacio_en_z258(self):
        datos = _json_con_servicios(
            {
                'consultas': [],
                'procedimientos': [
                    {
                        'fechaInicioAtencion': '2026-04-01 08:00',
                        'codProcedimiento': '993101',
                        'codDiagnosticoPrincipal': '',
                        'finalidadTecnologiaSalud': '',
                    }
                ],
            }
        )

        corregido = aplicar_cambios_compuestos_json(copy.deepcopy(datos))
        proc = corregido['usuarios'][0]['servicios']['procedimientos'][0]

        self.assertEqual(proc['codDiagnosticoPrincipal'], 'Z258')
        self.assertEqual(proc['finalidadTecnologiaSalud'], '14')


if __name__ == '__main__':
    unittest.main()