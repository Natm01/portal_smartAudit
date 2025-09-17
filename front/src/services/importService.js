// frontend/src/services/importService.js
import api from './api';

/**
 * ImportService - Cambios mínimos + endpoints de mapeo
 */
class ImportService {
  constructor() {
    // Cache para evitar llamadas duplicadas
    this.requestCache = new Map();
    this.activePolling = new Set();
  }

  // ===========================================
  // SUBIDA DE ARCHIVOS
  // ===========================================

  async uploadLibroDiarioYSumas(
    libroDiarioFiles,
    sumasSaldosFile,
    projectId,
    period,
    testType = 'libro_diario_import'
  ) {
    try {
      if (!libroDiarioFiles || libroDiarioFiles.length === 0) {
        return { success: false, error: 'Debe adjuntar al menos un archivo de Libro Diario' };
      }

      const primaryResult = await this._uploadPrimaryLibroDiario(
        libroDiarioFiles[0],
        projectId,
        period,
        testType
      );
      if (!primaryResult.success) return primaryResult;

      const executionIdLD = primaryResult.executionId;

      const additionalResults = await this._uploadAdditionalLibroDiarioFiles(
        libroDiarioFiles.slice(1),
        executionIdLD,
        projectId,
        period,
        testType
      );

      let sumasResult = null;
      if (sumasSaldosFile) {
        sumasResult = await this._uploadSumasSaldos(
          sumasSaldosFile,
          executionIdLD,
          projectId,
          period
        );
      }

      return {
        success: true,
        executionId: executionIdLD,
        executionIdSS: sumasResult?.executionId || null,
        primaryFile: primaryResult.data,
        additionalFiles: additionalResults,
        sumasUpload: sumasResult,
        summary: {
          libroDiarioFiles: libroDiarioFiles.length,
          sumasSaldosFile: sumasSaldosFile ? 1 : 0,
          totalFiles: libroDiarioFiles.length + (sumasSaldosFile ? 1 : 0),
          coordinatedIds: {
            libroDiario: executionIdLD,
            sumasSaldos: sumasResult?.executionId || null,
          },
        },
      };
    } catch (error) {
      return {
        success: false,
        error: error?.response?.data?.detail || error?.message || 'Error al subir archivos',
      };
    }
  }

  // ===========================================
  // VALIDACIÓN (con cache para evitar duplicados)
  // ===========================================

  async startValidation(executionId) {
    try {
      const cacheKey = `validate_start_${executionId}`;
      if (this.requestCache.has(cacheKey)) {
        return this.requestCache.get(cacheKey);
      }

      const response = await api.post(
        `/api/import/validate/${encodeURIComponent(executionId)}`
      );
      const result = { success: true, data: response?.data };
      this.requestCache.set(cacheKey, result);
      return result;
    } catch (error) {
      return {
        success: false,
        error:
          error?.response?.data?.detail ||
          error?.message ||
          'Error al iniciar validación',
      };
    }
  }

  async getValidationStatus(executionId) {
    try {
      const response = await api.get(
        `/api/import/validate/${encodeURIComponent(executionId)}/status`
      );
      return { success: true, data: response?.data };
    } catch (error) {
      const statusCode = error?.response?.status;
      const message =
        error?.response?.data?.detail || error?.message || 'Error al consultar estado';
      return { success: false, statusCode, error: message };
    }
  }

  async pollValidationStatus(executionId, options = {}) {
    const { intervalMs = 1200, timeoutMs = 120000 } = options;

    const pollingKey = `poll_validation_${executionId}`;
    if (this.activePolling.has(pollingKey)) {
      throw new Error(`Ya hay un polling activo para validación: ${executionId}`);
    }

    this.activePolling.add(pollingKey);

    const startTime = Date.now();
    const completedStates = new Set(['success', 'completed', 'validated', 'error', 'failed']);

    try {
      while (true) {
        const statusResult = await this.getValidationStatus(executionId);

        if (statusResult.success) {
          const status = (statusResult.data?.status || statusResult.data?.state || '')
            .toString()
            .toLowerCase();

          if (completedStates.has(status)) {
            const success = !['error', 'failed'].includes(status);
            return { success, finalStatus: status, data: statusResult.data };
          }
        } else if (statusResult.statusCode && statusResult.statusCode !== 404) {
          return { success: false, finalStatus: 'error', error: statusResult.error };
        }

        if (Date.now() - startTime > timeoutMs) {
          return {
            success: false,
            finalStatus: 'timeout',
            error: 'La validación tardó demasiado tiempo',
          };
        }

        await new Promise((resolve) => setTimeout(resolve, intervalMs));
      }
    } finally {
      this.activePolling.delete(pollingKey);
    }
  }

