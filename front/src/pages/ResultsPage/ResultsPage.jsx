// frontend/src/pages/ResultsPage/ResultsPage.jsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Header from '../../components/Header/Header';
import userService from '../../services/userService';
import importService from '../../services/importService';

const ResultsPage = () => {
  const { executionId } = useParams();
  const navigate = useNavigate();
  
  const [user, setUser] = useState(null);
  const [conversionData, setConversionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadInitialData();
  }, [executionId]);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      
      // Cargar usuario
      const userResponse = await userService.getCurrentUser();
      if (userResponse.success && userResponse.user) {
        setUser(userResponse.user);
      }
      
      // Simular datos de conversión (ya que los archivos están convertidos)
      // En una implementación real, esto vendría del backend
      const mockConversionData = {
        executionId: executionId,
        success: true,
        message: "Conversión completada exitosamente",
        convertedFiles: [
          `${executionId}_libro_diario_converted.json`
        ],
        downloadUrls: [
          `/api/import/download/${executionId}_libro_diario_converted.json`
        ],
        summary: {
          totalRecords: 1245,
          processedRecords: 1245,
          errors: 0,
          warnings: 3,
          processingTime: "2.3 segundos"
        }
      };
      
      setConversionData(mockConversionData);
      
    } catch (err) {
      console.error('Error loading results:', err);
      setError('Error al cargar los resultados');
    } finally {
      setLoading(false);
    }
  };

  // Función para manejar cambio de usuario
  const handleUserChange = async (newUser) => {
    try {
      setUser(newUser);
      
      // Mostrar notificación del cambio
      showUserChangeNotification(newUser.name);
      
    } catch (err) {
      console.error('Error changing user:', err);
    }
  };

  const showUserChangeNotification = (userName) => {
    // Crear notificación temporal
    const notification = document.createElement('div');
    notification.className = 'fixed top-4 right-4 bg-purple-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 transform transition-all duration-300';
    notification.innerHTML = `
      <div class="flex items-center space-x-2">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
        </svg>
        <span>Cambiado a ${userName}</span>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    // Remover después de 3 segundos
    setTimeout(() => {
      notification.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (document.body.contains(notification)) {
          document.body.removeChild(notification);
        }
      }, 300);
    }, 3000);
  };

  const handleDownload = (filename) => {
    importService.downloadFile(filename);
  };

  const handleNewImport = () => {
    navigate('/libro-diario');
  };

  const handleBackToValidation = () => {
    navigate(`/libro-diario/validation/${executionId}`);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header user={user} onUserChange={handleUserChange} />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-gray-200 border-t-purple-600 mb-4"></div>
            <p className="text-gray-600">Cargando resultados...</p>
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header user={user} onUserChange={handleUserChange} />
        <main className="flex-1 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white rounded-xl shadow-sm p-8 text-center border border-red-100">
            <div className="text-6xl mb-4">⚠️</div>
            <h2 className="text-xl font-semibold text-red-600 mb-2">Error al cargar resultados</h2>
            <p className="text-gray-600 mb-6">{error}</p>
            <div className="space-y-2">
              <button 
                onClick={() => window.location.reload()} 
                className="w-full bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
              >
                Reintentar
              </button>
              <button 
                onClick={() => navigate('/libro-diario')} 
                className="w-full bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200"
              >
                Volver al inicio
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header user={user} onUserChange={handleUserChange} />
      
      <main className="flex-1 [&_*]:text-xs [&_h1]:text-lg [&_h2]:text-base [&_h3]:text-sm">
        <div className="max-w-full mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8">
          {/* Breadcrumb */}
          <nav className="flex mb-8" aria-label="Breadcrumb">
            <ol className="inline-flex items-center space-x-1 md:space-x-3">
              <li className="inline-flex items-center">
                <button
                  onClick={() => navigate('/')}
                  className="inline-flex items-center text-sm font-medium text-gray-700 hover:text-purple-600"
                >
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"></path>
                  </svg>
                  Inicio
                </button>
              </li>
              <li>
                <div className="flex items-center">
                  <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd"></path>
                  </svg>
                  <button
                    onClick={() => navigate('/libro-diario')}
                    className="ml-1 text-sm font-medium text-gray-500 hover:text-purple-600 md:ml-2"
                  >
                    Importación Libro Diario
                  </button>
                </div>
              </li>
              <li>
                <div className="flex items-center">
                  <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd"></path>
                  </svg>
                  <span className="ml-1 text-sm font-medium text-gray-500 md:ml-2">Resultados</span>
                </div>
              </li>
            </ol>
          </nav>

          {/* Título */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultados de Conversión</h1>
            <p className="text-gray-600">Archivos procesados y listos para descarga</p>
          </div>

          {/* Indicador de pasos */}
          <div className="mb-8">
            <div className="flex items-center">
              <div className="flex items-center text-green-600">
                <div className="flex items-center justify-center w-8 h-8 border-2 border-green-600 rounded-full bg-green-600 text-white text-sm font-medium">
                  ✓
                </div>
                <span className="ml-2 text-sm font-medium">Importación</span>
              </div>
              <div className="flex-1 h-px bg-gray-200 mx-4"></div>
              <div className="flex items-center text-green-600">
                <div className="flex items-center justify-center w-8 h-8 border-2 border-green-600 rounded-full bg-green-600 text-white text-sm font-medium">
                  ✓
                </div>
                <span className="ml-2 text-sm font-medium">Validación</span>
              </div>
              <div className="flex-1 h-px bg-gray-200 mx-4"></div>
              <div className="flex items-center text-purple-600">
                <div className="flex items-center justify-center w-8 h-8 border-2 border-purple-600 rounded-full bg-purple-600 text-white text-sm font-medium">
                  ✓
                </div>
                <span className="ml-2 text-sm font-medium">Resultados</span>
              </div>
            </div>
          </div>

          {/* Mensaje de éxito */}
          <div className="mb-8 bg-green-50 border border-green-200 rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-medium text-green-800">
                  Procesamiento Completado Exitosamente
                </h3>
                <p className="text-green-700 mt-1">
                  Tus archivos han sido validados y grabados en la base de datos de Journal Entries. 
                  Puedes descargar los resultados.
                </p>
              </div>
            </div>
          </div>

          {conversionData && (
            <>
              
              {/* Resumen de procesamiento (modificado a dos cajitas) */}
              <div className="mb-8 grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Caja: Libro Diario */}
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <div className="flex items-start space-x-4">
                    <div className="flex-shrink-0">
                      <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                        <svg className="w-7 h-7 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 0 0 2-2V8.5L14.5 3H9a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.5 3V8.5H20" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6M9 16h6M9 8h4" />
</svg>
                      </div>
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">Libro Diario</h3>
                      <ul className="mt-3 space-y-2 text-sm text-gray-700 list-disc list-inside">
                        <li><span className="font-medium text-gray-900">6.391</span> cabeceras de asiento identificadas y procesadas correctamente</li>
                        <li><span className="font-medium text-gray-900">1.706</span> cabeceras de asiento sin detalle <span className="text-gray-500">(asientos estadísticos)</span></li>
                        <li><span className="font-medium text-gray-900">13.184</span> detalles de asiento identificados y procesadas correctamente</li>
                        <li><span className="font-medium text-gray-900">0</span> detalles de asiento sin cabecera</li>
                      </ul>
                    </div>
                  </div>
                </div>

                {/* Caja: Sumas y Saldos */}
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <div className="flex items-start space-x-4">
                    <div className="flex-shrink-0">
                      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                        <svg className="w-7 h-7 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 0 0 2-2V8.5L14.5 3H9a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.5 3V8.5H20" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6M9 16h6M9 8h4" />
</svg>
                      </div>
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">Sumas y Saldos</h3>
                      <ul className="mt-3 space-y-2 text-sm text-gray-700 list-disc list-inside">
                        <li><span className="font-medium text-gray-900">157</span> cuentas identificadas y procesadas correctamente</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              {/* Pruebas realizadas */}
              {/* Descargas de pruebas realizadas */}
              <div className="mb-8">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-6">Pruebas realizadas</h3>
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Archivo 1 */}
                    <a
                      href="/Reporte_Integridad_SumasYSaldos.xlsx"
                      download
                      className="flex items-center justify-between bg-white border border-gray-200 rounded-lg p-4 hover:shadow"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                          <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3v12m0 0l-3-3m3 3l3-3M6 21h12a2 2 0 002-2v-5a2 2 0 00-2-2H6a2 2 0 00-2 2v5a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">Reporte_Integridad_SumasYSaldos.xlsx</p>
                          <p className="text-xs text-gray-500">Descargar resultado de verificación de integridad</p>
                        </div>
                      </div>
                      <span className="text-xs text-gray-500">XLSX</span>
                    </a>
                    {/* Archivo 2 */}
                    <a
                      href="/Reporte_Resumen_Por_Usuario.xlsx"
                      download
                      className="flex items-center justify-between bg-white border border-gray-200 rounded-lg p-4 hover:shadow"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                          <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3v12m0 0l-3-3m3 3l3-3M6 21h12a2 2 0 002-2v-5a2 2 0 00-2-2H6a2 2 0 00-2 2v5a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">Reporte_Resumen_Por_Usuario.xlsx</p>
                          <p className="text-xs text-gray-500">Descargar resumen agregado por usuario</p>
                        </div>
                      </div>
                      <span className="text-xs text-gray-500">XLSX</span>
                    </a>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Botones de acción */}
          <div className="flex flex-col sm:flex-row sm:justify-between space-y-4 sm:space-y-0 sm:space-x-4">
            <div className="flex space-x-4">
              <button
                onClick={handleBackToValidation}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Ver Validación
              </button>
              <button
                onClick={() => navigate('/')}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                Ir al Inicio
              </button>
            </div>
            
            <button
              onClick={handleNewImport}
              className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-lg text-white bg-purple-600 hover:bg-purple-700 focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-colors"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Nueva Importación
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ResultsPage;