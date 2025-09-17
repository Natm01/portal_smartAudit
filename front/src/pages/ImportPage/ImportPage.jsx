// frontend/src/pages/ImportPage/ImportPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/Header/Header';
import ImportForm from '../../components/ImportForm/ImportForm';
import ImportHistory from '../../components/ImportHistory/ImportHistory';
import StatusModal from '../../components/StatusModal/StatusModal';
import userService from '../../services/userService';
import projectService from '../../services/projectService';
import importService from '../../services/importService';

const ImportPage = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [projects, setProjects] = useState([]);
  const [importHistory, setImportHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [statusModal, setStatusModal] = useState({
    open: false,
    title: '',
    subtitle: '',
    status: 'info', // info | loading | success | error
    executionId: null,
  });

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    setError(null);
    try {
      const userResponse = await userService.getCurrentUser();
      if (userResponse.success && userResponse.user) setUser(userResponse.user);

      const projectsResponse = await projectService.getAllProjects();
      if (projectsResponse.success) setProjects(projectsResponse.projects);

      const historyResponse = await importService.getImportHistory();
      if (historyResponse.success) setImportHistory(historyResponse.executions);
    } catch (err) {
      console.error('Error loading initial data:', err);
      setError('Error al cargar la información inicial');
    } finally {
      setLoading(false);
    }
  };

  const showUserChangeNotification = (userName) => {
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
    setTimeout(() => {
      notification.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (document.body.contains(notification)) document.body.removeChild(notification);
      }, 300);
    }, 3000);
  };

  const handleUserChange = async (newUser) => {
    try {
      setUser(newUser);
      showUserChangeNotification(newUser.name);
    } catch (err) {
      console.error('Error changing user:', err);
      setError('Error al cambiar de usuario');
    }
  };

  // === Submit: subir LD + (SS si existe) y validar ambos ===
  const handleImportSubmit = async ({ projectId, period, libroDiarioFiles, sumasSaldosFile }) => {
    try {
      setError(null);
      setStatusModal({
        open: true,
        title: 'Subiendo archivos…',
        subtitle: 'Cargando Libro Diario' + (sumasSaldosFile ? ' y Sumas y Saldos' : ''),
        status: 'loading',
        executionId: null,
      });

      // 1) Subir
      const uploadRes = await importService.uploadLibroDiarioYSumas(libroDiarioFiles, sumasSaldosFile, projectId, period);
      if (!uploadRes.success) {
        setStatusModal({
          open: true,
          title: 'Error al subir archivos',
          subtitle: uploadRes.error || 'Revisa los formatos y vuelve a intentar.',
          status: 'error',
          executionId: null,
        });
        return;
      }

      const executionIdLD = uploadRes.executionId;
      const executionIdSS = uploadRes.executionIdSS || null;

      // Persistir relación SS->LD para la página de Validación
      if (executionIdLD && executionIdSS) {
        try { sessionStorage.setItem(`ss_execution_for_${executionIdLD}`, executionIdSS); } catch {}
      }

      // 2) Validación de Libro Diario
      setStatusModal({
        open: true,
        title: 'Archivo(s) subido(s) correctamente',
        subtitle: 'Iniciando validación de Libro Diario…',
        status: 'info',
        executionId: executionIdLD,
      });

      const startValLD = await importService.startValidation(executionIdLD);
      if (!startValLD.success) {
        setStatusModal({
          open: true,
          title: 'Error al iniciar validación de Libro Diario',
          subtitle: startValLD.error || 'Intenta validar desde la página de Validación.',
          status: 'error',
          executionId: executionIdLD,
        });
        return;
      }

      setStatusModal({
        open: true,
        title: 'Validando…',
        subtitle: 'Libro Diario en proceso de validación.',
        status: 'loading',
        executionId: executionIdLD,
      });

      const pollLD = await importService.pollValidationStatus(executionIdLD, { intervalMs: 1200, timeoutMs: 180000 });

      // 3) Si hay Sumas y Saldos, validar también
      if (executionIdSS) {
        await importService.startValidation(executionIdSS);

        setStatusModal({
          open: true,
          title: pollLD.success ? 'Libro Diario validado' : 'Libro Diario no validado',
          subtitle: 'Iniciando validación de Sumas y Saldos…',
          status: pollLD.success ? 'info' : 'error',
          executionId: executionIdLD,
        });

        const pollSS = await importService.pollValidationStatus(executionIdSS, { intervalMs: 1200, timeoutMs: 180000 });

        if (pollLD.success && pollSS.success) {
          setStatusModal({
            open: true,
            title: '¡Archivos validados!',
            subtitle: 'Libro Diario y Sumas y Saldos validados correctamente.',
            status: 'success',
            executionId: executionIdLD,
          });
        } else if (pollLD.success && !pollSS.success) {
          setStatusModal({
            open: true,
            title: 'Libro Diario validado • Sumas y Saldos con problemas',
            subtitle: pollSS.error || `Estado SS: ${pollSS.finalStatus || 'desconocido'}`,
            status: 'error',
            executionId: executionIdLD,
          });
        } else if (!pollLD.success && pollSS.success) {
          setStatusModal({
            open: true,
            title: 'Sumas y Saldos validado • Libro Diario con problemas',
            subtitle: pollLD.error || `Estado LD: ${pollLD.finalStatus || 'desconocido'}`,
            status: 'error',
            executionId: executionIdLD,
          });
        } else {
          setStatusModal({
            open: true,
            title: 'Validaciones incompletas',
            subtitle: `LD: ${pollLD.finalStatus || 'error'} • SS: ${pollSS.finalStatus || 'error'}`,
            status: 'error',
            executionId: executionIdLD,
          });
        }
      } else {
        if (pollLD.success) {
          setStatusModal({
            open: true,
            title: '¡Archivo validado!',
            subtitle: 'Libro Diario validado correctamente.',
            status: 'success',
            executionId: executionIdLD,
          });
        } else {
          setStatusModal({
            open: true,
            title: 'La validación no se completó',
            subtitle: pollLD.error || `Estado final: ${pollLD.finalStatus || 'desconocido'}`,
            status: 'error',
            executionId: executionIdLD,
          });
        }
      }
    } catch (err) {
      console.error('handleImportSubmit error:', err);
      setStatusModal({
        open: true,
        title: 'Error inesperado',
        subtitle: err?.message || 'Ocurrió un problema al procesar tu solicitud.',
        status: 'error',
        executionId: null,
      });
    }
  };

  const handleHistoryItemClick = (execution) => {
    if (execution?.executionId) {
      navigate(`/libro-diario/validation/${execution.executionId}`);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header user={user} onUserChange={handleUserChange} />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-gray-200 border-t-purple-600 mb-4"></div>
            <p className="text-gray-600">Cargando información...</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header user={user} onUserChange={handleUserChange} />
      {/* Mantener proporciones originales */}
      <main className="flex-1">
        <div className="max-w-full mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8">
          {/* Breadcrumb */}
          <nav className="flex mb-8" aria-label="Breadcrumb">
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
                  <a href="/libro-diario" className="ml-4 text-sm font-medium text-gray-500 hover:text-gray-700">
                    Importación Libro Diario
                  </a>
                </div>
              </li>
            </ol>
          </nav>

          {/* Steps */}
          <div className="p-6">
            <div className="flex items-center justify-center">
              <div className="flex items-center text-purple-600">
                <div className="flex items-center justify-center w-8 h-8 border-2 border-purple-600 rounded-full bg-purple-600 text-white text-sm font-medium">1</div>
                <span className="ml-2 text-sm font-medium">Importación</span>
              </div>
              <div className="flex-1 h-px bg-gray-200 mx-4"></div>
              <div className="flex items-center text-gray-400">
                <div className="flex items-center justify-center w-8 h-8 border-2 border-gray-300 rounded-full text-sm font-medium">2</div>
                <span className="ml-2 text-sm font-medium">Validación</span>
              </div>
              <div className="flex-1 h-px bg-gray-200 mx-4"></div>
              <div className="flex items-center text-gray-400">
                <div className="flex items-center justify-center w-8 h-8 border-2 border-gray-300 rounded-full text-sm font-medium">3</div>
                <span className="ml-2 text-sm font-medium">Resultados</span>
              </div>
            </div>
          </div>

          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex">
                <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11V5a1 1 0 10-2 0v2a1 1 0 001 1h1a1 1 0 010 2h-1a3 3 0 100 6h1a1 1 0 110 2h-1a5 5 0 110-10h1z" clipRule="evenodd"></path>
                </svg>
                <span className="ml-2 text-sm text-red-700">{error}</span>
              </div>
            </div>
          )}

          {/* === Layout apilado: Formulario y debajo Historial === */}
          <div className="space-y-6">
            <ImportForm projects={projects} onSubmit={handleImportSubmit} loading={false} />
            <ImportHistory executions={importHistory} onItemClick={handleHistoryItemClick} loading={false} />
          </div>
        </div>
      </main>

      {/* Modal de estado */}
      <StatusModal
        isOpen={statusModal.open}
        title={statusModal.title}
        subtitle={statusModal.subtitle}
        status={statusModal.status}
        onClose={() => {
          if (statusModal.status === 'success' && statusModal.executionId) {
            const id = statusModal.executionId;
            setStatusModal(s => ({ ...s, open: false }));
            navigate(`/libro-diario/validation/${id}`);
          } else {
            setStatusModal(s => ({ ...s, open: false }));
          }
        }}
        actions={(statusModal.status === 'success' && statusModal.executionId) ? (
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setStatusModal(s => ({ ...s, open: false }))}
              className="px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-300 bg-white hover:bg-gray-50"
            >
              Seguir aquí
            </button>
            <button
              onClick={() => {
                const id = statusModal.executionId;
                setStatusModal(s => ({ ...s, open: false }));
                navigate(`/libro-diario/validation/${id}`);
              }}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-purple-600 text-white hover:bg-purple-700"
            >
              Ir a Validación
            </button>
          </div>
        ) : null}
      />
    </div>
  );
};

export default ImportPage;
