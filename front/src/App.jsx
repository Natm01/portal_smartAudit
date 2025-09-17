// frontend/src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import HomePage from './pages/HomePage/HomePage';
import ImportPage from './pages/ImportPage/ImportPage';
import ValidationPage from './pages/ValidationPage/ValidationPage';
import ResultsPage from './pages/ResultsPage/ResultsPage';
import ThoughtSpotPage from './pages/ThoughtSpotPage/ThoughtSpotPage';

function App() {
  return (
    <Router>
      <div className="App">
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