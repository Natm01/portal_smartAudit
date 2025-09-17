// frontend/src/components/FieldMapper/FieldMapper.jsx
import React, { useEffect, useMemo, useState } from 'react';
import importService from '../../services/importService';

const REQUIRED_FIELDS = new Set([
  'journal_entry_id',
  'line_number',
  'description',
  'line_description',
  'posting_date',
  'fiscal_year',
  'amount',
]);

/**
 * FieldMapper integrado a backend:
 * - Lee /api/import/mapeo/{execution_id}/fields-mapping
 * - Permite aplicar mapeo manual: /apply-manual-mapping
 */
const FieldMapper = ({
  executionId,
  originalFields = [],
  fileType = 'libro_diario',
  mappingSummary = null,
  mapeoReady = false,
}) => {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const [serverMap, setServerMap] = useState({});      // mapped_fields del backend
  const [missing, setMissing] = useState([]);          // missing_fields del backend
  const [summary, setSummary] = useState(mappingSummary || null);

  const [manual, setManual] = useState({});            // cambios locales pendientes {dest: source}
  const [applying, setApplying] = useState(false);
  const [appliedOk, setAppliedOk] = useState(false);

  const options = useMemo(() => originalFields, [originalFields]);

  useEffect(() => {
    if (!executionId) return;
    if (!mapeoReady) return; // esperamos a que el padre arranque el mapeo
    let mounted = true;
    const load = async () => {
      try {
        setLoading(true);
        setErr(null);
        const data = await importService.getFieldsMapping(executionId);
        if (!mounted) return;

        setServerMap(data.mapped_fields || {});
        setMissing(data.missing_fields || []);
        setSummary(data.mapping_summary || null);
      } catch (e) {
        if (!mounted) return;
        setErr(e?.message || 'Error al cargar mapeo');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, [executionId, mapeoReady]);

  const mappedCount = useMemo(() => Object.keys(serverMap).length, [serverMap]);
  const totalFields = useMemo(() => (summary?.total_standard_fields || 0), [summary]);
  const requiredMapped = useMemo(
    () => Object.keys(serverMap).filter(f => REQUIRED_FIELDS.has(f)).length,
    [serverMap]
  );

  const handleSelect = (destField, sourceValue) => {
    setManual(prev => {
      const next = { ...prev };
      next[destField] = sourceValue || '';
      return next;
    });
  };

  const applyManual = async () => {
    try {
      setApplying(true);
      setErr(null);
      const clean = Object.fromEntries(
        Object.entries(manual).filter(([, v]) => v && typeof v === 'string')
      );
      if (Object.keys(clean).length === 0) {
        setAppliedOk(true);
        setTimeout(() => setAppliedOk(false), 1800);
        return;
      }

      const res = await importService.applyManualMapping(executionId, clean);
      if (!res.success) throw new Error(res.error || 'No se pudo aplicar el mapeo');

      // Releer desde el backend para reflejar cambios
      const data = await importService.getFieldsMapping(executionId);
      setServerMap(data.mapped_fields || {});
      setMissing(data.missing_fields || []);
      setSummary(data.mapping_summary || null);
      setManual({});

      setAppliedOk(true);
      setTimeout(() => setAppliedOk(false), 1800);
    } catch (e) {
      setErr(e?.message || 'Error al aplicar mapeo manual');
    } finally {
      setApplying(false);
    }
  };

  const allDestFields = useMemo(() => {
    // Componemos lista final con:
    // - keys devueltas por el backend (mapped_fields + missing_fields),
    // - y aseguramos que los "required" existan
    const s = new Set([
      ...Object.keys(serverMap || {}),
      ...(missing || []),
      ...Array.from(REQUIRED_FIELDS),
    ]);
    return Array.from(s).sort();
  }, [serverMap, missing]);

  return (
    <div className="bg-white border border-gray-200 rounded-xl">
      {/* Encabezado resumen */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <div className="text-sm text-gray-700">
          {summary ? (
            <>
              <span className="font-medium">{mappedCount}</span>/{summary.total_standard_fields} mapeados
              <span className="mx-2 text-gray-300">•</span>
              <span className="font-medium">{requiredMapped}</span>/
              {Array.from(REQUIRED_FIELDS).length} obligatorios
              {typeof summary.completeness_percentage === 'number' && (
                <>
                  <span className="mx-2 text-gray-300">•</span>
                  {summary.completeness_percentage.toFixed(1)}% completo
                </>
              )}
            </>
          ) : (
            'Mapeo automático'
          )}
        </div>

        <div className="flex items-center space-x-2">
          {appliedOk && (
            <span className="text-xs px-2 py-1 rounded bg-green-100 text-green-800 border border-green-200">
              Cambios aplicados
            </span>
          )}
          <button
            onClick={applyManual}
            disabled={applying}
            className={`px-3 py-1.5 rounded-lg text-sm ${applying ? 'bg-gray-200 text-gray-500' : 'bg-purple-600 text-white hover:bg-purple-700'}`}
          >
            {applying ? 'Aplicando...' : 'Aplicar mapeo manual'}
          </button>
        </div>
      </div>

      {/* Estados */}
      {loading && (
        <div className="p-4 text-sm text-gray-600">Cargando mapeo...</div>
      )}
      {err && (
        <div className="p-4 text-sm text-red-600">{err}</div>
      )}

      {/* Tabla de mapeo */}
      {!loading && !err && (
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Campo BD (Destino)</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Campo Archivo (Origen)</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Conf.</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Oblig.</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {allDestFields.map((dest) => {
                const server = serverMap?.[dest] || null;
                const current = (manual?.[dest] ?? server?.mapped_column ?? '');
                const conf = server?.confidence ?? null;
                const required = REQUIRED_FIELDS.has(dest);
                const missingMark = (missing || []).includes(dest);

                return (
                  <tr key={dest} className={missingMark ? 'bg-red-50' : ''}>
                    <td className="px-3 py-2 text-sm text-gray-800 whitespace-nowrap">{dest}</td>
                    <td className="px-3 py-2">
                      <select
                        value={current}
                        onChange={(e) => handleSelect(dest, e.target.value)}
                        className="border-gray-300 rounded-md text-sm"
                      >
                        <option value="">-- Sin mapear --</option>
                        {options.map((opt) => (
                          <option key={`${dest}-${opt}`} value={opt}>{opt}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2 text-sm text-gray-700">
                      {conf != null ? `${Math.round(conf * 100)}%` : '—'}
                    </td>
                    <td className="px-3 py-2">
                      {required ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          Sí
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                          No
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* Nota de críticos */}
          {Array.isArray(missing) && missing.length > 0 && (
            <div className="px-4 py-3 text-sm text-red-700 bg-red-50 border-t border-red-100">
              Faltan campos: {missing.join(', ')}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FieldMapper;
