// frontend/src/services/importService.js - SOLO CAMBIOS MÃNIMOS
import api from './api';

/**
 * ImportService - Solo con los cambios mÃ­nimos para evitar mÃºltiples llamadas
 */
class ImportService {
  
  constructor() {
    // ÃšNICO CAMBIO: Cache para evitar mÃºltiples llamadas
    this.requestCache = new Map();
    this.activePolling = new Set();
  }

  // ===========================================
  // SUBIDA DE ARCHIVOS - SIN CAMBIOS
  // ===========================================

  async uploadLibroDiarioYSumas(libroDiarioFiles, sumasSaldosFile, projectId, period, testType = 'libro_diario_import') {
    try {
      console.log('ðŸš€ Iniciando subida coordinada...');
      
      if (!libroDiarioFiles || libroDiarioFiles.length === 0) {
        return { success: false, error: 'Debe adjuntar al menos un archivo de Libro Diario' };
      }

      const primaryResult = await this._uploadPrimaryLibroDiario(
        libroDiarioFiles[0], projectId, period, testType
      );

      if (!primaryResult.success) {
        return primaryResult;
      }

      const executionIdLD = primaryResult.executionId;
      console.log(`âœ… Libro Diario principal subido: ${executionIdLD}`);

      const additionalResults = await this._uploadAdditionalLibroDiarioFiles(
        libroDiarioFiles.slice(1), executionIdLD, projectId, period, testType
      );

      let sumasResult = null;
      if (sumasSaldosFile) {
        sumasResult = await this._uploadSumasSaldos(
          sumasSaldosFile, executionIdLD, projectId, period
        );
      }

      const result = {
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
            sumasSaldos: sumasResult?.executionId || null
          }
        }
      };

