// frontend/src/pages/HomePage/HomePage.jsx - Sin lógica de permisos
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/Header/Header';
import ApplicationCard from '../../components/ApplicationCard/ApplicationCard';
import userService from '../../services/userService';
import applicationService from '../../services/applicationService';

const HomePage = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      
      // Cargar información del usuario actual
      const userResponse = await userService.getCurrentUser();
      if (userResponse.success && userResponse.user) {
        setUser(userResponse.user);
      }
      
      // Cargar todas las aplicaciones activas
      const appsResponse = await applicationService.getAllApplications();
      if (appsResponse.success && appsResponse.applications) {
        setApplications(appsResponse.applications);
      }
      
    } catch (err) {
      console.error('Error loading initial data:', err);
      setError('Error al cargar la información inicial');
    } finally {
      setLoading(false);
    }
  };

  const handleUserChange = async (newUser) => {
    try {
      setUser(newUser);
      
      // Mostrar notificación del cambio
      showUserChangeNotification(newUser.name);
      
    } catch (err) {
      console.error('Error changing user:', err);
      setError('Error al cambiar de usuario');
    }
  };

  const showUserChangeNotification = (userName) => {
    // Crear notificación temporal
    const notification = document.createElement('div');
    notification.className = 'fixed top-4 right-4 bg-purple-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 transform transition-all duration-300';
    notification.innerHTML = `
      <div class="flex items-center space-x-2">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
        </svg>
        <span>Cambiado a ${userName}</span>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    // Remover después de 3 segundos
    setTimeout(() => {
      notification.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (document.body.contains(notification)) {
          document.body.removeChild(notification);
        }
      }, 300);
    }, 3000);
  };

  const handleApplicationClick = (application) => {
    console.log('Clicked application:', application);
    
    // Manejar navegación según la aplicación
    switch (application.id) {
      case 'importacion-libro-diario':
        navigate('/libro-diario');
        break;
      case 'analisis-jet':
        alert(`Navegando a: ${application.name} (Próximamente)`);
        break;
      case 'analisis-riesgos':
        alert(`Navegando a: ${application.name} (Próximamente)`);
        break;
      case 'analisis-obsolescencia':
        alert(`Navegando a: ${application.name} (Próximamente)`);
        break;
      case 'thoughtspot':
        navigate('/thoughtspot');
        break;
      default:
        alert(`Navegando a: ${application.name}`);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header user={user} onUserChange={handleUserChange} />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-gray-200 border-t-purple-600 mb-4"></div>
            <p className="text-gray-600">Cargando aplicaciones...</p>
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
            <h2 className="text-xl font-semibold text-red-600 mb-2">Error al cargar las aplicaciones</h2>
            <p className="text-gray-600 mb-6">{error}</p>
            <button 
              onClick={() => window.location.reload()} 
              className="btn-primary"
            >
              Reintentar
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header 
        user={user} 
        onUserChange={handleUserChange}
      />
      
      <main className="flex-1">
        <div className="max-w-8xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Welcome section */}
          {user && (
            <div className="text-center mb-8 animate-fade-in">
              <h2 className="text-lg sm:text-xl font-semibold text-gray-900 mb-1">
                Bienvenido, {user.name}
              </h2>
              <p className="text-sm text-gray-500">
                {user.department} • {user.roleName}
              </p>
            </div>
          )}
          
          {/* Applications section */}
          <section className="animate-fade-in">
            <div className="text-center mb-6">
              <h2 className="text-base font-semibold text-gray-900 mb-1">Aplicaciones</h2>
            </div>
            
            {applications.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {applications.map((application, index) => (
                  <div 
                    key={application.id}
                    className="animate-fade-in"
                    style={{ animationDelay: `${index * 100}ms` }}
                  >
                    <ApplicationCard
                      application={application}
                      onClick={handleApplicationClick}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-16">
                <div className="bg-white rounded-xl shadow-sm p-12 max-w-md mx-auto border border-gray-100">
                  <div className="text-6xl mb-6 opacity-50">📱</div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-3">
                    No hay aplicaciones disponibles
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    No se pudieron cargar las aplicaciones en este momento.
                  </p>
                </div>
              </div>
            )}
          </section>
        </div>
      </main>
      
      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            &copy; 2025 Grant Thornton • Todos los derechos reservados
          </p>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;