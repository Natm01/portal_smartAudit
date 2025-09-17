// frontend/src/pages/ValidationPage/ValidationPage.jsx
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
  const processStartedRef = useRef(false);

  // Datos del usuario y ejecución
  const [user, setUser] = useState(null);
  const [executionData, setExecutionData] = useState(null);

  // Estado de proceso
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusModal, setStatusModal] = useState({ open: false, title: '', subtitle: '', status: 'loading' });

  // Validación/Conversión/Mapeo
  const [processState, setProcessState] = useState({
    step: 'idle', // idle | validating | completed | error
    libroDiario: { validated: false, validationError: null, converted: false, conversionError: null },
    sumasSaldos: { validated: false, validationError: null }
  });

  // Flags de UI
  const [readyForPreview, setReadyForPreview] = useState(false);
  const [mapeoReady, setMapeoReady] = useState(false);
  const [fieldsMapping, setFieldsMapping] = useState(null);

  useEffect(() => {
    loadInitialData();
  }, [executionId]);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Usuario
      const userResponse = await userService.getCurrentUser();
      if (userResponse.success && userResponse.user) setUser(userResponse.user);

      // Datos mínimos de cabecera (si no los traes del backend)
      setExecutionData({
        executionId,
        projectName: 'HOTELES TURÍSTICOS UNIDOS, S.A.',
        period: '2023-01-01 a 2023-12-31',
        libroDiarioFile: 'Libro Diario',
      });

      // Inicia el proceso una sola vez
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

  const startValidationAndConversionProcess = async () => {
    try {
      setStatusModal({
        open: true,
        title: 'Convirtiendo archivo...',
        subtitle: 'Procesando y preparando archivos para validación',
        status: 'loading'
      });

      setProcessState(prev => ({ ...prev, step: 'validating' }));

      // 1) Validación coordinada (LD + SS) y 2) conversión de LD
      const result = await importService.validateCoordinatedFiles(executionId);

      if (result.success) {
        const ld = result.results.libroDiario;
        const ss = result.results.sumasSaldos;

        setProcessState({
          step: 'completed',
          libroDiario: {
            validated: ld.success,
            validationError: ld.error,
            converted: ld.converted,
            conversionError: ld.conversionError
          },
          sumasSaldos: {
            validated: ss.success,
            validationError: ss.error
          }
        });

        // Si la conversión terminó OK: habilitamos el preview y arrancamos mapeo
        if (ld.converted) {
          setReadyForPreview(true);

          // 3) Mapeo automático
          await importService.startAutomaticMapeo(executionId, 'TXT/SAP');

          // 4) Poll de estado del mapeo
          const completed = new Set(['completed', 'mapeo_completed', 'mapeo_completed_manual_required', 'error', 'failed']);
          for (let i = 0; i < 80; i++) { // ~100s a 1.25s
            const st = await importService.getMapeoStatus(executionId);
            const s = (st?.status || st?.state || '').toLowerCase();
            if (completed.has(s)) break;
            await new Promise(r => setTimeout(r, 1250));
          }

          // 5) Cargar detalle del mapeo (se usa para mostrar contadores si quieres)
          try {
            const fm = await importService.getFieldsMapping(executionId);
            setFieldsMapping(fm);
          } catch {
            setFieldsMapping(null);
          }
          setMapeoReady(true);
        }

        const hasLD = ld.attempted;
        const hasSS = ss.attempted;
        let successMessage = '';
        if (hasLD && hasSS) successMessage = 'Libro Diario validado y convertido • Sumas y Saldos validado';
        else if (hasLD) successMessage = 'Libro Diario validado y convertido correctamente';

        setStatusModal({
          open: true,
          title: 'Proceso completado',
          subtitle: successMessage,
          status: 'success'
        });
      } else {
        setProcessState(prev => ({
          ...prev,
          step: 'error',
          libroDiario: { validated: false, validationError: result.error, converted: false, conversionError: null }
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

  const handleUserChange = (newUser) => setUser(newUser);

  const canProceedToResults = () => {
    return processState.step === 'completed' && processState.libroDiario.converted;
  };

  const handleProceedToResults = () => {
    if (!canProceedToResults()) return;
    navigate(`/resultados/${executionId}`);
  };

  const getStepStatus = (stepNumber) => {
    // 1 Importación (siempre completada cuando llegas aquí)
    if (stepNumber === 1) return 'completed';
    // 2 Validación (completada si el proceso terminó)
    if (stepNumber === 2) return processState.step === 'completed' ? 'completed' : 'pending';
    // 3 Resultados
    if (stepNumber === 3) return canProceedToResults() ? 'ready' : 'pending';
    return 'pending';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header user={user} onUserChange={handleUserChange} showUserSelector={true} />
        <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-purple-600"></div>
            <span className="ml-4 text-lg text-gray-600">Cargando proceso...</span>
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header user={user} onUserChange={handleUserChange} showUserSelector={true} />
        <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-center py-12">
            <div className="max-w-md w-full bg-white rounded-xl shadow-sm p-8 text-center border border-red-100">
              <div className="text-6xl mb-4">!</div>
              <h2 className="text-xl font-semibold text-red-600 mb-2">Error al cargar resultados</h2>
              <p className="text-gray-600 mb-6">{error}</p>
              <button
                onClick={() => navigate('/libro-diario')}
                className="px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700"
              >
                Volver a Importación
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header user={user} onUserChange={handleUserChange} showUserSelector={true} />

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Validación de Archivos Contables</h1>
          <p className="mt-2 text-sm text-gray-600">
            Proyecto: {executionData?.projectName} • Período: {executionData?.period}
          </p>
        </div>

        {/* Steps */}
        <div className="p-6">
          <div className="flex items-center justify-center">
            <div className="flex items-center text-green-600">
              <div className="flex items-center justify-center w-8 h-8 border-2 border-green-600 rounded-full bg-green-600 text-white text-sm font-medium">✓</div>
              <span className="ml-2 text-sm font-medium">Importación</span>
            </div>
            <div className="flex-1 h-px bg-gray-200 mx-4"></div>
            <div className={`flex items-center ${getStepStatus(2) === 'completed' ? 'text-green-600' : 'text-purple-600'}`}>
              <div className={`flex items-center justify-center w-8 h-8 border-2 rounded-full text-sm font-medium ${
                getStepStatus(2) === 'completed' ? 'border-green-600 bg-green-600 text-white' : 'border-purple-600 bg-purple-600 text-white'
              }`}>
                {getStepStatus(2) === 'completed' ? '✓' : '2'}
              </div>
              <span className="ml-2 text-sm font-medium">Validación</span>
            </div>
            <div className="flex-1 h-px bg-gray-200 mx-4"></div>
            <div className={`flex items-center ${getStepStatus(3) === 'ready' ? 'text-green-600' : 'text-gray-400'}`}>
              <div className={`flex items-center justify-center w-8 h-8 border-2 rounded-full text-sm font-medium ${
                getStepStatus(3) === 'ready' ? 'border-green-600 bg-green-600 text-white' : 'border-gray-300 text-gray-500'
              }`}>
                3
              </div>
              <span className="ml-2 text-sm font-medium">Resultados</span>
            </div>
          </div>
        </div>

        {/* Bloque Libro Diario */}
        {executionData && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Validaciones de Libro Diario</h2>
              <span className="text-sm text-gray-500">
                {processState.step === 'completed' ? 'Completado' : 'Pendiente'}
              </span>
            </div>

            <div className="mt-4">
              <ValidationPhases fileType="libro_diario" onComplete={() => {}} />
              <FilePreview
                file={executionData.libroDiarioFile}
                fileType="libro_diario"
                executionId={executionId}
                maxRows={25}
                enabled={readyForPreview}  // Solo carga preview cuando hay conversión lista
                mapeoReady={mapeoReady}
                mappingSummary={fieldsMapping?.mapping_summary || null}
              />
            </div>
          </div>
        )}

        {/* Navegación inferior */}
        <div className="flex justify-between items-center mt-8 pt-8 border-t border-gray-200">
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
                : 'disabled:opacity-50 disabled:cursor-not-allowed bg-purple-600 text-white'
            }`}
          >
            Continuar a Resultados
            <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </main>

      {/* Modal estado */}
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
