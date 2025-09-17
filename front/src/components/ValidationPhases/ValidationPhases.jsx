// frontend/src/components/ValidationPhases/ValidationPhases.jsx - Versión con estilos más compactos
import React, { useState, useEffect } from 'react';

const ValidationPhases = ({ fileType, onComplete }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [currentPhase, setCurrentPhase] = useState(0);
  const [completedPhases, setCompletedPhases] = useState([]);
  const [isValidating, setIsValidating] = useState(false);
  const [allCompleted, setAllCompleted] = useState(false);

  const phases = {
    libro_diario: [
      {
        id: 1,
        name: "Validaciones de Formato",
        validations: [
          "Fechas con formato correcto",
          "Horas con formato correcto",
          "Importes con formato correcto"
        ]
      },
      {
        id: 2,
        name: "Validaciones de Identificadores",
        validations: [
          "Identificadores de asientos únicos",
          "Identificadores de apuntes secuenciales"
        ]
      },
      {
        id: 3,
        name: "Validaciones Temporales",
        validations: [
          "Fecha contable en el período",
          "Fecha registro excede el período contable"
        ]
      },
      {
        id: 4,
        name: "Validaciones de Integridad Contable",
        validations: [
          "Asientos balanceados"
        ]
      }
    ],
    sumas_saldos: [
      {
        id: 1,
        name: "Validaciones de Formato",
        validations: [
          "Fechas con formato correcto",
          "Horas con formato correcto",
          "Importes con formato correcto"
        ]
      }, 
      {
        id: 2,
        name: "Validaciones de Integridad Contable",
        validations: [
          "Saldos balanceados"
        ]
      }
    ]
  };

  const currentPhases = phases[fileType] || [];

  const startValidation = async () => {
    setIsValidating(true);
    setIsExpanded(true);
    
    for (let i = 0; i < currentPhases.length; i++) {
      setCurrentPhase(i);
      
      // Simular tiempo de validación
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      setCompletedPhases(prev => [...prev, i]);
    }
    
    setAllCompleted(true);
    setIsValidating(false);
    
    // Notificar completion
    if (onComplete) {
      onComplete();
    }
  };

  const getPhaseStatus = (phaseIndex) => {
    if (completedPhases.includes(phaseIndex)) {
      return 'completed';
    } else if (currentPhase === phaseIndex && isValidating) {
      return 'validating';
    } else {
      return 'pending';
    }
  };

  const getFileTypeTitle = () => {
    return fileType === 'libro_diario' ? 'Validaciones de Libro Diario' : 'Validaciones de Sumas y Saldos';
  };

  const getProgressPercentage = () => {
    return currentPhases.length > 0 ? (completedPhases.length / currentPhases.length) * 100 : 0;
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div 
        className="px-4 py-3 border-b border-gray-200 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3">
              <h3 className="text-base font-semibold text-gray-900">
                {getFileTypeTitle()}
              </h3>
              
              {/* Estado */}
              <div>
                {allCompleted ? (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Completado
                  </span>
                ) : isValidating ? (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    <svg className="animate-spin w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Validando...
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    Pendiente
                  </span>
                )}
              </div>
            </div>
            
            {/* Barra de progreso */}
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                <span>Progreso General</span>
                <span>{completedPhases.length} de {currentPhases.length} fases completadas</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div 
                  className={`h-1.5 rounded-full transition-all duration-500 ${
                    allCompleted ? 'bg-green-500' : 'bg-purple-600'
                  }`}
                  style={{ width: `${getProgressPercentage()}%` }}
                ></div>
              </div>
            </div>
          </div>

          {/* Botón para iniciar validación - más a la derecha y más pequeño */}
          <div className="flex items-center ml-4">
            {!isValidating && !allCompleted && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  startValidation();
                }}
                className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-colors"
              >
                <svg className="w-3 h-3 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h8m2-10v16a2 2 0 01-2 2H6a2 2 0 01-2-2V4a2 2 0 012-2h8l4 4z" />
                </svg>
                Iniciar Validación
              </button>
            )}
            
            {/* Icono de expand/collapse */}
            <svg 
              className={`w-4 h-4 text-gray-400 transition-transform duration-200 ml-3 ${
                isExpanded ? 'rotate-180' : ''
              }`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>

      {/* Contenido desplegable */}
      {isExpanded && (
        <div className="px-4 py-3 space-y-3">
          {currentPhases.map((phase, phaseIndex) => {
            const status = getPhaseStatus(phaseIndex);
            
            return (
              <div
                key={phase.id}
                className={`p-3 rounded-lg border transition-all duration-300 ${
                  status === 'completed'
                    ? 'border-green-300 bg-green-50'
                    : status === 'validating'
                    ? 'border-blue-300 bg-blue-50'
                    : 'border-gray-300 bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                      status === 'completed'
                        ? 'bg-green-100 text-green-600'
                        : status === 'validating'
                        ? 'bg-blue-100 text-blue-600'
                        : 'bg-gray-100 text-gray-400'
                    }`}>
                      {status === 'completed' ? (
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : status === 'validating' ? (
                        <svg className="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      ) : (
                        phase.id
                      )}
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-gray-900">
                        Fase {phase.id}: {phase.name}
                      </h4>
                      <p className="text-xs text-gray-600">
                        {status === 'completed' && '✓ Completada'}
                        {status === 'validating' && '⏳ Validando...'}
                        {status === 'pending' && 'Pendiente'}
                      </p>
                    </div>
                  </div>
                  
                  {status === 'completed' && (
                    <span className="text-xs font-medium text-green-600">
                      ✓ Completada
                    </span>
                  )}
                </div>

                {/* Lista de validaciones */}
                <div className="ml-8 space-y-1">
                  {phase.validations.map((validation, validationIndex) => (
                    <div key={validationIndex} className="flex items-center space-x-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${
                        status === 'completed'
                          ? 'bg-green-500'
                          : status === 'validating'
                          ? 'bg-blue-500'
                          : 'bg-gray-300'
                      }`}></div>
                      <span className="text-xs text-gray-700">{validation}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}

          {/* Mensaje final */}
          {allCompleted && (
            <div className="flex items-center p-3 bg-green-50 border border-green-200 rounded-lg">
              <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"></path>
              </svg>
              <div className="ml-2">
                <p className="text-xs font-medium text-green-800">
                  Todas las validaciones completadas exitosamente
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ValidationPhases;