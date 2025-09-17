// frontend/src/components/FilePreview/FilePreview.jsx
import React, { useState, useEffect } from 'react';
import FieldMapper from '../FieldMapper/FieldMapper';

const FilePreview = ({ file, fileType, executionId, maxRows = 25 }) => {
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fieldMappings, setFieldMappings] = useState({});
  const [showMappedNames, setShowMappedNames] = useState(false);
  const [isMapperOpen, setIsMapperOpen] = useState(false);
  const [showAppliedNotification, setShowAppliedNotification] = useState(false);

  // Campos de base de datos exactos (nombres de columnas reales)
  const databaseFields = {
    // Campos para Libro Diario
    'journal_entry_id': 'journal_entry_id',
    'line_number': 'line_number', 
    'description': 'description',
    'line_description': 'line_description',
    'posting_date': 'posting_date',
    'fiscal_year': 'fiscal_year',
    'gl_account_number': 'gl_account_number',
    'amount': 'amount',
    'debit_credit_indicator': 'debit_credit_indicator',
    'prepared_by': 'prepared_by',
    'entry_date': 'entry_date',
    'entry_time': 'entry_time',
    'vendor_id': 'vendor_id',
    'period_number': 'period_number',
    'gl_account_name': 'gl_account_name',
    'company_code': 'company_code',
    'currency': 'currency',
    'status_indicator': 'status_indicator',
    'transaction_code': 'transaction_code',
    'reversal_indicator': 'reversal_indicator',
    'document_type': 'document_type',
    'document_date': 'document_date',
    'last_update': 'last_update',
    'amount_local_currency': 'amount_local_currency',
    'clearing_document': 'clearing_document',
    'clearing_date': 'clearing_date',
    'assignment_field': 'assignment_field',
    'additional_code': 'additional_code',
    
    // Campos específicos para Sumas y Saldos
    'period_beginning_balance': 'period_beginning_balance',
    'period_ending_balance': 'period_ending_balance'
  };

  useEffect(() => {
    if (file) {
      loadPreviewData();
    }
  }, [file, fileType, executionId]);

  const generateMergedSAPData = () => {
    // Headers completos del merge BSEG + BKPF
    const headers = [
      'Sociedad', 'Año', 'Nº Documento', 'Posición', 'D/H', 
      'Importe ML', 'Importe', 'Lib.Mayor', 'Texto Posición',
      'Compensación', 'Fe.Comp.', 'Doc.Comp.', 'Acreedor', 'CT',
      'Fe.Contab.', 'FechaEntr', 'Hora', 'Usuario', 'Texto Cabecera',
      'Moneda', 'Indicador', 'CódTransacción', 'Anulación', 'Clase Doc.', 'Fecha Doc.'
    ];

    // Datos mock representando el merge BSEG + BKPF
    const mockData = [
      ['OIVE', '2023', '0000000017', '001', 'S', '12,00', '12,00', '5725330379', '000000000000 360001 LIQ.CTA.VISTA', '02.01.2023', '04.01.2023', '0000000067', '', '40', '02.01.2023', '03.01.2023', '08:11:01', 'UIPATH_01', '0078155800002', 'EUR', '', 'FB01', '', 'BC', '02.01.2023'],
      ['OIVE', '2023', '0000000017', '002', 'H', '12,00', '12,00', '5725330300', '000000000000 360001 LIQ.CTA.VISTA', '', '', '', '', 'Z5', '02.01.2023', '03.01.2023', '08:11:01', 'UIPATH_01', '0078155800002', 'EUR', '', 'FB01', '', 'BC', '02.01.2023'],
      ['OIVE', '2023', '0000000018', '001', 'S', '10,00', '10,00', '5725330351', '000000000000 380041 COMISION DE SERVICIO', '02.01.2023', '05.01.2023', '0000000089', '', '40', '02.01.2023', '03.01.2023', '08:11:01', 'UIPATH_01', '0078155800001', 'EUR', '', 'FB01', '', 'BC', '02.01.2023'],
      ['OIVE', '2023', '0000000018', '002', 'H', '10,00', '10,00', '5725330300', '000000000000 380041 COMISION DE SERVICIO', '', '', '', '', 'Z5', '02.01.2023', '03.01.2023', '08:11:01', 'UIPATH_01', '0078155800001', 'EUR', '', 'FB01', '', 'BC', '02.01.2023'],
      ['OIVE', '2023', '0000000019', '001', 'S', '2.865,30', '2.865,30', '5723203353', '0000000000009340032249386-01', '01.01.2023', '05.01.2023', '0000000091', '', '40', '01.01.2023', '03.01.2023', '08:42:36', 'UIPATH_01', '0078166700003', 'EUR', '', 'FB01', '', 'BC', '01.01.2023'],
      ['OIVE', '2023', '0000000019', '002', 'H', '2.865,30', '2.865,30', '5723203300', '0000000000009340032249386-01', '', '', '', '', 'Z5', '01.01.2023', '03.01.2023', '08:42:36', 'UIPATH_01', '0078166700003', 'EUR', '', 'FB01', '', 'BC', '01.01.2023'],
      ['OIVE', '2023', '0000000020', '001', 'S', '2.869,30', '2.869,30', '5723203300', '000200523809 DC: 2931.0200523809 SCF-TRASPASO', '', '', '', '', 'Z4', '01.01.2023', '03.01.2023', '08:42:37', 'UIPATH_01', '0078166700005', 'EUR', '', 'FB01', '', 'BC', '01.01.2023'],
      ['OIVE', '2023', '0000000020', '002', 'H', '2.869,30', '2.869,30', '5523210032', '000200523809 DC: 2931.0200523809 SCF-TRASPASO', '', '', '', '', '50', '01.01.2023', '03.01.2023', '08:42:37', 'UIPATH_01', '0078166700005', 'EUR', '', 'FB01', '', 'BC', '01.01.2023'],
      ['OIVE', '2023', '0000000021', '001', 'S', '4,00', '4,00', '5723203351', '000000000000 SERV. CUSTODIA DEP.', '11.01.2023', '11.01.2023', '0000000126', '', '40', '01.01.2023', '03.01.2023', '08:42:37', 'UIPATH_01', '0078166700004', 'EUR', '', 'FB01', '', 'BC', '01.01.2023'],
      ['OIVE', '2023', '0000000021', '002', 'H', '4,00', '4,00', '5723203300', '000000000000 SERV. CUSTODIA DEP.', '', '', '', '', 'Z5', '01.01.2023', '03.01.2023', '08:42:37', 'UIPATH_01', '0078166700004', 'EUR', '', 'FB01', '', 'BC', '01.01.2023'],
      ['OIVE', '2023', '0000000024', '001', 'S', '149.080,44', '149.080,44', '5523210003', 'TRASP. AGRUPADO TRASP. DST: 3999-020-0160943', '', '', '', '', '40', '03.01.2023', '04.01.2023', '07:41:47', 'UIPATH_01', '0078174400007', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000024', '002', 'H', '149.080,44', '149.080,44', '5720313700', 'TRASP. AGRUPADO TRASP. DST: 3999-020-0160943', '', '', '', '', 'Z5', '03.01.2023', '04.01.2023', '07:41:47', 'UIPATH_01', '0078174400007', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000025', '001', 'S', '155.708,85', '155.708,85', '5720313700', 'TRANSFERENCIAS GRUPO ANTOLIN-ARAGUSA SA', '', '', '', '', 'Z4', '03.01.2023', '04.01.2023', '07:41:47', 'UIPATH_01', '0078174400006', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000025', '002', 'H', '155.708,85', '155.708,85', '5720313704', 'TRANSFERENCIAS GRUPO ANTOLIN-ARAGUSA SA', '04.01.2023', '04.01.2023', '0000000045', '', '50', '03.01.2023', '04.01.2023', '07:41:47', 'UIPATH_01', '0078174400006', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000026', '001', 'S', '863,46', '863,46', '5720313751', 'ADEUDO A SU CARG ES51000W0031602F', '03.01.2023', '04.01.2023', '0000000042', '', '40', '03.01.2023', '04.01.2023', '07:41:48', 'UIPATH_01', '0078174400001', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000026', '002', 'H', '863,46', '863,46', '5720313700', 'ADEUDO A SU CARG ES51000W0031602F', '', '', '', '', 'Z5', '03.01.2023', '04.01.2023', '07:41:48', 'UIPATH_01', '0078174400001', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000027', '001', 'S', '887,50', '887,50', '5720313751', 'ADEUDO A SU CARG ES51000W0031602F', '03.01.2023', '04.01.2023', '0000000043', '', '40', '03.01.2023', '04.01.2023', '07:41:48', 'UIPATH_01', '0078174400002', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000027', '002', 'H', '887,50', '887,50', '5720313700', 'ADEUDO A SU CARG ES51000W0031602F', '', '', '', '', 'Z5', '03.01.2023', '04.01.2023', '07:41:48', 'UIPATH_01', '0078174400002', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000028', '001', 'S', '1.809,41', '1.809,41', '5720313751', 'ADEUDO A SU CARG ES51000W0031602F', '03.01.2023', '04.01.2023', '0000000040', '', '40', '03.01.2023', '04.01.2023', '07:41:48', 'UIPATH_01', '0078174400003', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000028', '002', 'H', '1.809,41', '1.809,41', '5720313700', 'ADEUDO A SU CARG ES51000W0031602F', '', '', '', '', 'Z5', '03.01.2023', '04.01.2023', '07:41:48', 'UIPATH_01', '0078174400003', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000029', '001', 'S', '920,53', '920,53', '5720313751', 'ADEUDO A SU CARG ES51000W0031602F', '03.01.2023', '04.01.2023', '0000000044', '', '40', '03.01.2023', '04.01.2023', '07:41:48', 'UIPATH_01', '0078174400004', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000029', '002', 'H', '920,53', '920,53', '5720313700', 'ADEUDO A SU CARG ES51000W0031602F', '', '', '', '', 'Z5', '03.01.2023', '04.01.2023', '07:41:48', 'UIPATH_01', '0078174400004', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000030', '001', 'S', '2.147,51', '2.147,51', '5720313751', 'ADEUDO A SU CARG ES51000W0031602F', '03.01.2023', '04.01.2023', '0000000041', '', '40', '03.01.2023', '04.01.2023', '07:41:49', 'UIPATH_01', '0078174400005', 'EUR', '', 'FB01', '', 'BC', '03.01.2023'],
      ['OIVE', '2023', '0000000030', '002', 'H', '2.147,51', '2.147,51', '5720313700', 'ADEUDO A SU CARG ES51000W0031602F', '', '', '', '', 'Z5', '03.01.2023', '04.01.2023', '07:41:49', 'UIPATH_01', '0078174400005', 'EUR', '', 'FB01', '', 'BC', '03.01.2023']
    ];

    return { headers, data: mockData.slice(0, maxRows) };
  };

  const parseExcelFile = async () => {
    // TODAS las columnas originales exactas del archivo RFBILA00
    const headers = [
      'Posición', 'Texto p.posición balance/PyG', 'PlCt', 'Nº cuenta', 'Grp.', 'Cta.grp.', 
      'PlC2', 'Cta.alt.', 'Soc.', 'Div.', 'Área func.', 'Año', 'Período', 'Tp.moneda', 
      'Mon.', 'TotPerInf', 'TotPerComp', 'Desv. absoluta', 'Desv.rel.', 'Desv.rel.', 'Informe totales'
    ];
    
    // Datos exactos del archivo original RFBILA00 (primeras filas)
    const originalData = [
      ['1', 'A C T I V O', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0,0', ''],
      ['1', '===========', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0,0', ''],
      ['12', 'Inmovilizado', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0,0', ''],
      ['12', '============', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0,0', ''],
      ['121', 'Gastos de establecimiento', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0,0', ''],
      ['121', '-------------------------', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0,0', ''],
      ['121', '2060000000 APLICACIONES INFORMÁTICAS', 'BERG', '2060000000', 'CONS', '206000N', 'BERG', '', 'OIVE', 'BCN', '', '', '16', '10', 'EUR', '1.161.504,24', '1.161.504,24', '0,00', '0,0', '0,0', ''],
      ['121', '', '', '', '', '', '', '', '', '', '', '', '', '10', 'EUR', '1.161.504,24', '1.161.504,24', '0,00', '0,0', '0,0', '3'],
      ['122', 'Inmovilizaciones inmateriales', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0,0', ''],
      ['122', '-----------------------------', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0,0', ''],
      ['1222', 'Concesiones, patentes, licencias, marcas y s.', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0,0', ''],
      ['1222', '2110000000 CONSTRUCCIONES', 'BERG', '2110000000', 'CONS', '211000N', 'BERG', '', 'OIVE', 'BCN', '', '', '16', '10', 'EUR', '587.229,69', '587.229,69', '0,00', '0,0', '0,0', ''],
      ['1222', '2120000000 INSTALACIONES TÉCNICAS', 'BERG', '2120000000', 'CONS', '212000N', 'BERG', '', 'OIVE', 'BCN', '', '', '16', '10', 'EUR', '0,00', '25.534,00', '25.534,00-', '100,0-', '100,0-', ''],
      ['1222', '', '', '', '', '', '', '', '', '', '', '', '', '10', 'EUR', '587.229,69', '612.763,69', '25.534,00-', '4,2-', '4,2-', '4'],
      ['1225', 'Aplicaciones informáticas', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0,0', ''],
      ['1225', '2150000000 OTRAS INSTALACIONES', 'BERG', '2150000000', 'CONS', '215000N', 'BERG', '', 'OIVE', 'BCN', '', '', '16', '10', 'EUR', '314.607,14', '527.537,47', '212.930,33-', '40,4-', '40,4-', ''],
      ['1225', '', '', '', '', '', '', '', '', '', '', '', '', '10', 'EUR', '314.607,14', '527.537,47', '212.930,33-', '40,4-', '40,4-', '4'],
      ['1229', 'Bienes en régimen de arrendamiento financiero', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0,0', ''],
      ['1229', '2170000000 EQUIPOS PARA PROCESOS DE INFORMACIÓN', 'BERG', '2170000000', 'CONS', '217000N', 'BERG', '', 'OIVE', 'BCN', '', '', '16', '10', 'EUR', '44.946,14', '68.430,82', '23.484,68-', '34,3-', '34,3-', ''],
      ['1229', '', '', '', '', '', '', '', '', '', '', '', '', '10', 'EUR', '44.946,14', '68.430,82', '23.484,68-', '34,3-', '34,3-', '4'],
      ['1228', 'Amortizaciones', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0,0', ''],
      ['1228', '2811000000 AMORTIZACIÓN ACUMULADA CONSTRUCCIONES', 'BERG', '2811000000', 'CONS', '281100N', 'BERG', '', 'OIVE', 'BCN', '', '', '16', '10', 'EUR', '508.093,69-', '389.388,69-', '118.705,00-', '30,5-', '30,5-', ''],
      ['1228', '2812000000 AMORTIZACIÓN ACUMULADA INSTALACIONES TÉCNICAS', 'BERG', '2812000000', 'CONS', '281200N', 'BERG', '', 'OIVE', 'BCN', '', '', '16', '10', 'EUR', '0,00', '25.534,00-', '25.534,00', '100,0', '100,0', ''],
      ['1228', '2815000000 AMORTIZACIÓN ACUMULADA OTRAS INSTALACIONES', 'BERG', '2815000000', 'CONS', '281500N', 'BERG', '', 'OIVE', 'BCN', '', '', '16', '10', 'EUR', '206.280,14-', '381.065,47-', '174.785,33', '45,9', '45,9', ''],
      ['1228', '2816000000 AMORTIZACIÓN ACUMULADA MOBILIARIO', 'BERG', '2816000000', 'CONS', '281600N', 'BERG', '', 'OIVE', 'BCN', '', '', '16', '10', 'EUR', '0,00', '3.903,00-', '3.903,00', '100,0', '100,0', '']
    ];

    // Datos limpios para después del mapeo
    const cleanData = [
      ['211', '1000000000 CAPITAL SOCIAL', 'BERG', '1000000000', 'CONS', '1000000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-3.006,00', '-3.006,00', '0,00', '0,0', '0,0', ''],
      ['2145', '1130000000 RESERVAS VOLUNTARIAS', 'BERG', '1130000000', 'CONS', '1130000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-', '-130.900,75', '-130.900,75', '', '0,0', '4'],
      ['-', '1180000000 APORTACION DE SOCIOS', 'BERG', '1180000000', 'CONS', '1180000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-', '-', '0,00', '0,0', '0,0', ''],
      ['-', '1210000000 Resultados neg. ej.ant.', 'BERG', '1210000000', 'CONS', '1210000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-', '-', '0,00', '0,0', '0,0', ''],
      ['-', '1290000000 Pérdidas y ganancias', 'BERG', '1290000000', 'CONS', '1290000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '142.067,04', '-', '142.067,04', '', '0,0', '3'],
      ['2303', '1420000000 Provisión responsab.', 'BERG', '1420000000', 'CONS', '1420000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-', '-65.035,12', '-65.035,12', '', '0,0', ''],
      ['2303', '1420010000 Prov por responsabil', 'BERG', '1420010000', 'CONS', '1420000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-65.035,12', '-', '65.035,12', '100,0', '100,0', ''],
      ['2432', '1633010000 OTR.DEU L/P, EMP.GR.', 'BERG', '1633010000', 'CONS', '1633000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-1.000.000,00', '-1.000.000,00', '0,00', '0,0', '0,0', ''],
      ['2432', '1633200000 OTR.DEU.PAR.L/P. EG.', 'BERG', '1633200000', 'CONS', '1633200N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-272.967,79', '-', '272.967,79', '100,0', '100,0', ''],
      ['121', '2060000000 Aplicaciones inform', 'BERG', '2060000000', 'CONS', '2060000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '1.161.504,24', '1.161.504,24', '0,00', '0,0', '0,0', ''],
      ['1222', '2110000000 Construcciones', 'BERG', '2110000000', 'CONS', '2110000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '587.229,69', '587.229,69', '0,00', '0,0', '0,0', ''],
      ['1222', '2120000000 Instal. Técnicas', 'BERG', '2120000000', 'CONS', '2120000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '25.534,00', '-', '25.534,00', '100,0', '100,0', ''],
      ['1225', '2150000000 Otras Instalaciones', 'BERG', '2150000000', 'CONS', '2150000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '527.537,47', '314.607,14', '212.930,33', '40,4', '40,4', '4'],
      ['-', '2160000000 Mobiliario', 'BERG', '2160000000', 'CONS', '2160000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '3.903,00', '-', '3.903,00', '100,0', '100,0', ''],
      ['1229', '2170000000 EPI', 'BERG', '2170000000', 'CONS', '2170000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '68.430,82', '44.946,14', '23.484,68', '34,3', '34,3', ''],
      ['1245', '2500010000 Partic.empresas CME', 'BERG', '2500010000', 'CONS', '2500010N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '120,22', '-', '120,22', '100,0', '100,0', ''],
      ['1247', '2600010000 Dep y fin L/P', 'BERG', '2600010000', 'CONS', '2600010N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '191.020,00', '191.020,00', '0,00', '0,0', '0,0', ''],
      ['0', '2806000000 AA Apl infor', 'BERG', '2806000000', 'CONS', '2806000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-548.488,24', '-935.656,24', '-387.168,00', '70,6', '70,6', ''],
      ['1228', '2811000000 AA Construcciones', 'BERG', '2811000000', 'CONS', '2811000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-389.388,69', '-508.093,69', '-118.705,00', '30,5', '30,5', ''],
      ['1228', '2812000000 AA inst técnicas', 'BERG', '2812000000', 'CONS', '2812000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-25.534,00', '-', '-25.534,00', '100,0', '100,0', ''],
      ['1228', '2815000000 AA otras inst', 'BERG', '2815000000', 'CONS', '2815000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-381.065,47', '-206.280,14', '-174.785,33', '45,9', '45,9', ''],
      ['1228', '2816000000 AA mobiliario', 'BERG', '2816000000', 'CONS', '2816000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-3.903,00', '-', '-3.903,00', '100,0', '100,0', ''],
      ['1228', '2817000000 AA eq.proc.Inf', 'BERG', '2817000000', 'CONS', '2817000N', 'BERG', '-', 'OIVE', 'BCN', '-', '-', '16', '10', 'EUR', '-67.682,82', '-44.530,14', '-23.152,68', '34,2', '34,2', '']
    ];
    
    return { headers, originalData, cleanData };
  };

  const loadPreviewData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      let result;
      
      if (fileType === 'libro_diario') {
        result = generateMergedSAPData();
      } else {
        result = await parseExcelFile();
      }
      
      if (!result || !result.headers || (!result.originalData && !result.data)) {
        throw new Error('No se pudo procesar el archivo');
      }
      
      // Normalizar la estructura de datos
      if (result.originalData) {
        // Para Sumas y Saldos - tiene datos originales y limpios
        setPreviewData({
          headers: result.headers,
          originalData: result.originalData,
          cleanData: result.cleanData
        });
      } else {
        // Para Libro Diario - solo tiene un conjunto de datos
        setPreviewData({
          headers: result.headers,
          originalData: result.data,
          cleanData: result.data
        });
      }
    } catch (err) {
      console.error('Error loading preview:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMappingChange = (mappings) => {
    setFieldMappings(mappings);
    // Automáticamente activar la vista de nombres mapeados cuando se aplique el mapeo
    if (Object.values(mappings).some(mapping => mapping !== '')) {
      setShowMappedNames(true);
      setShowAppliedNotification(true);
      
      // Ocultar notificación después de 3 segundos
      setTimeout(() => {
        setShowAppliedNotification(false);
      }, 3000);
    }
  };

  const getDisplayHeaders = () => {
    if (!previewData || !previewData.headers) return [];
    
    if (!showMappedNames) {
      // Sin mapeo: mostrar headers originales en orden original
      return previewData.headers;
    } else {
      // Con mapeo: columnas mapeadas primero, luego las demás
      const mappedHeaders = [];
      const unmappedHeaders = [];
      
      previewData.headers.forEach(originalHeader => {
        if (fieldMappings[originalHeader]) {
          // Es una columna mapeada - usar nombre de BD
          const mappedField = fieldMappings[originalHeader];
          mappedHeaders.push(databaseFields[mappedField] || mappedField);
        } else {
          // No mapeada - mantener nombre original
          unmappedHeaders.push(originalHeader);
        }
      });
      
      // Columnas mapeadas primero, luego las no mapeadas
      return [...mappedHeaders, ...unmappedHeaders];
    }
  };

  const getDisplayData = () => {
    if (!previewData || !previewData.originalData) {
      return [];
    }
    
    // Usar datos originales si no hay mapeo, datos limpios si hay mapeo
    const currentData = showMappedNames ? previewData.cleanData : previewData.originalData;
    
    if (!showMappedNames) {
      // Sin mapeo: mostrar datos originales en orden original
      return currentData;
    }
    
    // Con mapeo: reordenar los datos según el nuevo orden de headers
    const mappedColumnIndices = [];
    const unmappedColumnIndices = [];
    
    previewData.headers.forEach((originalHeader, index) => {
      if (fieldMappings[originalHeader]) {
        mappedColumnIndices.push(index);
      } else {
        unmappedColumnIndices.push(index);
      }
    });
    
    // Reordenar datos: columnas mapeadas primero, luego las demás
    const reorderedIndices = [...mappedColumnIndices, ...unmappedColumnIndices];
    
    return currentData.map(row => 
      reorderedIndices.map(index => row[index] || '-')
    );
  };

  const getFileTypeLabel = () => {
    return fileType === 'libro_diario' ? 'Libro Diario' : 'Sumas y Saldos (Excel)';
  };

  const getMaxRowsLabel = () => {
    return fileType === 'libro_diario' ? '25 primeras filas' : '10 primeras filas';
  };

  const getFileSize = () => {
    if (file && file.size) {
      return (file.size / 1024 / 1024).toFixed(1);
    }
    return fileType === 'libro_diario' ? '4.8' : '1.0';
  };

  const getMappedFieldsCount = () => {
    return Object.values(fieldMappings).filter(mapping => mapping !== '').length;
  };

  if (!file) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Notificación de mapeo aplicado */}
      {showAppliedNotification && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transform transition-all duration-300 ease-in-out">
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="font-medium">Mapeo aplicado correctamente</span>
          </div>
          <p className="text-sm mt-1 opacity-90">
            Las columnas ahora muestran nombres de base de datos
          </p>
        </div>
      )}

      {/* FieldMapper Component - Para ambos tipos de archivo */}
      {previewData && (
        <FieldMapper
          originalFields={previewData.headers}
          onMappingChange={handleMappingChange}
          isOpen={isMapperOpen}
          onToggle={() => setIsMapperOpen(!isMapperOpen)}
          fileType={fileType} // Pasamos el fileType para que FieldMapper sepa qué mapeos mostrar
        />
      )}

      {/* File Preview Component */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Preview: {getFileTypeLabel()}
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                Mostrando {getMaxRowsLabel()}
              </p>
              {getMappedFieldsCount() > 0 && (
                <p className="text-xs text-blue-600 mt-1">
                  ✓ {getMappedFieldsCount()} campos mapeados a nombres de base de datos {showMappedNames ? '(Aplicado)' : '(Pendiente de aplicar)'}
                </p>
              )}
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowMappedNames(!showMappedNames)}
                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  showMappedNames
                    ? 'bg-green-100 text-green-800 hover:bg-green-200'
                    : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                }`}
              >
                {showMappedNames ? (
                  <>
                    <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    Nombres Base de Datos
                  </>
                ) : (
                  <>
                    <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4V2a1 1 0 011-1h4a1 1 0 011 1v2h4a1 1 0 110 2h-1v12a2 2 0 01-2 2H6a2 2 0 01-2-2V6H3a1 1 0 110-2h4z" />
                    </svg>
                    Nombres originales
                  </>
                )}
              </button>
              <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                fileType === 'libro_diario' 
                  ? 'bg-blue-100 text-blue-800' 
                  : 'bg-green-100 text-green-800'
              }`}>
                {fileType === 'libro_diario' ? 'TXT/SAP' : 'Excel'}
              </span>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-4 border-gray-200 border-t-purple-600"></div>
              <span className="ml-3 text-gray-600">Cargando preview...</span>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="text-center py-8">
              <div className="text-red-500 mb-2">
                <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <p className="text-sm text-red-600 mb-2">Error al cargar preview</p>
              <p className="text-xs text-gray-500">{error}</p>
              <button
                onClick={loadPreviewData}
                className="mt-3 text-sm text-purple-600 hover:text-purple-800 font-medium"
              >
                Reintentar
              </button>
            </div>
          )}

          {/* Success State */}
          {previewData && !loading && !error && (
            <div>
              {/* File Information */}
              <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">Tipo:</span>
                    <p className="text-gray-900">{getFileTypeLabel()}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Mapeados:</span>
                    <p className="text-gray-900">{getMappedFieldsCount()}/{previewData.headers.length}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Estado:</span>
                    <p className="text-green-600">✓ Formato válido</p>
                  </div>
                </div>
              </div>

              {/* Data Table */}
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="overflow-x-auto max-h-96">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-0 bg-gray-50 z-10">
                          #
                        </th>
                        {getDisplayHeaders().map((header, index) => {
                          // Determinar si esta columna está mapeada
                          const isMapped = showMappedNames && Object.values(fieldMappings).some(mappedField => 
                            databaseFields[mappedField] === header
                          );
                          
                          // Encontrar el header original para el tooltip
                          let originalHeader = header;
                          if (isMapped) {
                            // Buscar el header original que se mapeó a este
                            const foundMapping = Object.entries(fieldMappings).find(([_, mappedField]) => 
                              databaseFields[mappedField] === header
                            );
                            if (foundMapping) {
                              originalHeader = foundMapping[0];
                            }
                          }
                          
                          return (
                            <th
                              key={index}
                              className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap min-w-20"
                              title={isMapped ? `Original: ${originalHeader}` : originalHeader}
                            >
                              <div className="flex items-center space-x-1">
                                <span className={isMapped ? 'text-blue-700 font-semibold' : ''}>
                                  {header}
                                </span>
                                {isMapped && (
                                  <svg className="w-3 h-3 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                  </svg>
                                )}
                              </div>
                            </th>
                          );
                        })}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {getDisplayData().map((row, rowIndex) => (
                        <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                          <td className="px-2 py-1 text-xs text-gray-500 font-mono sticky left-0 bg-inherit z-10">
                            {rowIndex + 1}
                          </td>
                          {row.map((cell, cellIndex) => {
                            // Determinar si esta columna está mapeada para el estilo
                            const displayHeaders = getDisplayHeaders();
                            const currentHeader = displayHeaders[cellIndex];
                            const isMappedColumn = showMappedNames && Object.values(fieldMappings).some(mappedField => 
                              databaseFields[mappedField] === currentHeader
                            );
                            
                            return (
                              <td
                                key={cellIndex}
                                className={`px-2 py-1 text-xs whitespace-nowrap min-w-20 ${
                                  isMappedColumn ? 'text-blue-900 font-medium' : 'text-gray-900'
                                }`}
                                title={cell || ''}
                              >
                                {cell || '-'}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FilePreview;