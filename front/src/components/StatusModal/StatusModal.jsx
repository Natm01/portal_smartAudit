// frontend/src/components/StatusModal/StatusModal.jsx
import React from 'react';

/**
 * Modal simple para mostrar estados (subida/validación)
 * Mantiene look & feel y proporciones del sitio (overlay fijo, card compacta).
 */
const StatusModal = ({ isOpen, title, subtitle, status = 'info', onClose, actions = null }) => {
  if (!isOpen) return null;

  const getIcon = () => {
    if (status === 'success') {
      return (
        <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
          <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      );
    }
    if (status === 'error') {
      return (
        <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
          <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      );
    }
    return (
      <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
        <svg className={"w-6 h-6 text-blue-600 " + (status === 'loading' ? 'animate-spin' : '')} fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-gray-200">
        <div className="p-5">
          <div className="flex items-start space-x-3">
            {getIcon()}
            <div className="flex-1">
              <h3 className="text-base font-semibold text-gray-900">{title}</h3>
              {subtitle && <p className="mt-1 text-xs text-gray-600">{subtitle}</p>}
            </div>
          </div>
        </div>
        <div className="px-5 pb-5 flex items-center justify-end space-x-2">
          {actions ? actions : (
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-purple-600 text-white hover:bg-purple-700"
            >
              Cerrar
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default StatusModal;
