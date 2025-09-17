// frontend/src/services/applicationService.js
import api from './api';

class ApplicationService {
  async getAllApplications() {
    try {
      const response = await api.get('/api/applications/');
      return response.data;
    } catch (error) {
      console.error('Error fetching applications:', error);
      throw error;
    }
  }

  async getApplicationById(applicationId) {
    try {
      const response = await api.get(`/api/applications/${applicationId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching application by ID:', error);
      throw error;
    }
  }
}

export default new ApplicationService();