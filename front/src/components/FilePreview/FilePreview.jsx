// src/components/FilePreview/FilePreview.jsx
import React, { useEffect, useRef, useState } from 'react';
import FieldMapper from '../FieldMapper/FieldMapper';
import api from '../../services/api';

const PREVIEW_PATH_BASE = '/api/import/preview';

const FilePreview = ({ file, fileType, executionId, maxRows = 25 }) => {
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [fieldMappings, setFieldMappings] = useState({});
  const [showMappedNames, setShowMappedNames] = useState(false);
  const [isMapperOpen, setIsMapperOpen] = useState(true);
  const [showAppliedNotification, setShowAppliedNotification] = useState(false);

  const abortRef = useRef(false);
  useEffect(() => { abortRef.current = false; return () => { abortRef.current = true; }; }, []);

  const sanitizeCell = (v) => (v === null || v === undefined ? '' : (typeof v === 'object' ? JSON.stringify(v) : String(v)));

  const pickRows = (payload) => {
    const rows = payload?.converted?.rows || payload?.converted?.data || payload?.converted ||
                 payload?.table?.rows || payload?.table || payload?.data || [];
    return Array.isArray(rows) ? rows : [];
  };

  const buildTable = (rowsObjArray) => {
    const headers = Array.from(rowsObjArray.reduce((acc, row) => {
      Object.keys(row || {}).forEach((k) => acc.add(k)); return acc;
    }, new Set()));
    const table = rowsObjArray.map((r) => headers.map((h) => sanitizeCell(r?.[h])));
    return { headers, table };
  };

  const fetchPreviewOnce = async () => {
    const url = `${PREVIEW_PATH_BASE}/${encodeURIComponent(executionId)}?_=${Date.now()}`;
    const resp = await api.get(url, {
      headers: { Accept: 'application/json, text/plain, */*' },
      transformResponse: [(data) => { try { return typeof data === 'string' ? JSON.parse(data) : data; } catch { return { data: [] }; } }],
    });
    const payload = resp?.data || {};
    const rows = pickRows(payload);
    return buildTable(rows);
  };

  const loadPreviewData = async () => {
    try {
      setLoading(true); setError(null);
      const t = await fetchPreviewOnce();
      if (abortRef.current) return;
      setPreviewData(t);
    } catch (e) {
      if (abortRef.current) return;
      setError(e?.response?.data?.detail || e?.message || 'Error al cargar el preview');
    } finally { if (!abortRef.current) setLoading(false); }
  };

  useEffect(() => { if (executionId) loadPreviewData(); }, [executionId, fileType]);

  const handleMappingChange = (newMap) => {
    setFieldMappings(newMap || {});
    setShowAppliedNotification(true);
    setTimeout(() => setShowAppliedNotification(false), 1800);
  };

  const getFileTypeLabel = () => (fileType === 'libro_diario' ? 'Libro Diario' : 'Sumas y Saldos (Excel)');
  const getMaxRowsLabel  = () => (fileType === 'libro_diario' ? '25 primeras filas' : '10 primeras filas');

  if (!executionId) return null;

  return (
    <div className="space-y-6">
      {showAppliedNotification && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50">
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="font-medium">Mapeo aplicado correctamente</span>
          </div>
          <p className="text-sm mt-1 opacity-90">Las columnas ya están mapeadas</p>
        </div>
      )}

      {previewData && (
        <FieldMapper
          originalFields={previewData.headers}
          executionId={executionId}
          fileType={fileType}
          isOpen={isMapperOpen}
          onToggle={() => setIsMapperOpen(!isMapperOpen)}
          onMappingChange={handleMappingChange}
        />
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Preview: {getFileTypeLabel()}</h3>
            <p className="text-sm text-gray-600 mt-1">Mostrando {getMaxRowsLabel()}</p>
          </div>
          <button
            onClick={() => setShowMappedNames(!showMappedNames)}
            className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
              showMappedNames ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
            }`}
          >
            {showMappedNames ? 'Ocultar nombres BD' : 'Ver nombres BD'}
          </button>
        </div>

        <div className="overflow-x-auto">
          {!previewData && loading && <div className="p-6 text-sm text-gray-500">Cargando preview…</div>}
          {error && <div className="p-6 text-sm text-red-600">{error}</div>}
          {previewData && (
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {previewData.headers.map((h) => {
                    const mapped = fieldMappings[h];
                    return (
                      <th key={h} className="px-4 py-2 text-left font-medium text-gray-700">
                        {showMappedNames && mapped ? `${mapped} (${h})` : h}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {previewData.table.slice(0, fileType === 'libro_diario' ? 25 : 10).map((row, idx) => (
                  <tr key={idx}>
                    {row.map((cell, cidx) => (
                      <td key={`${idx}-${cidx}`} className="px-4 py-2 whitespace-nowrap text-gray-800">{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

export default FilePreview;
