import React, { useState, useEffect, useCallback, useRef } from 'react';
import FieldMapper from '../FieldMapper/FieldMapper';
import api from '../../services/api';

const PREVIEW_PATH_BASE = '/api/import/preview';

const FilePreview = ({ file, fileType, executionId, maxRows = 25 }) => {
  const [previewData, setPreviewData] = useState(null); // { headers, table, metadata }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [fieldMappings, setFieldMappings] = useState({});
  const [showMappedNames, setShowMappedNames] = useState(false);
  const [isMapperOpen, setIsMapperOpen] = useState(false);
  const [showAppliedNotification, setShowAppliedNotification] = useState(false);

  // para cancelar si el componente se desmonta en medio de los reintentos
  const abortRef = useRef(false);
  useEffect(() => { abortRef.current = false; return () => { abortRef.current = true; }; }, []);

  const sanitizeCell = (v) => {
    if (v === null || v === undefined) return '';
    if (typeof v === 'object') return JSON.stringify(v);
    return String(v);
  };

  // Prioriza lo convertido si existe; si no, table; si no, data
  const pickRows = (payload) => {
    const rows =
      payload?.converted?.rows ||
      payload?.converted?.data ||
      payload?.converted ||
      payload?.table?.rows ||
      payload?.table ||
      payload?.data ||
      [];
    return Array.isArray(rows) ? rows : [];
  };

  const buildTable = (rowsObjArray) => {
    const headers = Array.from(
      rowsObjArray.reduce((acc, row) => {
        Object.keys(row || {}).forEach((k) => acc.add(k));
        return acc;
      }, new Set())
    );
    const table = rowsObjArray.map((r) => headers.map((h) => sanitizeCell(r?.[h])));
    return { headers, table };
  };

  const isTransientTokenizeError = (err) => {
    const msg = (err?.response?.data?.detail || err?.message || '').toLowerCase();
    return msg.includes('tokenizing') || msg.includes('expected') || (err?.response?.status >= 500);
  };

  const fetchPreviewOnce = async () => {
    // cache-buster para que no te devuelva un 500 cacheado por un proxy
    const url = `${PREVIEW_PATH_BASE}/${encodeURIComponent(executionId)}?_=${Date.now()}`;

    // Forzamos parseo a JSON aunque el servidor responda text/plain
    const resp = await api.get(url, {
      headers: { Accept: 'application/json, text/plain, */*' },
      transformResponse: [(data, _headers) => {
        try { return typeof data === 'string' ? JSON.parse(data) : data; }
        catch { return data; } // si ya viene como objeto, lo dejamos
      }],
      // IMPORTANTÍSIMO: sin params (nada de rows/type) para no activar ramas de tokenización
      params: undefined
    });

    return resp.data;
  };

  const loadPreviewData = useCallback(async () => {
    if (!executionId) return;
    setLoading(true);
    setError(null);

    let lastErr = null;

    for (let attempt = 1; attempt <= 3; attempt++) {
      if (abortRef.current) return;

      try {
        const payload = await fetchPreviewOnce();
        const rows = pickRows(payload);

        if (!Array.isArray(rows)) throw new Error('Respuesta inválida de preview');

        const { headers, table } = rows.length > 0 ? buildTable(rows) : { headers: [], table: [] };
        setPreviewData({ headers, table, metadata: payload?.metadata || {} });
        setLoading(false);
        return; // listo
      } catch (err) {
        lastErr = err;
        // si no es error transitorio, corta ya
        if (!isTransientTokenizeError(err) || attempt === 3) {
          break;
        }
        // backoff progresivo 250ms, 500ms
        const delay = 250 * attempt;
        await new Promise((r) => setTimeout(r, delay));
      }
    }

    if (!abortRef.current) {
      console.error('Preview error (tras reintentos):', lastErr);
      setError(
        lastErr?.response?.data?.detail ||
        lastErr?.message ||
        'Error al cargar la vista previa'
      );
      setLoading(false);
    }
  }, [executionId]);

  useEffect(() => { loadPreviewData(); }, [loadPreviewData]);

  const handleMappingChange = (mappings) => {
    setFieldMappings(mappings);
    if (Object.values(mappings).some(Boolean)) {
      setShowMappedNames(true);
      setShowAppliedNotification(true);
      setTimeout(() => setShowAppliedNotification(false), 2500);
    }
  };

  const databaseFields = {}; // (opcional) deja el mapper como antes si lo usas

  const getDisplayHeaders = () => {
    if (!previewData?.headers) return [];
    if (!showMappedNames) return previewData.headers;

    const mappedFirst = [];
    const unmapped = [];
    previewData.headers.forEach((original) => {
      const mapped = fieldMappings?.[original];
      if (mapped) mappedFirst.push(mapped);
      else unmapped.push(original);
    });
    return [...mappedFirst, ...unmapped];
  };

  const getDisplayData = () => {
    if (!previewData?.table) return [];
    if (!showMappedNames) return previewData.table;

    const originalHeaders = previewData.headers;
    const mappedHeaders = getDisplayHeaders();
    const pos = {};
    originalHeaders.forEach((h, i) => (pos[h] = i));

    return previewData.table.map((row) =>
      mappedHeaders.map((h) => {
        const originalFromMapping = Object.entries(fieldMappings).find(
          ([orig, target]) => (databaseFields[target] || target) === h
        )?.[0];
        const originalName = originalFromMapping || h;
        const idx = pos[originalName];
        return idx !== undefined ? row[idx] : '';
      })
    );
  };

  const title = fileType === 'sumas_saldos' ? 'Preview: Sumas y Saldos' : 'Preview: Libro Diario';
  const shownRows =
    previewData?.metadata?.total_rows_previewed ??
    (previewData?.table?.length || maxRows);
  const statusText = previewData?.metadata?.execution_step || '—';

  return (
    <div className="mt-6 w-full">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden w-full">
        {/* Header */}
        <div className="px-6 pt-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
              <p className="text-sm text-gray-600 mt-1">Mostrando {shownRows} primeras filas</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 text-xs rounded-full bg-gray-100 text-gray-700">
                {fileType === 'sumas_saldos' ? 'SUMAS/SALDOS' : 'TXT/SAP'}
              </span>
              <label className="inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="form-checkbox h-4 w-4 text-purple-600"
                  checked={showMappedNames}
                  onChange={(e) => setShowMappedNames(e.target.checked)}
                />
                <span className="ml-2 text-sm text-gray-700">
                  {showMappedNames ? 'Nombres mapeados' : 'Nombres originales'}
                </span>
              </label>
            </div>
          </div>

          {/* Info band */}
          <div className="mt-4 mb-3">
            <div className="bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 grid grid-cols-3 gap-4">
              <div className="text-sm">
                <div className="text-gray-500">Tipo:</div>
                <div className="text-gray-900">{fileType === 'sumas_saldos' ? 'Sumas y Saldos' : 'Libro Diario'}</div>
              </div>
              <div className="text-sm">
                <div className="text-gray-500">Mapeados:</div>
                <div className="text-gray-900">
                  {`${Object.values(fieldMappings || {}).filter(Boolean).length}/${previewData?.headers?.length || 0}`}
                </div>
              </div>
              <div className="text-sm">
                <div className="text-gray-500">Estado:</div>
                <div className="font-medium text-gray-800">{statusText}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Errores */}
        {error && (
          <div className="px-6 pb-6 text-sm text-red-600">
            Error: {error}
          </div>
        )}

        {/* Skeleton */}
        {loading && !error && (
          <div className="px-6 pb-6">
            <div className="animate-pulse">
              <div className="h-8 bg-gray-100 rounded mb-3" />
              {[...Array(8)].map((_, i) => (
                <div key={i} className="h-6 bg-gray-100 rounded mb-2" />
              ))}
            </div>
          </div>
        )}

        {/* Tabla */}
        {!loading && !error && previewData && previewData.headers?.length > 0 && (
          <div className="px-6 pb-6">
            <div className="rounded-[7px] border border-gray-200 overflow-auto max-h-96">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0 z-10">
                  <tr>
                    <th
                      className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-0 bg-gray-50 z-10 rounded-tl-[7px] border-r border-gray-200"
                      title="#"
                    >
                      #
                    </th>
                    {getDisplayHeaders().map((header, idx, arr) => (
                      <th
                        key={idx}
                        className={
                          'px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap min-w-20 ' +
                          (idx === arr.length - 1 ? 'rounded-tr-[7px]' : '')
                        }
                        title={header}
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {getDisplayData().map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-2 py-1 text-xs text-gray-500 sticky left-0 bg-white border-r border-gray-200">
                        {i + 1}
                      </td>
                      {row.map((cell, j) => (
                        <td key={j} className="px-2 py-1 text-xs text-gray-800 whitespace-nowrap">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {previewData?.metadata && (
              <div className="mt-3 text-xs text-gray-500">
                {previewData.metadata.storage_type ? `Origen: ${previewData.metadata.storage_type} • ` : ''}
                {previewData.metadata.file_extension ? `Extensión: ${previewData.metadata.file_extension} • ` : ''}
                {typeof previewData.metadata.total_rows_previewed === 'number'
                  ? `Filas mostradas: ${previewData.metadata.total_rows_previewed}`
                  : ''}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default FilePreview;
