// frontend/src/services/projectService.js
import api from './api';

class ProjectService {
  async getAllProjects() {
    try {
      const response = await api.get('/api/projects/');
      return response.data;
    } catch (error) {
      console.error('Error fetching projects:', error);
      throw error;
    }
  }

  async getProjectById(projectId) {
    try {
      const response = await api.get(`/api/projects/${projectId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching project by ID:', error);
      throw error;
    }
  }
}

export default new ProjectService();