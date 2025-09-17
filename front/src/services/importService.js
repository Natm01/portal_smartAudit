// frontend/src/services/importService.js
import api from './api';

/**
 * ImportService - Versión limpia y organizada
 * 
 * Funcionalidades principales:
 * 1. Subida de archivos con IDs coordinados
 * 2. Validación de archivos
 * 3. Gestión de estado de validación
 * 4. Verificación de estructura de archivos
 */
class ImportService {
  
  // ===========================================
  // SUBIDA DE ARCHIVOS
  // ===========================================

  /**
   * Sube Libro Diario y opcionalmente Sumas y Saldos con IDs coordinados
   * Estructura de nombres: executionId_NombreArchivo_TipoArchivo.extensión
   * 
   * @param {File[]} libroDiarioFiles - Archivos de Libro Diario
   * @param {File|null} sumasSaldosFile - Archivo de Sumas y Saldos (opcional)
   * @param {string} projectId - ID del proyecto
   * @param {string} period - Período
   * @param {string} testType - Tipo de test
   * @returns {Promise<Object>} Resultado de la subida
   */
  async uploadLibroDiarioYSumas(libroDiarioFiles, sumasSaldosFile, projectId, period, testType = 'libro_diario_import') {
    try {
      console.log('🚀 Iniciando subida coordinada...');
      
      // Validar inputs
      if (!libroDiarioFiles || libroDiarioFiles.length === 0) {
        return { success: false, error: 'Debe adjuntar al menos un archivo de Libro Diario' };
      }

      // 1. Subir archivo principal de Libro Diario
      const primaryResult = await this._uploadPrimaryLibroDiario(
        libroDiarioFiles[0], projectId, period, testType
      );

      if (!primaryResult.success) {
        return primaryResult;
      }

      const executionIdLD = primaryResult.executionId;
      console.log(`✅ Libro Diario principal subido: ${executionIdLD}`);

      // 2. Subir archivos adicionales de Libro Diario (si los hay)
      const additionalResults = await this._uploadAdditionalLibroDiarioFiles(
        libroDiarioFiles.slice(1), executionIdLD, projectId, period, testType
      );

      // 3. Subir Sumas y Saldos (si existe)
      let sumasResult = null;
      if (sumasSaldosFile) {
        sumasResult = await this._uploadSumasSaldos(
          sumasSaldosFile, executionIdLD, projectId, period
        );
      }

      // 4. Preparar resultado final
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

      console.log('🎉 Subida coordinada completada:', result.summary);
      return result;

    } catch (error) {
      console.error('❌ Error en subida coordinada:', error);
      return { 
        success: false, 
        error: error?.response?.data?.detail || error?.message || 'Error al subir archivos' 
      };
    }
  }

  /**
   * Método de compatibilidad - solo Libro Diario
   */
  async uploadLibroDiario(libroDiarioFiles, projectId, period, testType = 'libro_diario_import') {
    return this.uploadLibroDiarioYSumas(libroDiarioFiles, null, projectId, period, testType);
  }

  // ===========================================
  // VALIDACIÓN DE ARCHIVOS
  // ===========================================

  /**
   * Inicia validación para un execution_id
   */
  async startValidation(executionId) {
    try {
      console.log(`🔍 Iniciando validación: ${executionId}`);
      
      const response = await api.post(`/api/import/validate/${encodeURIComponent(executionId)}`);
      
      console.log(`✅ Validación iniciada: ${executionId}`);
      return { success: true, data: response?.data };
      
    } catch (error) {
      console.error(`❌ Error iniciando validación ${executionId}:`, error);
      return { 
        success: false, 
        error: error?.response?.data?.detail || error?.message || 'Error al iniciar validación' 
      };
    }
  }

  /**
   * Consulta estado de validación
   */
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