  // ===========================================
  // CONVERSIÓN
  // ===========================================

  async startConversion(executionId) {
    try {
      const response = await api.post(
        `/api/import/convert/${encodeURIComponent(executionId)}`
      );
      return { success: true, data: response?.data };
    } catch (error) {
      return {
        success: false,
        error:
          error?.response?.data?.detail ||
          error?.message ||
          'Error al iniciar conversión',
      };
    }
  }

  async getConversionStatus(executionId) {
    try {
      const response = await api.get(
        `/api/import/convert/${encodeURIComponent(executionId)}/status`
      );
      return { success: true, data: response?.data };
    } catch (error) {
      const statusCode = error?.response?.status;
      const message =
        error?.response?.data?.detail ||
        error?.message ||
        'Error al consultar estado de conversión';
      return { success: false, statusCode, error: message };
    }
  }

  async pollConversionStatus(executionId, options = {}) {
    const { intervalMs = 2000, timeoutMs = 300000 } = options;

    const pollingKey = `poll_conversion_${executionId}`;
    if (this.activePolling.has(pollingKey)) {
      throw new Error(`Ya hay un polling activo para conversión: ${executionId}`);
    }

    this.activePolling.add(pollingKey);

    const startTime = Date.now();
    const completedStates = new Set(['success', 'completed', 'converted', 'error', 'failed']);

    try {
      while (true) {
        const statusResult = await this.getConversionStatus(executionId);

        if (statusResult.success) {
          const status = (statusResult.data?.status || statusResult.data?.state || '')
            .toString()
            .toLowerCase();

          if (completedStates.has(status)) {
            const success = !['error', 'failed'].includes(status);
            return { success, finalStatus: status, data: statusResult.data };
          }
        } else if (statusResult.statusCode && statusResult.statusCode !== 404) {
          return { success: false, finalStatus: 'error', error: statusResult.error };
        }

        if (Date.now() - startTime > timeoutMs) {
          return {
            success: false,
            finalStatus: 'timeout',
            error: 'La conversión tardó demasiado tiempo',
          };
        }

        await new Promise((resolve) => setTimeout(resolve, intervalMs));
      }
    } finally {
      this.activePolling.delete(pollingKey);
    }
  }

  // ===========================================
  // PROCESO PRINCIPAL (validación + conversión coordinada)
  // ===========================================

