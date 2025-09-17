// frontend/src/components/FieldMapper/FieldMapper.jsx - Versión compacta
import React, { useState, useEffect } from 'react';

const FieldMapper = ({ originalFields, onMappingChange, isOpen, onToggle, fileType = 'libro_diario' }) => {
  const [fieldMappings, setFieldMappings] = useState({});
  const [searchTerm, setSearchTerm] = useState('');

  // Campos de base de datos (DESTINO) exactos del archivo de mapeo
  const databaseFields = {
    // Campos obligatorios para Libro Diario
    'journal_entry_id': { 
      label: 'journal_entry_id', 
      required: true, 
      confidence: 0.95,
      description: 'Identificador único del asiento contable',
      fileTypes: ['libro_diario']
    },
    'line_number': { 
      label: 'line_number', 
      required: true, 
      confidence: 1.0,
      description: 'Número secuencial de la línea del asiento',
      fileTypes: ['libro_diario']
    },
    'description': { 
      label: 'description', 
      required: true, 
      confidence: 0.9,
      description: 'Descripción general del asiento contable',
      fileTypes: ['libro_diario']
    },
    'line_description': { 
      label: 'line_description', 
      required: true, 
      confidence: 0.95,
      description: 'Descripción específica de la línea del asiento',
      fileTypes: ['libro_diario']
    },
    'posting_date': { 
      label: 'posting_date', 
      required: true, 
      confidence: 1.0,
      description: 'Fecha de contabilización del asiento',
      fileTypes: ['libro_diario']
    },
    'fiscal_year': { 
      label: 'fiscal_year', 
      required: true, 
      confidence: 1.0,
      description: 'Año del ejercicio fiscal',
      fileTypes: ['libro_diario']
    },
    'gl_account_number': { 
      label: 'gl_account_number', 
      required: true, 
      confidence: 0.8,
      description: 'Número de cuenta del libro mayor',
      fileTypes: ['libro_diario', 'sumas_saldos']
    },
    'amount': { 
      label: 'amount', 
      required: true, 
      confidence: 0.95,
      description: 'Importe en moneda local',
      fileTypes: ['libro_diario']
    },
    'debit_credit_indicator': { 
      label: 'debit_credit_indicator', 
      required: true, 
      confidence: 1.0,
      description: 'Indicador debe/haber (S = Debe, H = Haber)',
      fileTypes: ['libro_diario']
    },
    
    // Campos opcionales para Libro Diario
    'period_number': { 
      label: 'period_number', 
      required: false, 
      confidence: 0.0,
      description: 'Número de período contable',
      fileTypes: ['libro_diario']
    },
    'prepared_by': { 
      label: 'prepared_by', 
      required: false, 
      confidence: 0.9,
      description: 'Usuario que preparó el asiento',
      fileTypes: ['libro_diario']
    },
    'entry_date': { 
      label: 'entry_date', 
      required: false, 
      confidence: 0.95,
      description: 'Fecha de entrada al sistema',
      fileTypes: ['libro_diario']
    },
    'entry_time': { 
      label: 'entry_time', 
      required: false, 
      confidence: 1.0,
      description: 'Hora de entrada al sistema',
      fileTypes: ['libro_diario']
    },
    'vendor_id': { 
      label: 'vendor_id', 
      required: false, 
      confidence: 0.7,
      description: 'Identificador del proveedor/acreedor',
      fileTypes: ['libro_diario']
    },
    'company_code': { 
      label: 'company_code', 
      required: false, 
      confidence: 0.95,
      description: 'Sociedad/Empresa - Alta relevancia',
      fileTypes: ['libro_diario']
    },
    'currency': { 
      label: 'currency', 
      required: false, 
      confidence: 0.9,
      description: 'Moneda - Alta relevancia',
      fileTypes: ['libro_diario']
    },
    'status_indicator': { 
      label: 'status_indicator', 
      required: false, 
      confidence: 0.6,
      description: 'Estado/Status - Media relevancia',
      fileTypes: ['libro_diario']
    },
    'transaction_code': { 
      label: 'transaction_code', 
      required: false, 
      confidence: 0.6,
      description: 'Código de Transacción - Media relevancia',
      fileTypes: ['libro_diario']
    },
    'reversal_indicator': { 
      label: 'reversal_indicator', 
      required: false, 
      confidence: 0.6,
      description: 'Anulación/Contrapartida - Media relevancia',
      fileTypes: ['libro_diario']
    },
    'document_type': { 
      label: 'document_type', 
      required: false, 
      confidence: 0.6,
      description: 'Clase de Documento - Media relevancia',
      fileTypes: ['libro_diario']
    },
    'document_date': { 
      label: 'document_date', 
      required: false, 
      confidence: 0.85,
      description: 'Fecha del Documento - Alta relevancia',
      fileTypes: ['libro_diario']
    },
    'last_update': { 
      label: 'last_update', 
      required: false, 
      confidence: 0.3,
      description: 'Última Actualización - Baja relevancia',
      fileTypes: ['libro_diario']
    },
    'amount_local_currency': { 
      label: 'amount_local_currency', 
      required: false, 
      confidence: 0.95,
      description: 'Importe en Moneda Local - Alta relevancia',
      fileTypes: ['libro_diario']
    },
    'clearing_document': { 
      label: 'clearing_document', 
      required: false, 
      confidence: 0.6,
      description: 'Documento de Compensación - Media relevancia',
      fileTypes: ['libro_diario']
    },
    'clearing_date': { 
      label: 'clearing_date', 
      required: false, 
      confidence: 0.6,
      description: 'Fecha Compensación - Media relevancia',
      fileTypes: ['libro_diario']
    },
    'assignment_field': { 
      label: 'assignment_field', 
      required: false, 
      confidence: 0.6,
      description: 'Campo de Asignación/Compensación - Media relevancia',
      fileTypes: ['libro_diario']
    },
    'additional_code': { 
      label: 'additional_code', 
      required: false, 
      confidence: 0.3,
      description: 'Código adicional - Baja relevancia',
      fileTypes: ['libro_diario']
    },

    // Campos específicos para Sumas y Saldos
    'gl_account_name': { 
      label: 'gl_account_name', 
      required: false, 
      confidence: 0.9,
      description: 'Descripción de la cuenta contable',
      fileTypes: ['sumas_saldos']
    },
    'period_beginning_balance': { 
      label: 'period_beginning_balance', 
      required: false, 
      confidence: 1.0,
      description: 'Saldo inicial del período',
      fileTypes: ['sumas_saldos']
    },
    'period_ending_balance': { 
      label: 'period_ending_balance', 
      required: false, 
      confidence: 1.0,
      description: 'Saldo final del período',
      fileTypes: ['sumas_saldos']
    }
  };

  // Mapeo automático basado en el archivo de referencia (ORIGEN → DESTINO)
  const automaticMappings = {
    // Mapeos para Libro Diario
    'libro_diario': {
      'Nº doc.': 'journal_entry_id',
      'Pos': 'line_number',
      'Texto Cabecera': 'description',
      'Texto Posición': 'line_description',
      'Fe.Contab.': 'posting_date',
      'Año': 'fiscal_year',
      'Lib.Mayor': 'gl_account_number',
      'Importe': 'amount',
      'Importe ML': 'amount_local_currency',
      'D/H': 'debit_credit_indicator',
      'Usuario': 'prepared_by',
      'FechaEntr': 'entry_date',
      'Hora': 'entry_time',
      'Acreedor': 'vendor_id',
      'Sociedad': 'company_code',
      'Moneda': 'currency',
      'S': 'status_indicator',
      'CódT': 'transaction_code',
      'Anul.con': 'reversal_indicator',
      'Clase doc.': 'document_type',
      'Fecha doc.': 'document_date',
      'Últ.act.': 'last_update',
      'Compensación': 'assignment_field',
      'Fe.Comp.': 'clearing_date',
      'Doc.Comp.': 'clearing_document',
      'CT': 'additional_code'
    },
    
    // Mapeos específicos para Sumas y Saldos
    'sumas_saldos': {
      'Nº cuenta': 'gl_account_number',
      'Texto p.posición balance/PyG': 'gl_account_name',
      'TotPerInf': 'period_beginning_balance',
      'TotPerComp': 'period_ending_balance'
    }
  };

  useEffect(() => {
    if (originalFields && originalFields.length > 0) {
      const initialMappings = {};
      const currentMappings = automaticMappings[fileType] || {};
      
      originalFields.forEach(field => {
        initialMappings[field] = currentMappings[field] || '';
      });
      setFieldMappings(initialMappings);
    }
  }, [originalFields, fileType]);

  const handleMappingChange = (originalField, targetField) => {
    const newMappings = {
      ...fieldMappings,
      [originalField]: targetField
    };
    setFieldMappings(newMappings);
  };

  const handleApplyMappings = () => {
    if (onMappingChange) {
      onMappingChange(fieldMappings);
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.9) return 'text-green-600 bg-green-50';
    if (confidence >= 0.7) return 'text-yellow-600 bg-yellow-50';
    if (confidence >= 0.5) return 'text-orange-600 bg-orange-50';
    return 'text-red-600 bg-red-50';
  };

  const getConfidenceLabel = (confidence) => {
    if (confidence >= 0.9) return 'Alta';
    if (confidence >= 0.7) return 'Media';
    if (confidence >= 0.5) return 'Baja';
    return 'Sin mapeo';
  };

  const getMappedCount = () => {
    return Object.values(fieldMappings).filter(mapping => mapping !== '').length;
  };

  const getRequiredMappedCount = () => {
    const mappedRequiredFields = Object.entries(fieldMappings)
      .filter(([_, targetField]) => targetField && databaseFields[targetField]?.required)
      .length;
    const totalRequiredFields = Object.values(databaseFields)
      .filter(field => field.required && field.fileTypes.includes(fileType)).length;
    return { mapped: mappedRequiredFields, total: totalRequiredFields };
  };

  const getFilteredDatabaseFields = () => {
    return Object.entries(databaseFields)
      .filter(([key, field]) => {
        const matchesFileType = field.fileTypes.includes(fileType);
        const matchesSearch = searchTerm === '' || 
          key.toLowerCase().includes(searchTerm.toLowerCase()) ||
          field.label.toLowerCase().includes(searchTerm.toLowerCase());
        return matchesFileType && matchesSearch;
      });
  };

  const getFileTypeTitle = () => {
    return fileType === 'libro_diario' 
      ? 'Mapeo de Campos - Libro Diario'
      : 'Mapeo de Campos - Sumas y Saldos';
  };

  if (!originalFields || originalFields.length === 0) {
    return null;
  }

  const requiredStats = getRequiredMappedCount();
  const filteredDatabaseFields = getFilteredDatabaseFields();

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header - más compacto */}
      <div 
        className="px-4 py-3 border-b border-gray-200 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3">
              <h3 className="text-base font-semibold text-gray-900">
                {getFileTypeTitle()}
              </h3>
              
              {/* Estadísticas compactas */}
              <div className="flex items-center space-x-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {getMappedCount()}/{originalFields.length} mapeados
                </span>
                {fileType === 'libro_diario' && (
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    requiredStats.mapped === requiredStats.total 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {requiredStats.mapped}/{requiredStats.total} obligatorios
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Botón Aplicar compacto */}
          <div className="flex items-center ml-4">
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleApplyMappings();
              }}
              className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
            >
              <svg className="w-3 h-3 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Aplicar
            </button>
            
            {/* Icono de expand/collapse */}
            <svg 
              className={`w-4 h-4 text-gray-400 transition-transform duration-200 ml-3 ${
                isOpen ? 'rotate-180' : ''
              }`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>

      {/* Contenido del mapeo - más compacto */}
      {isOpen && (
        <div className="px-4 py-3">
          {/* Buscador compacto */}
          <div className="mb-3">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-2 flex items-center pointer-events-none">
                <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                className="block w-full pl-8 pr-3 py-1.5 border border-gray-300 rounded-md leading-4 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-purple-500 focus:border-purple-500 text-xs"
                placeholder="Buscar campos de base de datos..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          {/* Tabla de mapeo compacta */}
          <div className="overflow-x-auto max-h-64 overflow-y-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Campo BD (Destino)
                  </th>
                  <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Campo {fileType === 'libro_diario' ? 'SAP' : 'SyS'} (Origen)
                  </th>
                  <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Confianza
                  </th>
                  <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Oblig.
                  </th>
                  <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Descripción
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredDatabaseFields.map(([databaseField, fieldInfo], index) => {
                  const mappedOriginalField = Object.entries(fieldMappings)
                    .find(([_, mappedField]) => mappedField === databaseField)?.[0] || '';
                  
                  return (
                    <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-3 py-1.5 whitespace-nowrap">
                        <div className="text-xs font-medium text-gray-900">
                          {fieldInfo.label}
                        </div>
                      </td>
                      <td className="px-3 py-1.5 whitespace-nowrap">
                        <select
                          value={mappedOriginalField}
                          onChange={(e) => {
                            const currentMappedField = Object.entries(fieldMappings)
                              .find(([_, mappedField]) => mappedField === databaseField);
                            if (currentMappedField) {
                              handleMappingChange(currentMappedField[0], '');
                            }
                            if (e.target.value) {
                              handleMappingChange(e.target.value, databaseField);
                            }
                          }}
                          className="block w-full px-2 py-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 text-xs"
                        >
                          <option value="">-- Sin mapear --</option>
                          {originalFields.map((originalField) => {
                            const isAlreadyMapped = fieldMappings[originalField] && fieldMappings[originalField] !== databaseField;
                            return (
                              <option 
                                key={originalField} 
                                value={originalField}
                                disabled={isAlreadyMapped}
                                style={isAlreadyMapped ? { color: '#9CA3AF' } : {}}
                              >
                                {originalField} {isAlreadyMapped ? '(ya mapeado)' : ''}
                              </option>
                            );
                          })}
                        </select>
                      </td>
                      <td className="px-3 py-1.5 whitespace-nowrap">
                        {mappedOriginalField && (
                          <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium ${getConfidenceColor(fieldInfo.confidence)}`}>
                            {Math.round(fieldInfo.confidence * 100)}%
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-1.5 whitespace-nowrap">
                        {fieldInfo.required && (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            Sí
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-1.5">
                        <div className="text-xs text-gray-500 max-w-xs truncate" title={fieldInfo.description}>
                          {fieldInfo.description}
                        </div>
                      </td>
                    </tr>
                  )}
                )}
              </tbody>
            </table>
          </div>

          {/* Resumen y acciones compactos */}
          <div className="mt-3 bg-gray-50 rounded-lg px-3 py-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="text-xs">
                  <span className="font-medium text-gray-900">Progreso:</span>
                  <span className="ml-1 text-gray-600">
                    {getMappedCount()}/{filteredDatabaseFields.length}
                  </span>
                </div>
                {fileType === 'libro_diario' && (
                  <div className="text-xs">
                    <span className="font-medium text-gray-900">Obligatorios:</span>
                    <span className={`ml-1 ${
                      requiredStats.mapped === requiredStats.total 
                        ? 'text-green-600' 
                        : 'text-yellow-600'
                    }`}>
                      {requiredStats.mapped}/{requiredStats.total}
                    </span>
                  </div>
                )}
              </div>
              
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => {
                    const resetMappings = {};
                    originalFields.forEach(field => {
                      resetMappings[field] = '';
                    });
                    setFieldMappings(resetMappings);
                  }}
                  className="inline-flex items-center px-2 py-1 border border-gray-300 shadow-sm text-xs leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                >
                  Limpiar
                </button>
                <button
                  onClick={() => {
                    const autoMappings = {};
                    const currentMappings = automaticMappings[fileType] || {};
                    originalFields.forEach(field => {
                      autoMappings[field] = currentMappings[field] || '';
                    });
                    setFieldMappings(autoMappings);
                  }}
                  className="inline-flex items-center px-2 py-1 border border-transparent text-xs leading-4 font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                >
                  Auto
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FieldMapper;