  /**
   * Hace polling del estado de validación hasta completarse
   */
  async pollValidationStatus(executionId, options = {}) {
    const { intervalMs = 1200, timeoutMs = 120000 } = options;
    
    console.log(`⏳ Monitoreando validación: ${executionId}`);
    
    const startTime = Date.now();
    const completedStates = new Set(['success', 'completed', 'validated', 'error', 'failed']);

    while (true) {
      const statusResult = await this.getValidationStatus(executionId);
      
      if (statusResult.success) {
        const status = (statusResult.data?.status || statusResult.data?.state || '').toString().toLowerCase();
        
        if (completedStates.has(status)) {
          const success = !['error', 'failed'].includes(status);
          console.log(`${success ? '✅' : '❌'} Validación completada ${executionId}: ${status}`);
          
          return { 
            success, 
            finalStatus: status, 
            data: statusResult.data 
          };
        }
        
        // Log de progreso cada ~10 segundos
        const elapsed = Date.now() - startTime;
        if (elapsed % 10000 < intervalMs) {
          console.log(`⏳ Validando ${executionId}... (${Math.round(elapsed/1000)}s, estado: ${status})`);
        }
        
      } else if (statusResult.statusCode && statusResult.statusCode !== 404) {
        console.error(`❌ Error en validación ${executionId}:`, statusResult.error);
        return { success: false, finalStatus: 'error', error: statusResult.error };
      }

      // Verificar timeout
      if (Date.now() - startTime > timeoutMs) {
        console.warn(`⏰ Timeout en validación ${executionId} después de ${timeoutMs}ms`);
        return { 
          success: false, 
          finalStatus: 'timeout', 
          error: 'La validación tardó demasiado tiempo' 
        };
      }

      // Esperar antes del siguiente check
      await new Promise(resolve => setTimeout(resolve, intervalMs));
    }
  }

  /**
   * Valida archivos coordinados (LD + SS si existe) y convierte el LD
   */
  async validateCoordinatedFiles(executionId) {
    try {
      console.log(`🔍 Iniciando validación coordinada: ${executionId}`);

      // Obtener información de archivos coordinados
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
        console.log(`📄 Validando Libro Diario: ${ldId}`);
        
        results.libroDiario.attempted = true;
        
        const startResult = await this.startValidation(ldId);
        if (startResult.success) {
          const pollResult = await this.pollValidationStatus(ldId, { intervalMs: 1500, timeoutMs: 180000 });
          results.libroDiario.success = pollResult.success;
          results.libroDiario.finalStatus = pollResult.finalStatus;
          results.libroDiario.error = pollResult.error;

          // Si la validación del LD fue exitosa, iniciar conversión
          if (pollResult.success) {
            console.log(`🔄 Iniciando conversión del Libro Diario: ${ldId}`);
            
            try {
              const conversionResult = await this.startConversion(ldId);
              if (conversionResult.success) {
                console.log(`⏳ Monitoreando conversión del Libro Diario: ${ldId}`);
                const conversionPoll = await this.pollConversionStatus(ldId, { intervalMs: 2000, timeoutMs: 300000 });
                results.libroDiario.converted = conversionPoll.success;
                results.libroDiario.conversionStatus = conversionPoll.finalStatus;
                results.libroDiario.conversionError = conversionPoll.error;
                
                if (conversionPoll.success) {
                  console.log(`✅ Conversión del Libro Diario completada: ${ldId}`);
                } else {
                  console.log(`❌ Error en conversión del Libro Diario: ${conversionPoll.error}`);
                }
              } else {
                results.libroDiario.conversionError = conversionResult.error;
                console.log(`❌ No se pudo iniciar conversión del Libro Diario: ${conversionResult.error}`);
              }
            } catch (convError) {
              results.libroDiario.conversionError = convError.message;
              console.log(`❌ Error durante conversión del Libro Diario: ${convError.message}`);
            }
          }
        } else {
          results.libroDiario.error = startResult.error;
        }
      }

      // Validar Sumas y Saldos (SIN conversión)
      if (coordinated.data.sumasSaldos) {
        const ssId = coordinated.data.sumasSaldos.executionId;
        console.log(`📊 Validando Sumas y Saldos: ${ssId}`);
        
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
      
      // El éxito general requiere validación + conversión del LD (si existe) y validación del SS (si existe)
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

      console.log(`🎯 Validación y conversión coordinada completada:`, summary);

      return { success: overallSuccess, results, summary };

    } catch (error) {
      console.error(`❌ Error en validación coordinada ${executionId}:`, error);
      return { success: false, error: error.message };
    }
  }