  async validateCoordinatedFiles(executionId) {
    try {
      const coordinated = await this.getCoordinatedExecutions(executionId);
      if (!coordinated.success) {
        return { success: false, error: 'No se pudieron obtener archivos coordinados' };
      }

      const results = {
        libroDiario: { attempted: false, success: false, finalStatus: null, error: null, converted: false },
        sumasSaldos: { attempted: false, success: false, finalStatus: null, error: null },
      };

      // Libro Diario
      if (coordinated.data.libroDiario) {
        const ldId = coordinated.data.libroDiario.executionId;
        results.libroDiario.attempted = true;

        const startResult = await this.startValidation(ldId);
        if (startResult.success) {
          const pollResult = await this.pollValidationStatus(ldId, {
            intervalMs: 1500,
            timeoutMs: 180000,
          });
          results.libroDiario.success = pollResult.success;
          results.libroDiario.finalStatus = pollResult.finalStatus;
          results.libroDiario.error = pollResult.error;

          // Si validó, convertir
          if (pollResult.success) {
            const conversionResult = await this.startConversion(ldId);
            if (conversionResult.success) {
              const conversionPoll = await this.pollConversionStatus(ldId, {
                intervalMs: 2000,
                timeoutMs: 300000,
              });
              results.libroDiario.converted = conversionPoll.success;
              results.libroDiario.conversionStatus = conversionPoll.finalStatus;
              results.libroDiario.conversionError = conversionPoll.error;
            } else {
              results.libroDiario.conversionError = conversionResult.error;
            }
          }
        } else {
          results.libroDiario.error = startResult.error;
        }
      }

      // Sumas y Saldos (sin conversión)
      if (coordinated.data.sumasSaldos) {
        const ssId = coordinated.data.sumasSaldos.executionId;
        results.sumasSaldos.attempted = true;

        const startResult = await this.startValidation(ssId);
        if (startResult.success) {
          const pollResult = await this.pollValidationStatus(ssId, {
            intervalMs: 1500,
            timeoutMs: 180000,
          });
          results.sumasSaldos.success = pollResult.success;
          results.sumasSaldos.finalStatus = pollResult.finalStatus;
          results.sumasSaldos.error = pollResult.error;
        } else {
          results.sumasSaldos.error = startResult.error;
        }
      }

      // Resumen
      const ldValidated = !results.libroDiario.attempted || results.libroDiario.success;
      const ldConverted = !results.libroDiario.attempted || results.libroDiario.converted;
      const ssOk = !results.sumasSaldos.attempted || results.sumasSaldos.success;

      const overallSuccess = ldValidated && ldConverted && ssOk;

      const summary = {
        libroDiarioValidated: ldValidated,
        libroDiarioConverted: ldConverted,
        sumasSaldosOk: ssOk,
        overallSuccess,
        filesValidated: (results.libroDiario.attempted ? 1 : 0) + (results.sumasSaldos.attempted ? 1 : 0),
        filesSuccessful: (results.libroDiario.success ? 1 : 0) + (results.sumasSaldos.success ? 1 : 0),
        conversionAttempted: results.libroDiario.attempted,
        conversionSuccessful: results.libroDiario.converted,
      };

      return { success: overallSuccess, results, summary };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // ===========================================
  // MAPEOS (NUEVO)
  // ===========================================

  /**
   * Arranca el mapeo automático (si tu backend lo soporta).
   * POST /api/import/mapeo/{execution_id}?erp_hint=TXT/SAP|...
   */
  async startAutomaticMapeo(executionId, erpHint) {
    try {
      const cacheKey = `mapeo_start_${executionId}_${erpHint || 'none'}`;
      if (this.requestCache.has(cacheKey)) return this.requestCache.get(cacheKey);

      const { data } = await api.post(
        `/api/import/mapeo/${encodeURIComponent(executionId)}`,
        null,
        { params: erpHint ? { erp_hint: erpHint } : undefined }
      );
      const result = { success: true, ...data };
      this.requestCache.set(cacheKey, result);
      return result;
    } catch (e) {
      return { success: false, error: e?.response?.data?.detail || e.message };
    }
  }

  /**
   * GET /api/import/mapeo/{execution_id}/status
   */
  async getMapeoStatus(executionId) {
    try {
      const { data } = await api.get(
        `/api/import/mapeo/${encodeURIComponent(executionId)}/status`
      );
      return { success: true, ...data };
    } catch (e) {
      return { success: false, error: e?.response?.data?.detail || e.message };
    }
  }

  /**
   * Obtiene el detalle del mapeo de campos.
   * GET /api/import/mapeo/{execution_id}/fields-mapping
   * Devuelve el JSON tal cual (mapping_summary, mapped_fields, missing_fields)
   */
  async getFieldsMapping(executionId) {
    const cacheKey = `fields_mapping_${executionId}`;
    if (this.requestCache.has(cacheKey)) return this.requestCache.get(cacheKey);

    const { data } = await api.get(
      `/api/import/mapeo/${encodeURIComponent(executionId)}/fields-mapping`
    );
    // Normalizamos mínimos para evitar undefined en el front
    const normalized = {
      mapping_summary: data?.mapping_summary || {},
      mapped_fields: data?.mapped_fields || {},
      missing_fields: data?.missing_fields || [],
    };
    this.requestCache.set(cacheKey, normalized);
    return normalized;
  }

  /**
   * Aplica mapeo manual y regenera archivos/preview en backend.
   * POST /api/import/mapeo/{execution_id}/apply-manual-mapping
   * Body: { manual_mappings: { [dest_field]: "sourceColumn", ... } }
   */
  async applyManualMapping(executionId, manualMappings) {
    try {
      const body = { manual_mappings: manualMappings || {} };
      const { data } = await api.post(
        `/api/import/mapeo/${encodeURIComponent(executionId)}/apply-manual-mapping`,
        body
      );
      // Invalida cache de mapeo para que el siguiente GET refresque
      this.requestCache.delete(`fields_mapping_${executionId}`);
      return { success: true, ...data };
    } catch (e) {
      return { success: false, error: e?.response?.data?.detail || e.message };
    }
  }

  // ===========================================
  // UTILIDADES
  // ===========================================

  async getCoordinatedExecutions(executionId) {
    try {
      const ldId = executionId.endsWith('-ss') ? executionId.replace('-ss', '') : executionId;
      const ssId = executionId.endsWith('-ss') ? executionId : `${executionId}-ss`;

      const results = { libroDiario: null, sumasSaldos: null };

      try {
        const ldInfo = await this.getUploadInfo(ldId);
        if (ldInfo.success) results.libroDiario = { executionId: ldId, ...ldInfo.data };
      } catch {}

      try {
        const ssInfo = await this.getUploadInfo(ssId);
        if (ssInfo.success) results.sumasSaldos = { executionId: ssId, ...ssInfo.data };
      } catch {}

      return { success: true, data: results };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getUploadInfo(executionId) {
    try {
      const response = await api.get(
        `/api/import/upload/${encodeURIComponent(executionId)}/info`
      );
      return { success: true, data: response?.data };
    } catch (error) {
      return {
        success: false,
        error:
          error?.response?.data?.detail || error?.message || 'Error obteniendo información',
      };
    }
  }

  // ===========================================
  // PRIVADOS (subidas)
  // ===========================================

  async _uploadPrimaryLibroDiario(file, projectId, period, testType) {
    try {
      const formData = new FormData();
      formData.append('file', file, file.name);
      formData.append('project_id', projectId || '');
      formData.append('period', period || '');
      formData.append('test_type', testType);

      const response = await api.post('/api/import/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const data = response?.data || {};
      const executionId = data.execution_id || data.executionId || data.id;
      if (!executionId) {
        return { success: false, error: 'No se recibió execution_id del servidor', data };
      }
      return { success: true, executionId, data };
    } catch (error) {
      return {
        success: false,
        error:
          error?.response?.data?.detail ||
          error?.message ||
          'Error al subir archivo principal',
      };
    }
  }

  async _uploadAdditionalLibroDiarioFiles(files, parentExecutionId, projectId, period, testType) {
    const results = [];
    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append('file', file, file.name);
        formData.append('project_id', projectId || '');
        formData.append('period', period || '');
        formData.append('test_type', testType);
        formData.append('parent_execution_id', parentExecutionId);

        const response = await api.post('/api/import/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        const data = response?.data || {};
        const executionId = data.execution_id || data.executionId || data.id;

        results.push({ success: true, filename: file.name, executionId, data });
      } catch (error) {
        results.push({
          success: false,
          filename: file.name,
          error:
            error?.response?.data?.detail ||
            error?.message ||
            'Error al subir archivo',
        });
      }
    }
    return results;
  }

  async _uploadSumasSaldos(file, parentExecutionId, projectId, period) {
    try {
      const formData = new FormData();
      formData.append('file', file, file.name);
      formData.append('project_id', projectId || '');
      formData.append('period', period || '');
      formData.append('test_type', 'sumas_saldos_import');
      formData.append('parent_execution_id', parentExecutionId);

      const response = await api.post('/api/import/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const data = response?.data || {};
      const executionId = data.execution_id || data.executionId || data.id;
      if (!executionId) {
        return { success: false, error: 'No se recibió execution_id para Sumas y Saldos', data };
      }

      return { success: true, executionId, data };
    } catch (error) {
      return {
        success: false,
        error:
          error?.response?.data?.detail ||
          error?.message ||
          'Error al subir Sumas y Saldos',
      };
    }
  }

  // ===========================================
  // COMPATIBILIDAD / UTILIDAD
  // ===========================================

  async uploadLibroDiario(libroDiarioFiles, projectId, period, testType = 'libro_diario_import') {
    return this.uploadLibroDiarioYSumas(libroDiarioFiles, null, projectId, period, testType);
  }

  async getImportHistory() {
    // Placeholder; implementa si tu backend lo soporta
    return { success: true, executions: [] };
  }

  downloadFile(filename) {
    const link = document.createElement('a');
    link.href = `/api/import/download/${encodeURIComponent(filename)}`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

export default new ImportService();
