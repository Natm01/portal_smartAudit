```
import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import HomePage from './pages/HomePage/HomePage';
import ImportPage from './pages/ImportPage/ImportPage';
import ValidationPage from './pages/ValidationPage/ValidationPage';
import ResultsPage from './pages/ResultsPage/ResultsPage';
import ThoughtSpotPage from './pages/ThoughtSpotPage/ThoughtSpotPage';

function App() {
  // Estado para almacenar el mensaje de la API
  const [apiMessage, setApiMessage] = useState('');

  // Fetch de la API en el useEffect
  useEffect(() => {
    // Realizar una solicitud a la API FastAPI
    fetch('http://127.0.0.1:8000/api/hello')
      .then((response) => response.json())
      .then((data) => setApiMessage(data.message))  // Guardamos el mensaje en el estado
      .catch((error) => console.error('Error al obtener la API:', error));
  }, []); // El array vacío asegura que se ejecute solo una vez al cargar el componente

  return (
    <Router>
      <div className="App">
        <h1>API Response: {apiMessage ? apiMessage : 'Cargando...'}</h1> {/* Mostrar el mensaje de la API */}

        <Routes>
          {/* Página principal */}
          <Route path="/" element={<HomePage />} />
          
          {/* Rutas del módulo de Importación de Libro Diario */}
          <Route path="/libro-diario" element={<ImportPage />} />
          <Route path="/libro-diario/validation/:executionId" element={<ValidationPage />} />
          <Route path="/libro-diario/results/:executionId" element={<ResultsPage />} />

          {/* Ruta para ThoughtSpot */}
          <Route path="/thoughtspot" element={<ThoughtSpotPage />} />
          
          {/* Redirección para rutas no encontradas */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
```