  // ===========================================
  // CONVERSIÓN DE ARCHIVOS (SOLO LIBRO DIARIO)
  // ===========================================

  /**
   * Inicia conversión para un execution_id (solo Libro Diario)
   */
  async startConversion(executionId) {
    try {
      console.log(`🔄 Iniciando conversión: ${executionId}`);
      
      const response = await api.post(`/api/import/convert/${encodeURIComponent(executionId)}`);
      
      console.log(`✅ Conversión iniciada: ${executionId}`);
      return { success: true, data: response?.data };
      
    } catch (error) {
      console.error(`❌ Error iniciando conversión ${executionId}:`, error);
      return { 
        success: false, 
        error: error?.response?.data?.detail || error?.message || 'Error al iniciar conversión' 
      };
    }
  }

  /**
   * Consulta estado de conversión
   */
  async getConversionStatus(executionId) {
    try {
      const response = await api.get(`/api/import/convert/${encodeURIComponent(executionId)}/status`);
      return { success: true, data: response?.data };
      
    } catch (error) {
      const statusCode = error?.response?.status;
      const message = error?.response?.data?.detail || error?.message || 'Error al consultar estado de conversión';
      
      return { success: false, statusCode, error: message };
    }
  }

  /**
   * Hace polling del estado de conversión hasta completarse
   */
  async pollConversionStatus(executionId, options = {}) {
    const { intervalMs = 2000, timeoutMs = 300000 } = options; // 5 minutos timeout por defecto
    
    console.log(`⏳ Monitoreando conversión: ${executionId}`);
    
    const startTime = Date.now();
    const completedStates = new Set(['success', 'completed', 'converted', 'error', 'failed']);

    while (true) {
      const statusResult = await this.getConversionStatus(executionId);
      
      if (statusResult.success) {
        const status = (statusResult.data?.status || statusResult.data?.state || '').toString().toLowerCase();
        
        if (completedStates.has(status)) {
          const success = !['error', 'failed'].includes(status);
          console.log(`${success ? '✅' : '❌'} Conversión completada ${executionId}: ${status}`);
          
          return { 
            success, 
            finalStatus: status, 
            data: statusResult.data 
          };
        }
        
        // Log de progreso cada ~10 segundos
        const elapsed = Date.now() - startTime;
        if (elapsed % 10000 < intervalMs) {
          console.log(`🔄 Convirtiendo ${executionId}... (${Math.round(elapsed/1000)}s, estado: ${status})`);
        }
        
      } else if (statusResult.statusCode && statusResult.statusCode !== 404) {
        console.error(`❌ Error en conversión ${executionId}:`, statusResult.error);
        return { success: false, finalStatus: 'error', error: statusResult.error };
      }

      // Verificar timeout
      if (Date.now() - startTime > timeoutMs) {
        console.warn(`⏰ Timeout en conversión ${executionId} después de ${timeoutMs}ms`);
        return { 
          success: false, 
          finalStatus: 'timeout', 
          error: 'La conversión tardó demasiado tiempo' 
        };
      }

      // Esperar antes del siguiente check
      await new Promise(resolve => setTimeout(resolve, intervalMs));
    }
  }

