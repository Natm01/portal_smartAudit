// frontend/src/components/ImportForm/ImportForm.jsx
import React, { useState } from 'react';

const ImportForm = ({ projects, onSubmit, loading }) => {
  const [formData, setFormData] = useState({
    projectId: '',
    fechaInicio: '',
    fechaFin: '',
    libroDiarioFiles: [],
    sumasSaldosFile: null,
  });
  const [dragActive, setDragActive] = useState({ libroDiario: false, sumasSaldos: false });
  const [errors, setErrors] = useState({});

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: null }));
  };

  const handleDrag = (e, type) => {
    e.preventDefault(); e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(prev => ({ ...prev, [type]: true }));
    else if (e.type === 'dragleave') setDragActive(prev => ({ ...prev, [type]: false }));
  };

  const handleDrop = (e, type) => {
    e.preventDefault(); e.stopPropagation();
    setDragActive(prev => ({ ...prev, [type]: false }));
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      if (type === 'libroDiario') {
        const files = Array.from(e.dataTransfer.files);
        handleMultipleFileSelect(files, type);
      } else {
        const file = e.dataTransfer.files[0];
        handleFileSelect(file, type);
      }
    }
  };

  const handleFileSelect = (file, type) => {
    const allowedTypes = ['.csv', '.txt', '.xls', '.xlsx'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedTypes.includes(fileExtension)) {
      setErrors(prev => ({ ...prev, [type]: 'Tipo de archivo no válido. Formatos permitidos: CSV, TXT, XLS, XLSX' }));
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setErrors(prev => ({ ...prev, [type]: 'El archivo es demasiado grande. Tamaño máximo: 50MB' }));
      return;
    }
    if (type === 'libroDiario') {
      setFormData(prev => ({ ...prev, libroDiarioFiles: [...prev.libroDiarioFiles, file] }));
    } else {
      setFormData(prev => ({ ...prev, sumasSaldosFile: file }));
    }
    setErrors(prev => ({ ...prev, [type]: null }));
  };

  const handleMultipleFileSelect = (files, type) => {
    const allowedTypes = ['.csv', '.txt', '.xls', '.xlsx'];
    const validFiles = [];
    const invalidFiles = [];
    files.forEach(file => {
      const ext = '.' + file.name.split('.').pop().toLowerCase();
      if (!allowedTypes.includes(ext)) invalidFiles.push(file.name);
      else if (file.size > 50 * 1024 * 1024) invalidFiles.push(`${file.name} (demasiado grande)`);
      else validFiles.push(file);
    });
    if (invalidFiles.length > 0) {
      setErrors(prev => ({ ...prev, [type]: `Archivos no válidos: ${invalidFiles.join(', ')}` }));
    }
    if (validFiles.length > 0) {
      setFormData(prev => ({ ...prev, libroDiarioFiles: [...prev.libroDiarioFiles, ...validFiles] }));
      setErrors(prev => ({ ...prev, [type]: null }));
    }
  };

  const removeFile = (index, type) => {
    if (type === 'libroDiario') {
      setFormData(prev => ({ ...prev, libroDiarioFiles: prev.libroDiarioFiles.filter((_, i) => i !== index) }));
    } else {
      setFormData(prev => ({ ...prev, sumasSaldosFile: null }));
    }
  };

  const getFileTypeBadge = (filename) => {
    const extension = filename.split('.').pop().toLowerCase();
    const colors = { txt: 'bg-blue-100 text-blue-600', csv: 'bg-orange-100 text-orange-600', xls: 'bg-green-100 text-green-600', xlsx: 'bg-green-100 text-green-600' };
    return <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${colors[extension] || 'bg-gray-100 text-gray-800'}`}>{extension.toUpperCase()}</span>;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const newErrors = {};
    if (!formData.projectId) newErrors.projectId = 'Debe seleccionar un proyecto';
    if (!formData.fechaInicio) newErrors.fechaInicio = 'La fecha de inicio es requerida';
    if (!formData.fechaFin) newErrors.fechaFin = 'La fecha de fin es requerida';
    if (formData.fechaInicio && formData.fechaFin && formData.fechaInicio > formData.fechaFin) {
      newErrors.fechaFin = 'La fecha de fin debe ser posterior a la fecha de inicio';
    }
    if (formData.libroDiarioFiles.length === 0) newErrors.libroDiario = 'Debe seleccionar al menos un archivo de Libro Diario';

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    const period = `${formData.fechaInicio} a ${formData.fechaFin}`;
    onSubmit({ ...formData, period });
  };

  const handleDateChange = (field, value) => {
    if (value) {
      const parts = value.split('-');
      if (parts[0] && parts[0].length > 4) { parts[0] = parts[0].substring(0, 4); value = parts.join('-'); }
      handleInputChange(field, value);
    }
  };

  const FileDropZone = ({ type, label, files, isMultiple = false, error, required = false, extraHint = null }) => {
    const isDragging = dragActive[type];
    const hasFiles = isMultiple ? files.length > 0 : files !== null;
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label} {required && <span className="text-red-500">*</span>}
        </label>
        <div
          className={`relative min-h-[150px] border-2 border-dashed rounded-lg transition-all ${
            isDragging ? 'border-purple-400 bg-purple-50' : error ? 'border-red-300 bg-red-50' : 'border-gray-300 hover:border-purple-400 hover:bg-gray-50'
          }`}
          onDragEnter={(e) => handleDrag(e, type)}
          onDragLeave={(e) => handleDrag(e, type)}
          onDragOver={(e) => handleDrag(e, type)}
          onDrop={(e) => handleDrop(e, type)}
        >
          <input
            type="file"
            multiple={isMultiple}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            accept=".csv,.txt,.xls,.xlsx"
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                if (isMultiple) {
                  const filesArray = Array.from(e.target.files);
                  handleMultipleFileSelect(filesArray, type);
                } else {
                  handleFileSelect(e.target.files[0], type);
                }
              }
            }}
          />
          <div className="p-4">
            {!hasFiles ? (
              <div className="flex flex-col items-center justify-center h-[100px] space-y-2">
                <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <div className="text-center">
                  <p className="text-sm text-gray-600">
                    <span className="font-medium text-purple-600">Subir {isMultiple ? 'archivos' : 'archivo'}</span> o arrastrar aquí
                  </p>
                  <p className="text-xs text-gray-500 mt-1">CSV, TXT, XLS, XLSX</p>
                  {extraHint && <p className="text-[10px] text-gray-400 mt-1">{extraHint}</p>}
                </div>
              </div>
            ) : (
              <div className="space-y-2 max-h-[100px] overflow-y-auto">
                {isMultiple ? (
                  files.map((file, index) => (
                    <div key={index} className="flex items-center justify-between bg-gray-50 p-2 rounded-lg group hover:bg-gray-100 transition-colors">
                      <div className="flex items-center space-x-2 flex-1 min-w-0">
                        <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M9 2a2 2 0 00-2 2v8a2 2 0 002 2h6a2 2 0 002-2V6.414A2 2 0 0016.414 5L14 2.586A2 2 0 0012.586 2H9z" />
                          <path d="M3 8a2 2 0 012-2v10h8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                        </svg>
                        <span className="text-sm text-gray-700 truncate">{file.name}</span>
                        {getFileTypeBadge(file.name)}
                        <span className="text-xs text-gray-500">({(file.size / 1024).toFixed(1)} KB)</span>
                      </div>
                      <button type="button" onClick={() => removeFile(index, type)} className="ml-2 text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"></path>
                        </svg>
                      </button>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center justify-between bg-gray-50 p-2 rounded-lg group hover:bg-gray-100 transition-colors">
                    <div className="flex items-center space-x-2 flex-1 min-w-0">
                      <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9 2a2 2 0 00-2 2v8a2 2 0 002 2h6a2 2 0 002-2V6.414A2 2 0 0016.414 5L14 2.586A2 2 0 0012.586 2H9z" />
                        <path d="M3 8a2 2 0 012-2v10h8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                      </svg>
                      <span className="text-sm text-gray-700 truncate">{files.name}</span>
                      {getFileTypeBadge(files.name)}
                      <span className="text-xs text-gray-500">({(files.size / 1024).toFixed(1)} KB)</span>
                    </div>
                    <button type="button" onClick={() => removeFile(0, type)} className="ml-2 text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"></path>
                      </svg>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="mb-3">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Formulario de Importación</h2>
        <p className="text-sm text-gray-600">Complete los datos necesarios para procesar sus archivos contables</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Proyecto + Fechas */}
        <div className="grid grid-cols-1 lg:grid-cols-8 gap-4">
          <div className="lg:col-span-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Proyecto <span className="text-red-500">*</span></label>
            <select
              value={formData.projectId}
              onChange={(e) => handleInputChange('projectId', e.target.value)}
              className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 ${errors.projectId ? 'border-red-300' : 'border-gray-300'}`}
            >
              <option value="">Seleccionar proyecto...</option>
              {projects?.map((project) => (
                <option key={project.id} value={project.id}>{project.name}</option>
              ))}
            </select>
            {errors.projectId && <p className="text-xs text-red-600 mt-1">{errors.projectId}</p>}
          </div>

          <div className="lg:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Fecha Inicio <span className="text-red-500">*</span></label>
            <input
              type="date"
              value={formData.fechaInicio || ''}
              onChange={(e) => handleDateChange('fechaInicio', e.target.value)}
              onBlur={(e) => handleDateChange('fechaInicio', e.target.value)}
              min="1900-01-01"
              max="9999-12-31"
              className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 ${errors.fechaInicio ? 'border-red-300' : 'border-gray-300'}`}
              placeholder="dd/mm/aaaa"
            />
            {errors.fechaInicio && <p className="text-xs text-red-600 mt-1">{errors.fechaInicio}</p>}
          </div>

          <div className="lg:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Fecha Fin <span className="text-red-500">*</span></label>
            <input
              type="date"
              value={formData.fechaFin || ''}
              onChange={(e) => handleDateChange('fechaFin', e.target.value)}
              onBlur={(e) => handleDateChange('fechaFin', e.target.value)}
              min="1900-01-01"
              max="9999-12-31"
              className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 ${errors.fechaFin ? 'border-red-300' : 'border-gray-300'}`}
              placeholder="dd/mm/aaaa"
            />
            {errors.fechaFin && <p className="text-xs text-red-600 mt-1">{errors.fechaFin}</p>}
          </div>
        </div>

        {/* Dropzones */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <FileDropZone
            type="libroDiario"
            label="Archivos Libro Diario"
            files={formData.libroDiarioFiles}
            isMultiple={true}
            error={errors.libroDiario}
            required={true}
          />
          <FileDropZone
            type="sumasSaldos"
            label="Archivo Sumas y Saldos (opcional)"
            files={formData.sumasSaldosFile}
            isMultiple={false}
            error={errors.sumasSaldos}
            required={false}
          />
        </div>

        {/* Acción */}
        <div className="flex justify-end pt-3 border-t border-gray-200">
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Procesando...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <span>Importar Archivos</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ImportForm;
