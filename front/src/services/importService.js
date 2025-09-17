// frontend/src/services/importService.js
import api from './api';

/**
 * ImportService
 * - Sube Libro Diario y (opcionalmente) Sumas y Saldos al endpoint /api/import/upload
 * - Lanza validación con /api/import/validate/{execution_id}
 * - Consulta estado con /api/import/validate/{execution_id}/status
 */
class ImportService {
  /**
   * Compat: solo Libro Diario
   */
  async uploadLibroDiario(libroDiarioFiles, projectId, period, testType = 'libro_diario_import') {
    return this.uploadLibroDiarioYSumas(libroDiarioFiles, null, projectId, period, testType);
  }

  /**
   * Sube Libro Diario y, si existe, Sumas y Saldos.
   * Devuelve ambos executionIds para poder validar cada uno con el mismo endpoint de validación.
   */
  async uploadLibroDiarioYSumas(libroDiarioFiles, sumasSaldosFile, projectId, period, testType = 'libro_diario_import') {
    try {
      if (!libroDiarioFiles || libroDiarioFiles.length === 0) {
        return { success: false, error: 'Debe adjuntar al menos un archivo de Libro Diario' };
      }

      // 1) Subir Libro Diario (permite múltiples archivos)
      const formDataLD = new FormData();
      libroDiarioFiles.forEach((f) => formDataLD.append('file', f, f.name));
      formDataLD.append('project_id', projectId || '');
      formDataLD.append('period', period || '');
      formDataLD.append('test_type', testType || 'libro_diario_import');

      const respLD = await api.post('/api/import/upload', formDataLD, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const dataLD = respLD?.data || {};
      const executionIdLD = dataLD.execution_id || dataLD.executionId || dataLD.id;
      if (!executionIdLD) {
        return { success: false, error: 'No se recibió execution_id del backend al subir Libro Diario', data: dataLD };
      }

      // 2) Si existe Sumas y Saldos, subirlo
      let sumasUpload = null;
      let executionIdSS = null;

      if (sumasSaldosFile) {
        try {
          const formDataSS = new FormData();
          formDataSS.append('file', sumasSaldosFile, sumasSaldosFile.name);
          formDataSS.append('project_id', projectId || '');
          formDataSS.append('period', period || '');
          formDataSS.append('test_type', 'sumas_saldos_import');
          // vincular al LD si el backend lo soporta (si no, lo ignora sin romper)
          formDataSS.append('parent_execution_id', executionIdLD);

          const respSS = await api.post('/api/import/upload', formDataSS, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          const dataSS = respSS?.data || {};
          executionIdSS = dataSS.execution_id || dataSS.executionId || dataSS.id || null;
          sumasUpload = { success: true, data: dataSS, executionIdSS };
        } catch (e) {
          console.error('upload Sumas y Saldos error:', e);
          sumasUpload = { success: false, error: e?.response?.data?.detail || e?.message || 'Error al subir Sumas y Saldos' };
        }
      }

      return { success: true, executionId: executionIdLD, executionIdSS, data: dataLD, sumasUpload };
    } catch (error) {
      console.error('uploadLibroDiarioYSumas error:', error);
      const msg = error?.response?.data?.detail || error?.message || 'Error al subir los archivos';
      return { success: false, error: msg };
    }
  }

  /** Lanza la validación */
  async startValidation(executionId) {
    try {
      const resp = await api.post(`/api/import/validate/${encodeURIComponent(executionId)}`);
      return { success: true, data: resp?.data };
    } catch (error) {
      console.error('startValidation error:', error);
      const msg = error?.response?.data?.detail || error?.message || 'Error al iniciar validación';
      return { success: false, error: msg };
    }
  }

  /** Consulta estado */
  async getValidationStatus(executionId) {
    try {
      const resp = await api.get(`/api/import/validate/${encodeURIComponent(executionId)}/status`);
      return { success: true, data: resp?.data };
    } catch (error) {
      console.error('getValidationStatus error:', error);
      const status = error?.response?.status;
      const msg = error?.response?.data?.detail || error?.message || 'Error al consultar estado';
      return { success: false, statusCode: status, error: msg };
    }
  }

  /** Polling status hasta finalizar */
  async pollValidationStatus(executionId, { intervalMs = 1200, timeoutMs = 120000 } = {}) {
    const start = Date.now();
    const doneStates = new Set(['success', 'completed', 'validated', 'error', 'failed']);

    while (true) {
      const res = await this.getValidationStatus(executionId);
      if (res.success) {
        const status = (res.data?.status || res.data?.state || '').toString().toLowerCase();
        if (doneStates.has(status)) {
          const isOk = !['error', 'failed'].includes(status);
          return { success: isOk, finalStatus: status, data: res.data };
        }
      } else if (res.statusCode && res.statusCode !== 404) {
        return { success: false, finalStatus: 'error', error: res.error };
      }

      if (Date.now() - start > timeoutMs) {
        return { success: false, finalStatus: 'timeout', error: 'La validación tardó demasiado' };
      }
      await new Promise(r => setTimeout(r, intervalMs));
    }
  }

  /** Mock historial */
  async getImportHistory() {
    return { success: true, executions: [] };
  }
}

export default new ImportService();