  /**
   * Obtiene información de archivos coordinados
   */
  async getCoordinatedExecutions(executionId) {
    try {
      console.log(`🔍 Obteniendo archivos coordinados: ${executionId}`);
      
      // Determinar IDs relacionados
      const ldId = executionId.endsWith('-ss') ? executionId.replace('-ss', '') : executionId;
      const ssId = executionId.endsWith('-ss') ? executionId : `${executionId}-ss`;

      const results = {
        libroDiario: null,
        sumasSaldos: null
      };

      // Obtener Libro Diario
      try {
        const ldInfo = await this.getUploadInfo(ldId);
        if (ldInfo.success) {
          results.libroDiario = { executionId: ldId, ...ldInfo.data };
        }
      } catch (error) {
        console.log(`ℹ️  LD no encontrado: ${ldId}`);
      }

      // Obtener Sumas y Saldos
      try {
        const ssInfo = await this.getUploadInfo(ssId);
        if (ssInfo.success) {
          results.sumasSaldos = { executionId: ssId, ...ssInfo.data };
        }
      } catch (error) {
        console.log(`ℹ️  SS no encontrado: ${ssId}`);
      }

      console.log(`📋 Archivos coordinados encontrados:`, {
        LD: !!results.libroDiario,
        SS: !!results.sumasSaldos
      });

      return { success: true, data: results };

    } catch (error) {
      console.error(`❌ Error obteniendo archivos coordinados ${executionId}:`, error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Obtiene información de un upload específico
   */
  async getUploadInfo(executionId) {
    try {
      const response = await api.get(`/api/import/upload/${encodeURIComponent(executionId)}/info`);
      return { success: true, data: response?.data };
      
    } catch (error) {
      return { 
        success: false, 
        error: error?.response?.data?.detail || error?.message || 'Error obteniendo información' 
      };
    }
  }

  /**
   * Verifica la estructura de nombres de archivos
   */
  async verifyFileNaming(executionId) {
    try {
      const response = await api.get(`/api/debug/execution/${encodeURIComponent(executionId)}/file-structure`);
      return { success: true, data: response?.data };
      
    } catch (error) {
      console.error(`❌ Error verificando estructura de archivos ${executionId}:`, error);
      return { success: false, error: error.message };
    }
  }

  // ===========================================
  // MÉTODOS PRIVADOS
  // ===========================================

  /**
   * Sube el archivo principal de Libro Diario
   */
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
          error: 'No se recibió execution_id del servidor', 
          data 
        };
      }

      return { success: true, executionId, data };

    } catch (error) {
      console.error('❌ Error subiendo LD principal:', error);
      return { 
        success: false, 
        error: error?.response?.data?.detail || error?.message || 'Error al subir archivo principal' 
      };
    }
  }

  /**
   * Sube archivos adicionales de Libro Diario
   */
  async _uploadAdditionalLibroDiarioFiles(files, parentExecutionId, projectId, period, testType) {
    const results = [];

    for (const [index, file] of files.entries()) {
      try {
        console.log(`📤 Subiendo archivo adicional ${index + 1}/${files.length}: ${file.name}`);
        
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

        console.log(`✅ Archivo adicional subido: ${file.name} -> ${executionId}`);

      } catch (error) {
        console.error(`❌ Error subiendo archivo adicional ${file.name}:`, error);
        
        results.push({
          success: false,
          filename: file.name,
          error: error?.response?.data?.detail || error?.message || 'Error al subir archivo'
        });
      }
    }

    return results;
  }

  /**
   * Sube archivo de Sumas y Saldos
   */
  async _uploadSumasSaldos(file, parentExecutionId, projectId, period) {
    try {
      console.log(`📤 Subiendo Sumas y Saldos: ${file.name}`);
      
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
          error: 'No se recibió execution_id para Sumas y Saldos', 
          data 
        };
      }

      console.log(`✅ Sumas y Saldos subido: ${executionId}`);

      // Verificar coordinación de IDs
      const expectedId = `${parentExecutionId}-ss`;
      if (executionId === expectedId) {
        console.log(`✅ Coordinación de IDs confirmada: ${executionId}`);
      } else {
        console.warn(`⚠️  ID no coordinado. Esperado: ${expectedId}, Obtenido: ${executionId}`);
      }

      return { success: true, executionId, data };

    } catch (error) {
      console.error('❌ Error subiendo Sumas y Saldos:', error);
      return { 
        success: false, 
        error: error?.response?.data?.detail || error?.message || 'Error al subir Sumas y Saldos' 
      };
    }
  }

  // ===========================================
  // MÉTODOS DE COMPATIBILIDAD
  // ===========================================

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