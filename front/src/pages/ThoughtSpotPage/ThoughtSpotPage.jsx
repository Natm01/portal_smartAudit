// frontend/src/pages/ThoughtSpotPage/ThoughtSpotPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LiveboardEmbed } from '@thoughtspot/visual-embed-sdk/react';
import { init, prefetch } from '@thoughtspot/visual-embed-sdk';
import Header from '../../components/Header/Header';
import userService from '../../services/userService';

const ThoughtSpotPage = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      
      // Cargar usuario actual
      const userResponse = await userService.getCurrentUser();
      if (userResponse.success && userResponse.user) {
        setUser(userResponse.user);
      }
      
    } catch (err) {
      console.error('Error loading initial data:', err);
      setError('Error al cargar la información inicial');
    } finally {
      setLoading(false);
    }
  };

  const handleUserChange = (newUser) => {
    setUser(newUser);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header user={user} onUserChange={handleUserChange} />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-gray-200 border-t-purple-600 mb-4"></div>
            <p className="text-gray-600">Cargando dashboard...</p>
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header user={user} onUserChange={handleUserChange} />
        <main className="flex-1 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white rounded-xl shadow-sm p-8 text-center border border-red-100">
            <div className="text-6xl mb-4">⚠️</div>
            <h2 className="text-xl font-semibold text-red-600 mb-2">Error de acceso</h2>
            <p className="text-gray-600 mb-6">{error}</p>
            <div className="space-y-2">
              <button 
                onClick={() => window.location.reload()} 
                className="w-full bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
              >
                Reintentar
              </button>
              <button 
                onClick={() => navigate('/')} 
                className="w-full bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200"
              >
                Volver al inicio
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header user={user} onUserChange={handleUserChange} />
      
      <main className="flex-1 flex flex-col">
        {/* Breadcrumb */}
        <div className="w-full px-4 sm:px-6 lg:px-8 py-4">
          <nav className="flex" aria-label="Breadcrumb">
            <ol className="inline-flex items-center space-x-1 md:space-x-3">
              <li className="inline-flex items-center">
                <button
                  onClick={() => navigate('/')}
                  className="inline-flex items-center text-sm font-medium text-gray-700 hover:text-purple-600 transition-colors"
                >
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"></path>
                  </svg>
                  Inicio
                </button>
              </li>
              <li>
                <div className="flex items-center">
                  <svg className="w-6 h-6 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd"></path>
                  </svg>
                  <span className="ml-1 text-sm font-medium text-gray-500 md:ml-2">ThoughtSpot</span>
                </div>
              </li>
            </ol>
          </nav>
        </div>

        {/* Información del proyecto */}
        <div className="w-full px-4 sm:px-6 lg:px-8 mb-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-4m-5 0H3m0 0h2M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 8h1m-1-4h1m4 4h1m-1-4h1" />
                </svg>
              </div>
              <div>
                <h2 className="text-sm font-semibold text-gray-900">
                  Proyecto: OPERADOR INTEGRAL DE VEHICULOS, S.L.U
                </h2>
                <p className="text-xs text-gray-600">
                  Dashboard de análisis y visualización de datos 
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Dashboard Container */}
        <div className="flex-1 px-4 sm:px-6 lg:px-8 pb-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden h-full">
            <div className="h-full">
              <LiveboardEmbed
                liveboardId="f1f1312f-af0d-40d2-b94f-85f75f154bb4"
                frameParams={{
                  height: '100vh',
                  width: '100%', 
                }}
                hideLiveboardHeader={true}      
                hiddenActions={[
                    'explore',
                    'exploreChart',
                    'drill',
                    'drillDown',
                    'drillUp',
                    'contextMenu'
                ]}
              />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ThoughtSpotPage;