      console.log('ðŸŽ‰ Subida coordinada completada:', result.summary);
      return result;

    } catch (error) {
      console.error('âŒ Error en subida coordinada:', error);
      return { 
        success: false, 
        error: error?.response?.data?.detail || error?.message || 'Error al subir archivos' 
      };
    }
  }

  // ===========================================
  // VALIDACIÃ“N - CON CACHE PARA EVITAR MÃšLTIPLES LLAMADAS
  // ===========================================

  async startValidation(executionId) {
    try {
      // CAMBIO: Evitar llamadas duplicadas
      const cacheKey = `validate_start_${executionId}`;
      if (this.requestCache.has(cacheKey)) {
        console.log(`ðŸ“‹ Usando resultado cacheado para validaciÃ³n: ${executionId}`);
        return this.requestCache.get(cacheKey);
      }

      console.log(`ðŸ” Iniciando validaciÃ³n: ${executionId}`);
      
      const response = await api.post(`/api/import/validate/${encodeURIComponent(executionId)}`);
      
      const result = { success: true, data: response?.data };
      this.requestCache.set(cacheKey, result);
      
      console.log(`âœ… ValidaciÃ³n iniciada: ${executionId}`);
      return result;
      
    } catch (error) {
      console.error(`âŒ Error iniciando validaciÃ³n ${executionId}:`, error);
      return { 
        success: false, 
        error: error?.response?.data?.detail || error?.message || 'Error al iniciar validaciÃ³n' 
      };
    }
  }

  async getValidationStatus(executionId) {
    try {
      const response = await api.get(`/api/import/validate/${encodeURIComponent(executionId)}/status`);
      return { success: true, data: response?.data };
      
    } catch (error) {
      const statusCode = error?.response?.status;
      const message = error?.response?.data?.detail || error?.message || 'Error al consultar estado';
      
      return { success: false, statusCode, error: message };
    }
  }

  async pollValidationStatus(executionId, options = {}) {
    const { intervalMs = 1200, timeoutMs = 120000 } = options;
    
    // CAMBIO: Evitar polling duplicado
    const pollingKey = `poll_validation_${executionId}`;
    if (this.activePolling.has(pollingKey)) {
      throw new Error(`Ya hay un polling activo para validaciÃ³n: ${executionId}`);
    }

    this.activePolling.add(pollingKey);
    console.log(`â³ Monitoreando validaciÃ³n: ${executionId}`);
    
    const startTime = Date.now();
    const completedStates = new Set(['success', 'completed', 'validated', 'error', 'failed']);

    try {
      while (true) {
        const statusResult = await this.getValidationStatus(executionId);
        
        if (statusResult.success) {
          const status = (statusResult.data?.status || statusResult.data?.state || '').toString().toLowerCase();
          
          if (completedStates.has(status)) {
            const success = !['error', 'failed'].includes(status);
            console.log(`${success ? 'âœ…' : 'âŒ'} ValidaciÃ³n completada ${executionId}: ${status}`);
            
            return { 
              success, 
              finalStatus: status, 
              data: statusResult.data 
            };
          }
          
          const elapsed = Date.now() - startTime;
          if (elapsed % 10000 < intervalMs) {
            console.log(`â³ Validando ${executionId}... (${Math.round(elapsed/1000)}s, estado: ${status})`);
          }
          
        } else if (statusResult.statusCode && statusResult.statusCode !== 404) {
          console.error(`âŒ Error en validaciÃ³n ${executionId}:`, statusResult.error);
          return { success: false, finalStatus: 'error', error: statusResult.error };
        }

        if (Date.now() - startTime > timeoutMs) {
          console.warn(`â° Timeout en validaciÃ³n ${executionId} despuÃ©s de ${timeoutMs}ms`);
          return { 
            success: false, 
            finalStatus: 'timeout', 
            error: 'La validaciÃ³n tardÃ³ demasiado tiempo' 
          };
        }

        await new Promise(resolve => setTimeout(resolve, intervalMs));
      }
    } finally {
      this.activePolling.delete(pollingKey);
    }
  }

  // ===========================================
  // CONVERSIÃ“N - SIN CAMBIOS
  // ===========================================

  async startConversion(executionId) {
    try {
      console.log(`ðŸ”„ Iniciando conversiÃ³n: ${executionId}`);
      
      const response = await api.post(`/api/import/convert/${encodeURIComponent(executionId)}`);
      
      console.log(`âœ… ConversiÃ³n iniciada: ${executionId}`);
      return { success: true, data: response?.data };
      
    } catch (error) {
      console.error(`âŒ Error iniciando conversiÃ³n ${executionId}:`, error);
      return { 
        success: false, 
        error: error?.response?.data?.detail || error?.message || 'Error al iniciar conversiÃ³n' 
      };
    }
  }

  async getConversionStatus(executionId) {
    try {
      const response = await api.get(`/api/import/convert/${encodeURIComponent(executionId)}/status`);
      return { success: true, data: response?.data };
      
    } catch (error) {
      const statusCode = error?.response?.status;
      const message = error?.response?.data?.detail || error?.message || 'Error al consultar estado de conversiÃ³n';
      
      return { success: false, statusCode, error: message };
    }
  }

  async pollConversionStatus(executionId, options = {}) {
    const { intervalMs = 2000, timeoutMs = 300000 } = options;
    
    // CAMBIO: Evitar polling duplicado
    const pollingKey = `poll_conversion_${executionId}`;
    if (this.activePolling.has(pollingKey)) {
      throw new Error(`Ya hay un polling activo para conversiÃ³n: ${executionId}`);
    }

    this.activePolling.add(pollingKey);
    console.log(`â³ Monitoreando conversiÃ³n: ${executionId}`);
    
    const startTime = Date.now();
    const completedStates = new Set(['success', 'completed', 'converted', 'error', 'failed']);

    try {
      while (true) {
        const statusResult = await this.getConversionStatus(executionId);
        
        if (statusResult.success) {
          const status = (statusResult.data?.status || statusResult.data?.state || '').toString().toLowerCase();
          
          if (completedStates.has(status)) {
            const success = !['error', 'failed'].includes(status);
            console.log(`${success ? 'âœ…' : 'âŒ'} ConversiÃ³n completada ${executionId}: ${status}`);
            
            return { 
              success, 
              finalStatus: status, 
              data: statusResult.data 
            };
          }
          
          const elapsed = Date.now() - startTime;
          if (elapsed % 10000 < intervalMs) {
            console.log(`ðŸ”„ Convirtiendo ${executionId}... (${Math.round(elapsed/1000)}s, estado: ${status})`);
          }
          
        } else if (statusResult.statusCode && statusResult.statusCode !== 404) {
          console.error(`âŒ Error en conversiÃ³n ${executionId}:`, statusResult.error);
          return { success: false, finalStatus: 'error', error: statusResult.error };
        }

        if (Date.now() - startTime > timeoutMs) {
          console.warn(`â° Timeout en conversiÃ³n ${executionId} despuÃ©s de ${timeoutMs}ms`);
          return { 
            success: false, 
            finalStatus: 'timeout', 
            error: 'La conversiÃ³n tardÃ³ demasiado tiempo' 
          };
        }

        await new Promise(resolve => setTimeout(resolve, intervalMs));
      }
    } finally {
      this.activePolling.delete(pollingKey);
    }
  }

  // ===========================================
  // PROCESO PRINCIPAL - SIN CAMBIOS
  // ===========================================

  async validateCoordinatedFiles(executionId) {
    try {
      console.log(`ðŸ” Iniciando validaciÃ³n coordinada: ${executionId}`);

      const coordinated = await this.getCoordinatedExecutions(executionId);
      if (!coordinated.success) {
        return { success: false, error: 'No se pudieron obtener archivos coordinados' };
      }

      const results = {
        libroDiario: { attempted: false, success: false, finalStatus: null, error: null, converted: false },
        sumasSaldos: { attempted: false, success: false, finalStatus: null, error: null }
      };

      // Validar Libro Diario
      if (coordinated.data.libroDiario) {
        const ldId = coordinated.data.libroDiario.executionId;
        console.log(`ðŸ“„ Validando Libro Diario: ${ldId}`);
        
        results.libroDiario.attempted = true;
        
        const startResult = await this.startValidation(ldId);
        if (startResult.success) {
          const pollResult = await this.pollValidationStatus(ldId, { intervalMs: 1500, timeoutMs: 180000 });
          results.libroDiario.success = pollResult.success;
          results.libroDiario.finalStatus = pollResult.finalStatus;
          results.libroDiario.error = pollResult.error;

          // Si la validaciÃ³n del LD fue exitosa, iniciar conversiÃ³n
          if (pollResult.success) {
            console.log(`ðŸ”„ Iniciando conversiÃ³n del Libro Diario: ${ldId}`);
            
            try {
              const conversionResult = await this.startConversion(ldId);
              if (conversionResult.success) {
                console.log(`â³ Monitoreando conversiÃ³n del Libro Diario: ${ldId}`);
                const conversionPoll = await this.pollConversionStatus(ldId, { intervalMs: 2000, timeoutMs: 300000 });
                results.libroDiario.converted = conversionPoll.success;
                results.libroDiario.conversionStatus = conversionPoll.finalStatus;
                results.libroDiario.conversionError = conversionPoll.error;
                
                if (conversionPoll.success) {
                  console.log(`âœ… ConversiÃ³n del Libro Diario completada: ${ldId}`);
                } else {
                  console.log(`âŒ Error en conversiÃ³n del Libro Diario: ${conversionPoll.error}`);
                }
              } else {
                results.libroDiario.conversionError = conversionResult.error;
                console.log(`âŒ No se pudo iniciar conversiÃ³n del Libro Diario: ${conversionResult.error}`);
              }
            } catch (convError) {
              results.libroDiario.conversionError = convError.message;
              console.log(`âŒ Error durante conversiÃ³n del Libro Diario: ${convError.message}`);
            }
          }
        } else {
          results.libroDiario.error = startResult.error;
        }
      }

      // Validar Sumas y Saldos (SIN conversiÃ³n)
      if (coordinated.data.sumasSaldos) {
        const ssId = coordinated.data.sumasSaldos.executionId;
        console.log(`ðŸ“Š Validando Sumas y Saldos: ${ssId}`);
        
        results.sumasSaldos.attempted = true;
        
        const startResult = await this.startValidation(ssId);
        if (startResult.success) {
          const pollResult = await this.pollValidationStatus(ssId, { intervalMs: 1500, timeoutMs: 180000 });
          results.sumasSaldos.success = pollResult.success;
          results.sumasSaldos.finalStatus = pollResult.finalStatus;
          results.sumasSaldos.error = pollResult.error;
        } else {
          results.sumasSaldos.error = startResult.error;
        }
      }

      // Evaluar resultado general
      const ldValidated = !results.libroDiario.attempted || results.libroDiario.success;
      const ldConverted = !results.libroDiario.attempted || results.libroDiario.converted;
      const ssOk = !results.sumasSaldos.attempted || results.sumasSaldos.success;
      
      const overallSuccess = ldValidated && ldConverted && ssOk;

      const summary = {
        libroDiarioValidated: ldValidated,
        libroDiarioConverted: ldConverted,
        sumasSaldosOk: ssOk,
        overallSuccess: overallSuccess,
        filesValidated: (results.libroDiario.attempted ? 1 : 0) + (results.sumasSaldos.attempted ? 1 : 0),
        filesSuccessful: (results.libroDiario.success ? 1 : 0) + (results.sumasSaldos.success ? 1 : 0),
        conversionAttempted: results.libroDiario.attempted,
        conversionSuccessful: results.libroDiario.converted
      };

      console.log(`ðŸŽ¯ ValidaciÃ³n y conversiÃ³n coordinada completada:`, summary);

      return { success: overallSuccess, results, summary };

    } catch (error) {
      console.error(`âŒ Error en validaciÃ³n coordinada ${executionId}:`, error);
      return { success: false, error: error.message };
    }
  }

  // ===========================================
  // MÃ‰TODOS DE UTILIDAD - SIN CAMBIOS
  // ===========================================

  async getCoordinatedExecutions(executionId) {
    try {
      console.log(`ðŸ” Obteniendo archivos coordinados: ${executionId}`);
      
      const ldId = executionId.endsWith('-ss') ? executionId.replace('-ss', '') : executionId;
      const ssId = executionId.endsWith('-ss') ? executionId : `${executionId}-ss`;

      const results = {
        libroDiario: null,
        sumasSaldos: null
      };

      try {
        const ldInfo = await this.getUploadInfo(ldId);
        if (ldInfo.success) {
          results.libroDiario = { executionId: ldId, ...ldInfo.data };
        }
      } catch (error) {
        console.log(`â„¹ï¸  LD no encontrado: ${ldId}`);
      }

      try {
        const ssInfo = await this.getUploadInfo(ssId);
        if (ssInfo.success) {
          results.sumasSaldos = { executionId: ssId, ...ssInfo.data };
        }
      } catch (error) {
        console.log(`â„¹ï¸  SS no encontrado: ${ssId}`);
      }

      console.log(`ðŸ“‹ Archivos coordinados encontrados:`, {
        LD: !!results.libroDiario,
        SS: !!results.sumasSaldos
      });

      return { success: true, data: results };

    } catch (error) {
      console.error(`âŒ Error obteniendo archivos coordinados ${executionId}:`, error);
      return { success: false, error: error.message };
    }
  }

  async getUploadInfo(executionId) {
    try {
      const response = await api.get(`/api/import/upload/${encodeURIComponent(executionId)}/info`);
      return { success: true, data: response?.data };
      
    } catch (error) {
      return { 
        success: false, 
        error: error?.response?.data?.detail || error?.message || 'Error obteniendo informaciÃ³n' 
      };
    }
  }

  // ===========================================
  // MÃ‰TODOS PRIVADOS - SIN CAMBIOS
  // ===========================================

  async _uploadPrimaryLibroDiario(file, projectId, period, testType) {
    try {
      const formData = new FormData();
      formData.append('file', file, file.name);
      formData.append('project_id', projectId || '');
      formData.append('period', period || '');
      formData.append('test_type', testType);

      const response = await api.post('/api/import/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const data = response?.data || {};
      const executionId = data.execution_id || data.executionId || data.id;

      if (!executionId) {
        return { 
          success: false, 
          error: 'No se recibiÃ³ execution_id del servidor', 
          data 
        };
      }

      return { success: true, executionId, data };

    } catch (error) {
      console.error('âŒ Error subiendo LD principal:', error);
      return { 
        success: false, 
        error: error?.response?.data?.detail || error?.message || 'Error al subir archivo principal' 
      };
    }
  }

  async _uploadAdditionalLibroDiarioFiles(files, parentExecutionId, projectId, period, testType) {
    const results = [];

    for (const [index, file] of files.entries()) {
      try {
        console.log(`ðŸ“¤ Subiendo archivo adicional ${index + 1}/${files.length}: ${file.name}`);
        
        const formData = new FormData();
        formData.append('file', file, file.name);
        formData.append('project_id', projectId || '');
        formData.append('period', period || '');
        formData.append('test_type', testType);
        formData.append('parent_execution_id', parentExecutionId);

        const response = await api.post('/api/import/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });

        const data = response?.data || {};
        const executionId = data.execution_id || data.executionId || data.id;

        results.push({
          success: true,
          filename: file.name,
          executionId: executionId,
          data: data
        });

        console.log(`âœ… Archivo adicional subido: ${file.name} -> ${executionId}`);

      } catch (error) {
        console.error(`âŒ Error subiendo archivo adicional ${file.name}:`, error);
        
        results.push({
          success: false,
          filename: file.name,
          error: error?.response?.data?.detail || error?.message || 'Error al subir archivo'
        });
      }
    }

    return results;
  }

  async _uploadSumasSaldos(file, parentExecutionId, projectId, period) {
    try {
      console.log(`ðŸ“¤ Subiendo Sumas y Saldos: ${file.name}`);
      
      const formData = new FormData();
      formData.append('file', file, file.name);
      formData.append('project_id', projectId || '');
      formData.append('period', period || '');
      formData.append('test_type', 'sumas_saldos_import');
      formData.append('parent_execution_id', parentExecutionId);

      const response = await api.post('/api/import/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const data = response?.data || {};
      const executionId = data.execution_id || data.executionId || data.id;

      if (!executionId) {
        return { 
          success: false, 
          error: 'No se recibiÃ³ execution_id para Sumas y Saldos', 
          data 
        };
      }

      console.log(`âœ… Sumas y Saldos subido: ${executionId}`);

      const expectedId = `${parentExecutionId}-ss`;
      if (executionId === expectedId) {
        console.log(`âœ… CoordinaciÃ³n de IDs confirmada: ${executionId}`);
      } else {
        console.warn(`âš ï¸  ID no coordinado. Esperado: ${expectedId}, Obtenido: ${executionId}`);
      }

      return { success: true, executionId, data };

    } catch (error) {
      console.error('âŒ Error subiendo Sumas y Saldos:', error);
      return { 
        success: false, 
        error: error?.response?.data?.detail || error?.message || 'Error al subir Sumas y Saldos' 
      };
    }
  }

  // ===========================================
  // MÃ‰TODOS DE COMPATIBILIDAD - SIN CAMBIOS
  // ===========================================

  async uploadLibroDiario(libroDiarioFiles, projectId, period, testType = 'libro_diario_import') {
    return this.uploadLibroDiarioYSumas(libroDiarioFiles, null, projectId, period, testType);
  }

  async getImportHistory() {
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