// frontend/src/pages/ValidationPage/ValidationPage.jsx
import React, { useState, useEffect } from 'react';
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
  
  const [user, setUser] = useState(null);
  const [executionData, setExecutionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [validationPhases, setValidationPhases] = useState({
    libroDiario: { completed: false, results: null },
    sumasSaldos: { completed: false, results: null }
  });
  const [canProceed, setCanProceed] = useState(false);

  const [statusModal, setStatusModal] = useState({
    open: false, title: '', subtitle: '', status: 'info'
  });

  useEffect(() => {
    loadInitialData();
  }, [executionId]);

  const loadInitialData = async () => {
    setLoading(true);
    setError(null);
    try {
      const userResponse = await userService.getCurrentUser();
      if (userResponse.success && userResponse.user) {
        setUser(userResponse.user);
        setExecutionData({
          executionId: executionId,
          projectId: 'hoteles-turisticos-unidos-sa',
          projectName: 'HOTELES TURÍSTICOS UNIDOS, S.A.',
          period: '2023-01-01 a 2023-12-31',
          userId: userResponse.user.id,
          userName: userResponse.user.name,
          libroDiarioFile: 'BSEG.txt + BKPF.txt',
        });
      } else {
        setError('No se pudo cargar la información del usuario');
      }

      // 1) Estado de Libro Diario
      setStatusModal({ open: true, title: 'Comprobando validación…', subtitle: 'Consultando estado actual de Libro Diario.', status: 'loading' });
      let stateLD = await importService.getValidationStatus(executionId);
      if (!stateLD.success && stateLD.statusCode === 404) {
        await importService.startValidation(executionId);
        stateLD = await importService.getValidationStatus(executionId);
      }

      let ldOK = false;
      if (stateLD.success) {
        const s = (stateLD.data?.status || stateLD.data?.state || 'desconocido').toString().toLowerCase();
        if (['success', 'completed', 'validated'].includes(s)) ldOK = true;
        else if (!['error', 'failed'].includes(s)) {
          const pollLD = await importService.pollValidationStatus(executionId, { intervalMs: 1200, timeoutMs: 180000 });
          ldOK = pollLD.success;
        }
      }

      if (ldOK) setValidationPhases(prev => ({ ...prev, libroDiario: { completed: true, results: 'success' } }));
      else setValidationPhases(prev => ({ ...prev, libroDiario: { completed: false, results: 'error' } }));

      // 2) Si existe un executionId de Sumas y Saldos relacionado, comprobar también
      let ssExec = null;
      try {
        ssExec = sessionStorage.getItem(`ss_execution_for_${executionId}`);
      } catch {}
      if (ssExec) {
        let stateSS = await importService.getValidationStatus(ssExec);
        if (!stateSS.success && stateSS.statusCode === 404) {
          await importService.startValidation(ssExec);
          stateSS = await importService.getValidationStatus(ssExec);
        }

        let ssOK = false;
        if (stateSS.success) {
          const s2 = (stateSS.data?.status || stateSS.data?.state || 'desconocido').toString().toLowerCase();
          if (['success', 'completed', 'validated'].includes(s2)) ssOK = true;
          else if (!['error', 'failed'].includes(s2)) {
            const pollSS = await importService.pollValidationStatus(ssExec, { intervalMs: 1200, timeoutMs: 180000 });
            ssOK = pollSS.success;
          }
        }
        if (ssOK) setValidationPhases(prev => ({ ...prev, sumasSaldos: { completed: true, results: 'success' } }));
        else setValidationPhases(prev => ({ ...prev, sumasSaldos: { completed: false, results: 'error' } }));

        // Modal resumen
        const msg = `Libro Diario: ${ldOK ? 'OK' : 'Error'} • Sumas y Saldos: ${ssOK ? 'OK' : 'Error'}`;
        setStatusModal({ open: true, title: (ldOK && ssOK) ? '¡Validación completada!' : 'Validación con incidencias', subtitle: msg, status: (ldOK && ssOK) ? 'success' : 'error' });
      } else {
        // Solo LD
        setStatusModal({ open: true, title: ldOK ? '¡Validación de Libro Diario completada!' : 'Error en la validación de Libro Diario', subtitle: '', status: ldOK ? 'success' : 'error' });
      }

      // Habilitar continuar si al menos uno terminó OK (o ajusta la regla si quieres ambos OK)
      setCanProceed(ldOK || (validationPhases.sumasSaldos?.completed && validationPhases.sumasSaldos?.results === 'success'));
    } catch (err) {
      console.error('Error loading initial data:', err);
      setError('Error al cargar la información inicial');
    } finally {
      setLoading(false);
    }
  };

  const handleUserChange = async (newUser) => {
    try {
      setUser(newUser);
      const notification = document.createElement('div');
      notification.className = 'fixed top-4 right-4 bg-purple-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 transform transition-all duration-300';
      notification.innerHTML = `<div class="flex items-center space-x-2">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
        </svg><span>Cambiado a ${newUser.name}</span></div>`;
      document.body.appendChild(notification);
      setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => document.body.contains(notification) && document.body.removeChild(notification), 300);
      }, 3000);
    } catch (err) {
      console.error('Error changing user:', err);
    }
  };

  const handleLibroDiarioValidationComplete = () => {
    setValidationPhases(prev => ({ ...prev, libroDiario: { completed: true, results: 'success' } }));
    checkCanProceed();
  };

  const handleSumasSaldosValidationComplete = () => {
    setValidationPhases(prev => ({ ...prev, sumasSaldos: { completed: true, results: 'success' } }));
    checkCanProceed();
  };

  const checkCanProceed = () => {
    const libroDiarioCompleted = validationPhases.libroDiario.completed;
    const sumasSaldosCompleted = validationPhases.sumasSaldos.completed;
    if (libroDiarioCompleted || sumasSaldosCompleted) {
      setCanProceed(true);
    }
  };

  const handleProceedToResults = () => {
    if (canProceed) {
      navigate(`/libro-diario/results/${executionId}`);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header user={user} onUserChange={handleUserChange} showUserSelector={true} />
        <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-purple-600"></div>
            <span className="ml-4 text-lg text-gray-600">Cargando validación...</span>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header user={user} onUserChange={handleUserChange} showUserSelector={true} />
      
      <main className="flex-1 [&_*]:text-xs [&_h1]:text-lg [&_h2]:text-base [&_h3]:text-sm">
        <div className="space-y-6 max-w-full mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8">
          {/* Breadcrumb */}
          <nav className="flex" aria-label="Breadcrumb">
            <ol className="flex items-center space-x-4">
              <li>
                <div>
                  <a href="/" className="text-gray-400 hover:text-gray-500" title="Inicio">
                    <svg className="flex-shrink-0 w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"></path>
                    </svg>
                    <span className="sr-only">Inicio</span>
                  </a>
                </div>
              </li>
              <li>
                <div className="flex items-center">
                  <svg className="flex-shrink-0 w-4 h-4 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd"></path>
                  </svg>
                  <a href="/libro-diario" className="ml-4 text-sm font-medium text-gray-500 hover:text-gray-700">Importación Libro Diario</a>
                </div>
              </li>
              <li>
                <div className="flex items-center">
                  <svg className="flex-shrink-0 w-4 h-4 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd"></path>
                  </svg>
                  <span className="ml-4 text-sm font-medium text-gray-500">Validación</span>
                </div>
              </li>
            </ol>
          </nav>

          {/* Header */}
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Validación de Archivos Contables</h1>
            <p className="mt-2 text-sm text-gray-600">Proyecto: {executionData?.projectName} • Período: {executionData?.period}</p>
          </div>

          {/* Steps */}
          <div className="p-6">
            <div className="flex items-center justify-center">
              <div className="flex items-center text-green-600">
                <div className="flex items-center justify-center w-8 h-8 border-2 border-green-600 rounded-full bg-green-600 text-white text-sm font-medium">✓</div>
                <span className="ml-2 text-sm font-medium">Importación</span>
              </div>
              <div className="flex-1 h-px bg-gray-200 mx-4"></div>
              <div className="flex items-center text-purple-600">
                <div className="flex items-center justify-center w-8 h-8 border-2 border-purple-600 rounded-full bg-purple-600 text-white text-sm font-medium">2</div>
                <span className="ml-2 text-sm font-medium">Validación</span>
              </div>
              <div className="flex-1 h-px bg-gray-200 mx-4"></div>
              <div className="flex items-center text-gray-400">
                <div className="flex items-center justify-center w-8 h-8 border-2 border-gray-300 rounded-full text-sm font-medium">3</div>
                <span className="ml-2 text-sm font-medium">Resultados</span>
              </div>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
              <span className="block sm:inline">{error}</span>
            </div>
          )}

          {/* Contenido */}
          {executionData && (
            <div className="space-y-6 max-w-full mx-auto px-6 sm:px-8 lg:px-12 xl:px-16">
              <ValidationPhases fileType="libro_diario" onComplete={handleLibroDiarioValidationComplete} />
              <FilePreview file={executionData.libroDiarioFile} fileType="libro_diario" executionId={executionId} maxRows={25} />
            </div>
          )}

          {/* Navegación inferior */}
          <div className="flex justify-between items-center mt-8 pt-8 border-t border-gray-200">
            <button onClick={() => navigate('/libro-diario')} className="flex items-center px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Volver a Importación
            </button>
            <button onClick={handleProceedToResults} disabled={!canProceed} className="disabled:opacity-50 disabled:cursor-not-allowed hover:bg-purple-700 flex items-center px-6 py-2 bg-purple-600 text-white rounded-lg transition-colors">
              Continuar a Resultados
              <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </main>

      {/* Modal de estado de validación */}
      <StatusModal
        isOpen={statusModal.open}
        title={statusModal.title}
        subtitle={statusModal.subtitle}
        status={statusModal.status}
        onClose={() => setStatusModal(s => ({ ...s, open: false }))}
      />
    </div>
  );
};

export default ValidationPage;
