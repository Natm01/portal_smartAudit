// frontend/src/pages/ValidationPage/ValidationPage.jsx - SOLO LOS CAMBIOS SOLICITADOS
import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Header from '../../components/Header/Header';
import ValidationPhases from '../../components/ValidationPhases/ValidationPhases';
import FilePreview from '../../components/FilePreview/FilePreview';
import StatusModal from '../../components/StatusModal/StatusModal';
import userService from '../../services/userService';
import importService from '../../services/importService';

const ValidationPage = () => {
  const { executionId } = useParams();
  const navigate = useNavigate();
  const processStartedRef = useRef(false); // ÚNICO CAMBIO: Prevenir múltiples ejecuciones
  
  // Estados principales
  const [user, setUser] = useState(null);
  const [executionData, setExecutionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Estados del proceso
  const [processState, setProcessState] = useState({
    step: 'starting', // starting, validating, converting, completed, error
    libroDiario: {
      validated: false,
      validationError: null,
      converted: false, 
      conversionError: null
    },
    sumasSaldos: {
      validated: false,
      validationError: null
    }
  });
  
  const [statusModal, setStatusModal] = useState({ open: false, title: '', subtitle: '', status: 'info' });

  // ===========================================
  // EFECTOS Y CARGA INICIAL
  // ===========================================

  useEffect(() => {
    loadInitialData();
  }, [executionId]);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Cargar usuario
      const userResponse = await userService.getCurrentUser();
      if (userResponse.success && userResponse.user) {
        setUser(userResponse.user);
      }

      // Configurar datos de ejecución
      setExecutionData({
        executionId: executionId,
        projectName: 'HOTELES TURÍSTICOS UNIDOS, S.A.',
        period: '2023-01-01 a 2023-12-31',
        libroDiarioFile: 'BSEG.txt + BKPF.txt',
      });

      // CAMBIO: Iniciar proceso SOLO UNA VEZ
      if (!processStartedRef.current) {
        processStartedRef.current = true;
        await startValidationAndConversionProcess();
      }

    } catch (err) {
      console.error('Error en carga inicial:', err);
      setError('Error al cargar la información inicial');
    } finally {
      setLoading(false);
    }
  };

  // ===========================================
  // PROCESO PRINCIPAL
  // ===========================================

  const startValidationAndConversionProcess = async () => {
    try {
      // CAMBIO: Mostrar modal de conversión inicial
      setStatusModal({
        open: true,
        title: 'Convirtiendo archivo...',
        subtitle: 'Procesando y preparando archivos para validación',
        status: 'loading'
      });

      setProcessState(prev => ({ ...prev, step: 'validating' }));

      // Ejecutar validación coordinada + conversión
      const result = await importService.validateCoordinatedFiles(executionId);

      if (result.success) {
        // Proceso exitoso
        setProcessState({
          step: 'completed',
          libroDiario: {
            validated: result.results.libroDiario.success,
            validationError: result.results.libroDiario.error,
            converted: result.results.libroDiario.converted,
            conversionError: result.results.libroDiario.conversionError
          },
          sumasSaldos: {
            validated: result.results.sumasSaldos.success,
            validationError: result.results.sumasSaldos.error
          }
        });

        // Determinar mensaje de éxito
        const hasLD = result.results.libroDiario.attempted;
        const hasSS = result.results.sumasSaldos.attempted;
        
        let successMessage = '';
        if (hasLD && hasSS) {
          successMessage = 'Libro Diario validado y convertido • Sumas y Saldos validado';
        } else if (hasLD) {
          successMessage = 'Libro Diario validado y convertido correctamente';
        }

        setStatusModal({
          open: true,
          title: '¡Proceso completado!',
          subtitle: successMessage,
          status: 'success'
        });

      } else {
        // Proceso falló
        setProcessState(prev => ({
          ...prev,
          step: 'error',
          libroDiario: {
            validated: false,
            validationError: result.error,
            converted: false,
            conversionError: null
          }
        }));

        setStatusModal({
          open: true,
          title: 'Error en el proceso',
          subtitle: result.error || 'No se pudo completar la validación',
          status: 'error'
        });
      }

    } catch (error) {
      console.error('Error en proceso de validación:', error);
      
      setProcessState(prev => ({ ...prev, step: 'error' }));
      setStatusModal({
        open: true,
        title: 'Error inesperado',
        subtitle: error.message || 'Ocurrió un error durante el proceso',
        status: 'error'
      });
    }
  };

  // ===========================================
  // HANDLERS
  // ===========================================

  const handleUserChange = async (newUser) => {
    setUser(newUser);
    showUserChangeNotification(newUser.name);
  };

  const showUserChangeNotification = (userName) => {
    const notification = document.createElement('div');
    notification.className = 'fixed top-4 right-4 bg-purple-500 text-white px-4 py-2 rounded-lg shadow-lg z-50';
    notification.innerHTML = `
      <div class="flex items-center space-x-2">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
        </svg>
        <span>Cambiado a ${userName}</span>
      </div>
    `;
    document.body.appendChild(notification);
    setTimeout(() => {
      notification.style.transform = 'translateX(100%)';
      setTimeout(() => document.body.contains(notification) && document.body.removeChild(notification), 300);
    }, 3000);
  };

  const handleProceedToResults = () => {
    const canProceed = processState.step === 'completed' && 
                      processState.libroDiario.validated && 
                      processState.libroDiario.converted;
                      
    if (canProceed) {
      navigate(`/libro-diario/results/${executionId}`);
    }
  };

  // ===========================================
  // HELPERS
  // ===========================================

  const getProcessStatus = () => {
    switch (processState.step) {
      case 'starting':
        return { status: 'loading', message: 'Iniciando proceso...' };
      case 'validating':
        return { status: 'loading', message: 'Validando archivos...' };
      case 'converting':
        return { status: 'loading', message: 'Convirtiendo Libro Diario...' };
      case 'completed':
        if (processState.libroDiario.validated && processState.libroDiario.converted) {
          return { status: 'success', message: 'Proceso completado correctamente' };
        } else {
          return { status: 'error', message: 'Proceso incompleto' };
        }
      case 'error':
        return { status: 'error', message: 'Error en el proceso' };
      default:
        return { status: 'loading', message: 'Procesando...' };
    }
  };

  const canProceedToResults = () => {
    return processState.step === 'completed' && 
           processState.libroDiario.validated && 
           processState.libroDiario.converted;
  };

  const getStepStatus = (stepNumber) => {
    if (stepNumber === 1) return 'completed'; // Importación siempre completada
    if (stepNumber === 2) {
      return processState.step === 'completed' ? 'completed' : 'active';
    }
    if (stepNumber === 3) {
      return canProceedToResults() ? 'ready' : 'pending';
    }
    return 'pending';
  };

  // ===========================================
  // RENDER - SIN CAMBIOS VISUALES
  // ===========================================

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header user={user} onUserChange={handleUserChange} />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-gray-200 border-t-purple-600 mb-4"></div>
            <p className="text-gray-600">Cargando proceso...</p>
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
            <button 
              onClick={() => window.location.reload()} 
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
            >
              Reintentar
            </button>
          </div>
        </main>
      </div>
    );
  }

  const processStatus = getProcessStatus();

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header user={user} onUserChange={handleUserChange} />
      
      <main className="flex-1">
        <div className="max-w-full mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8 space-y-6">
          
          {/* Breadcrumb */}
          <nav className="flex" aria-label="Breadcrumb">
            <ol className="flex items-center space-x-4">
              <li>
                <a href="/" className="text-gray-400 hover:text-gray-500">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"></path>
                  </svg>
                </a>
              </li>
              <li>
                <div className="flex items-center">
                  <svg className="w-4 h-4 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd"></path>
                  </svg>
                  <a href="/libro-diario" className="ml-4 text-sm font-medium text-gray-500 hover:text-gray-700">
                    Importación Libro Diario
                  </a>
                </div>
              </li>
              <li>
                <div className="flex items-center">
                  <svg className="w-4 h-4 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd"></path>
                  </svg>
                  <span className="ml-4 text-sm font-medium text-gray-500">Validación</span>
                </div>
              </li>
            </ol>
          </nav>

          {/* Header */}
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Validación</h1>
            <p className="text-gray-600">
              Proyecto: {executionData?.projectName} • Período: {executionData?.period}
            </p>
          </div>

          {/* Steps Progress */}
          <div className="p-6">
            <div className="flex items-center justify-center">
              <div className="flex items-center text-green-600">
                <div className="flex items-center justify-center w-8 h-8 border-2 border-green-600 rounded-full bg-green-600 text-white text-sm font-medium">
                  ✓
                </div>
                <span className="ml-2 text-sm font-medium">Importación</span>
              </div>
              <div className="flex-1 h-px bg-gray-200 mx-4"></div>
              <div className={`flex items-center ${
                getStepStatus(2) === 'completed' ? 'text-green-600' : 'text-purple-600'
              }`}>
                <div className={`flex items-center justify-center w-8 h-8 border-2 rounded-full text-sm font-medium ${
                  getStepStatus(2) === 'completed' 
                    ? 'border-green-600 bg-green-600 text-white' 
                    : 'border-purple-600 bg-purple-600 text-white'
                }`}>
                  {getStepStatus(2) === 'completed' ? '✓' : '2'}
                </div>
                <span className="ml-2 text-sm font-medium">Validación</span>
              </div>
              <div className="flex-1 h-px bg-gray-200 mx-4"></div>
              <div className={`flex items-center ${
                getStepStatus(3) === 'ready' ? 'text-green-600' : 'text-gray-400'
              }`}>
                <div className={`flex items-center justify-center w-8 h-8 border-2 rounded-full text-sm font-medium ${
                  getStepStatus(3) === 'ready'
                    ? 'border-green-600 bg-green-600 text-white'
                    : 'border-gray-300'
                }`}>
                  {getStepStatus(3) === 'ready' ? '✓' : '3'}
                </div>
                <span className="ml-2 text-sm font-medium">Resultados</span>
              </div>
            </div>
          </div>

          {/* Status Card */}
          <div className={`p-4 rounded-lg border ${
            processStatus.status === 'success' 
              ? 'bg-green-50 border-green-200' 
              : processStatus.status === 'error'
              ? 'bg-red-50 border-red-200'
              : 'bg-blue-50 border-blue-200'
          }`}>
            <div className="flex items-center">
              <div className="flex-shrink-0">
                {processStatus.status === 'success' && (
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
                {processStatus.status === 'error' && (
                  <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
                {processStatus.status === 'loading' && (
                  <svg className="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                )}
              </div>
              <div className="ml-3">
                <p className={`text-sm font-medium ${
                  processStatus.status === 'success' ? 'text-green-800' :
                  processStatus.status === 'error' ? 'text-red-800' : 'text-blue-800'
                }`}>
                  {processStatus.message}
                </p>
              </div>
            </div>
          </div>

          {/* Validation Phases Component - SIN CAMBIOS */}
          <ValidationPhases 
            fileType="libro_diario" 
            onComplete={() => {}}
          />

          {/* File Preview - SIN CAMBIOS */}
          {executionData && (
            <FilePreview 
              file={executionData.libroDiarioFile} 
              fileType="libro_diario" 
              executionId={executionId} 
              maxRows={25} 
            />
          )}

          {/* Navigation */}
          <div className="flex justify-between items-center pt-6 border-t border-gray-200">
            <button 
              onClick={() => navigate('/libro-diario')} 
              className="flex items-center px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Volver a Importación
            </button>

            <button 
              onClick={handleProceedToResults} 
              disabled={!canProceedToResults()}
              className={`flex items-center px-6 py-2 rounded-lg transition-colors ${
                canProceedToResults()
                  ? 'bg-purple-600 text-white hover:bg-purple-700'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              Continuar a Resultados
              <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>

        </div>
      </main>

      {/* Status Modal */}
      <StatusModal
        isOpen={statusModal.open}
        title={statusModal.title}
        subtitle={statusModal.subtitle}
        status={statusModal.status}
        onClose={() => setStatusModal(prev => ({ ...prev, open: false }))}
      />

    </div>
  );
};

export default ValidationPage;