// frontend/src/components/ImportHistory/ImportHistory.jsx
import React from 'react';

const ImportHistory = ({ executions, onItemClick, onDownload, loading }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return (
          <div className="flex items-center justify-center w-5 h-5 bg-green-100 rounded-full">
            <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        );
      case 'error':
        return (
          <div className="flex items-center justify-center w-5 h-5 bg-red-100 rounded-full">
            <svg className="w-3 h-3 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        );
      case 'warning':
        return (
          <div className="flex items-center justify-center w-5 h-5 bg-yellow-100 rounded-full">
            <svg className="w-3 h-3 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
        );
      case 'processing':
        return (
          <div className="flex items-center justify-center w-5 h-5 bg-blue-100 rounded-full">
            <svg className="w-3 h-3 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        );
      default:
        return (
          <div className="flex items-center justify-center w-5 h-5 bg-gray-100 rounded-full">
            <svg className="w-3 h-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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

  const getStatusBadgeColor = (status) => {
    switch (status) {
      case 'success': return 'bg-green-100 text-green-800';
      case 'error': return 'bg-red-100 text-red-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'processing': return 'bg-blue-100 text-blue-800';
      case 'pending': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
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

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Historial de Importaciones</h3>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-full mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-12 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Historial de Importaciones</h3>
        <p className="text-sm text-gray-600 mt-1">Tus últimas ejecuciones de importación</p>
      </div>

      {executions.length === 0 ? (
        <div className="text-center py-12">
          <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h4 className="text-sm font-medium text-gray-900 mb-1">No hay importaciones</h4>
          <p className="text-sm text-gray-500">Sube tu primer archivo para comenzar</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tipo de Prueba
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Proyecto
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Usuario
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Fecha de Ejecución
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {executions.slice(0, 10).map((execution) => (
                <tr key={execution.executionId} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(execution.status)}
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusBadgeColor(execution.status)}`}>
                        {getStatusText(execution.status)}
                      </span>
                    </div>
                    {execution.errorMessage && (
                      <div className="text-xs text-red-500 mt-1 max-w-xs truncate" title={execution.errorMessage}>
                        {execution.errorMessage}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {getTestTypeText(execution.testType)}
                    </div>
                    {execution.version && execution.version > 1 && (
                      <div className="text-xs text-gray-500">
                        Versión {execution.version}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900 max-w-xs truncate" title={execution.projectName}>
                      {execution.projectName}
                    </div>
                    <div className="text-xs text-gray-500">
                      {execution.period}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{execution.userName}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {formatDate(execution.executionDate)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        onClick={() => onItemClick(execution)}
                        className="text-purple-600 hover:text-purple-900 p-1 rounded-full hover:bg-purple-50"
                        title="Ver detalles"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </button>
                      {execution.status === 'success' && (
                        <button
                          onClick={() => onDownload && onDownload(`${execution.executionId}_libro_diario_converted.json`)}
                          className="text-green-600 hover:text-green-900 p-1 rounded-full hover:bg-green-50"
                          title="Descargar resultado"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {executions.length > 10 && (
        <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
          <div className="text-center">
            <button className="text-sm text-purple-600 hover:text-purple-500 font-medium">
              Ver más historial ({executions.length - 10} más)
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImportHistory;