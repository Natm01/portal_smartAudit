// frontend/src/components/ExecutionDetailsModal/ExecutionDetailsModal.jsx
import React from 'react';

const ExecutionDetailsModal = ({ isOpen, execution, onClose, onDownload }) => {
  const [fullDetails, setFullDetails] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  // Cargar detalles completos cuando se abre el modal
  React.useEffect(() => {
    const loadFullDetails = async () => {
      if (isOpen && execution) {
        setLoading(true);
        try {
          // En desarrollo, usar datos simulados
          const mockDetails = {
            execution: execution,
            metadata: {
              executionId: execution.executionId,
              projectId: execution.projectId,
              fileSize: Math.floor(Math.random() * 5000000) + 1000000, // 1-5MB
              uploadDate: execution.executionDate,
              filePath: `/storage/files/${execution.executionId}_${execution.libroDiarioFile || 'archivo.csv'}`,
              version: execution.version || 1
            },
            canDownload: execution.status === 'success',
            availableFiles: []
          };

          // Agregar archivos disponibles si es exitoso
          if (execution.status === 'success') {
            if (execution.libroDiarioFile) {
              mockDetails.availableFiles.push({
                type: 'libro_diario',
                originalName: execution.libroDiarioFile,
                convertedName: `${execution.executionId}_libro_diario_converted.json`,
                description: 'Libro Diario en formato estándar JSON',
                size: '2.5 MB',
                records: Math.floor(Math.random() * 5000) + 1000
              });
            }
            if (execution.sumasSaldosFile) {
              mockDetails.availableFiles.push({
                type: 'sumas_saldos',
                originalName: execution.sumasSaldosFile,
                convertedName: `${execution.executionId}_sumas_saldos_converted.json`,
                description: 'Sumas y Saldos en formato estándar JSON',
                size: '1.2 MB',
                records: Math.floor(Math.random() * 500) + 100
              });
            }
          }

          setFullDetails(mockDetails);
        } catch (error) {
          console.error('Error loading full details:', error);
          setFullDetails(null);
        } finally {
          setLoading(false);
        }
      }
    };

    loadFullDetails();
  }, [isOpen, execution]);

  if (!isOpen || !execution) return null;

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return (
          <div className="flex items-center justify-center w-8 h-8 bg-green-100 rounded-full">
            <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        );
      case 'error':
        return (
          <div className="flex items-center justify-center w-8 h-8 bg-red-100 rounded-full">
            <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        );
      case 'warning':
        return (
          <div className="flex items-center justify-center w-8 h-8 bg-yellow-100 rounded-full">
            <svg className="w-4 h-4 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
        );
      case 'processing':
        return (
          <div className="flex items-center justify-center w-8 h-8 bg-blue-100 rounded-full">
            <svg className="w-4 h-4 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        );
      default:
        return (
          <div className="flex items-center justify-center w-8 h-8 bg-gray-100 rounded-full">
            <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'success': return 'Completado';
      case 'error': return 'Error';
      case 'warning': return 'Con advertencias';
      case 'processing': return 'Procesando';
      case 'pending': return 'Pendiente';
      default: return 'Desconocido';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return 'text-green-600 bg-green-50 border-green-200';
      case 'error': return 'text-red-600 bg-red-50 border-red-200';
      case 'warning': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'processing': return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'pending': return 'text-gray-600 bg-gray-50 border-gray-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('es-ES', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      }).format(date);
    } catch {
      return dateString;
    }
  };

  const getTestTypeText = (testType) => {
    switch (testType) {
      case 'libro_diario_import': return 'Importación Libro Diario';
      case 'sumas_saldos_import': return 'Importación Sumas y Saldos';
      default: return testType;
    }
  };

  const handleDownloadFile = (filename) => {
    if (onDownload) {
      onDownload(filename);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" onClick={handleBackdropClick}>
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Backdrop */}
        <div className="fixed inset-0 transition-opacity" aria-hidden="true">
          <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
        </div>

        {/* Modal */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
          {/* Header */}
          <div className="bg-white px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                {getStatusIcon(execution.status)}
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    Detalles de Importación
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">ID: {execution.executionId}</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="bg-white rounded-md text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <span className="sr-only">Cerrar</span>
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="bg-white px-6 py-6 max-h-96 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-4 border-gray-200 border-t-purple-600"></div>
                <span className="ml-3 text-gray-600">Cargando detalles...</span>
              </div>
            ) : (
              <div className="space-y-6">

                {/* Información del proyecto */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h4 className="font-medium text-gray-900 border-b pb-2">Información del Proyecto</h4>
                    
                    <div className="space-y-3">
                      <div>
                        <label className="text-sm font-medium text-gray-500">Proyecto</label>
                        <p className="text-sm text-gray-900">{execution.projectName}</p>
                        <p className="text-xs text-gray-500">ID: {execution.projectId}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-500">Tipo de Prueba</label>
                        <p className="text-sm text-gray-900">{getTestTypeText(execution.testType)}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-500">Periodo</label>
                        <p className="text-sm text-gray-900">{execution.period}</p>
                      </div>
                      {execution.version && execution.version > 1 && (
                        <div>
                          <label className="text-sm font-medium text-gray-500">Versión</label>
                          <p className="text-sm text-gray-900">
                            Versión {execution.version}
                            <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                              Actualizada
                            </span>
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h4 className="font-medium text-gray-900 border-b pb-2">Información de Ejecución</h4>
                    
                    <div className="space-y-3">
                      <div>
                        <label className="text-sm font-medium text-gray-500">Ejecutado por</label>
                        <p className="text-sm text-gray-900">{execution.userName}</p>
                        <p className="text-xs text-gray-500">ID: {execution.userId}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-500">Fecha de Ejecución</label>
                        <p className="text-sm text-gray-900">{formatDate(execution.executionDate)}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-500">ID de Ejecución</label>
                        <p className="text-sm text-gray-900 font-mono bg-gray-100 px-2 py-1 rounded">
                          {execution.executionId}
                        </p>
                      </div>
                      {fullDetails?.metadata && (
                        <div>
                          <label className="text-sm font-medium text-gray-500">Tamaño del archivo</label>
                          <p className="text-sm text-gray-900">
                            {(fullDetails.metadata.fileSize / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Archivos procesados */}
                <div className="space-y-4">
                  <h4 className="font-medium text-gray-900 border-b pb-2">Archivos Procesados</h4>
                  
                  <div className="space-y-3">
                    {execution.libroDiarioFile && (
                      <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg border border-blue-200">
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                            <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">📄 Libro Diario</p>
                            <p className="text-xs text-gray-600">{execution.libroDiarioFile}</p>
                            {fullDetails?.availableFiles?.find(f => f.type === 'libro_diario') && (
                              <p className="text-xs text-blue-600 mt-1">
                                {fullDetails.availableFiles.find(f => f.type === 'libro_diario').records} registros procesados
                              </p>
                            )}
                          </div>
                        </div>
                        {execution.status === 'success' && (
                          <button
                            onClick={() => handleDownloadFile(`${execution.executionId}_libro_diario_converted.json`)}
                            className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded text-white bg-purple-600 hover:bg-purple-700 transition-colors"
                          >
                            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Descargar JSON
                          </button>
                        )}
                      </div>
                    )}

                    {execution.sumasSaldosFile && (
                      <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg border border-green-200">
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                            <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">📊 Sumas y Saldos</p>
                            <p className="text-xs text-gray-600">{execution.sumasSaldosFile}</p>
                            {fullDetails?.availableFiles?.find(f => f.type === 'sumas_saldos') && (
                              <p className="text-xs text-green-600 mt-1">
                                {fullDetails.availableFiles.find(f => f.type === 'sumas_saldos').records} cuentas procesadas
                              </p>
                            )}
                          </div>
                        </div>
                        {execution.status === 'success' && (
                          <button
                            onClick={() => handleDownloadFile(`${execution.executionId}_sumas_saldos_converted.json`)}
                            className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded text-white bg-purple-600 hover:bg-purple-700 transition-colors"
                          >
                            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Descargar JSON
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Información técnica adicional */}
                {fullDetails && (
                  <div className="space-y-4">
                    <h4 className="font-medium text-gray-900 border-b pb-2">Información Técnica</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <label className="text-xs font-medium text-gray-500">Ruta del archivo</label>
                        <p className="text-xs text-gray-700 font-mono break-all">
                          {fullDetails.metadata?.filePath || 'N/A'}
                        </p>
                      </div>
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <label className="text-xs font-medium text-gray-500">Formato de salida</label>
                        <p className="text-xs text-gray-700">JSON estándar contable</p>
                      </div>
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <label className="text-xs font-medium text-gray-500">Estado de conversión</label>
                        <p className="text-xs text-gray-700">
                          {execution.status === 'success' ? '✅ Completado' : '⏳ Pendiente'}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Resumen de archivos disponibles para descarga */}
                {execution.status === 'success' && fullDetails?.availableFiles?.length > 0 && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h4 className="font-medium text-green-800 mb-3 flex items-center">
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Archivos Listos para Descarga ({fullDetails.availableFiles.length})
                    </h4>
                    <div className="space-y-2">
                      {fullDetails.availableFiles.map((file, index) => (
                        <div key={index} className="flex items-center justify-between bg-white p-3 rounded border">
                          <div>
                            <p className="text-sm font-medium text-gray-900">{file.description}</p>
                            <p className="text-xs text-gray-500">
                              {file.convertedName} • {file.size} • {file.records} registros
                            </p>
                          </div>
                          <button
                            onClick={() => handleDownloadFile(file.convertedName)}
                            className="text-sm text-green-600 hover:text-green-800 font-medium flex items-center"
                          >
                            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3" />
                            </svg>
                            Descargar
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-3 flex justify-between">
            <div>
              {execution.status === 'success' && (
                <p className="text-sm text-green-600 flex items-center">
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Procesamiento completado exitosamente
                </p>
              )}
              {execution.status === 'error' && (
                <p className="text-sm text-red-600 flex items-center">
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Error durante el procesamiento
                </p>
              )}
              {execution.status === 'processing' && (
                <p className="text-sm text-blue-600 flex items-center">
                  <svg className="w-4 h-4 mr-1 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Procesamiento en curso...
                </p>
              )}
            </div>
            <div className="flex space-x-3">
              {execution.status === 'success' && (
                <button
                  onClick={() => handleDownloadFile(`${execution.executionId}_libro_diario_converted.json`)}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Descargar Resultado
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExecutionDetailsModal;