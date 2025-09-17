// frontend/src/services/userService.js
class UserService {
  constructor() {
    // Estado del usuario actual en memoria
    this.currentUserState = null;
    this.isUserOverridden = false;
    
    // Usuarios simulados - sin endpoints del backend
    this.mockUsers = [
      {
        id: 'carlos.rodriguez',
        name: 'Carlos Rodríguez',
        roleName: 'Senior Auditor',
        department: 'Auditoría Externa'
      },
      {
        id: 'maria.garcia',
        name: 'María García',
        roleName: 'Auditor Manager',
        department: 'Auditoría Externa'
      },
      {
        id: 'juan.lopez',
        name: 'Juan López',
        roleName: 'Junior Auditor',
        department: 'Auditoría Externa'
      },
      {
        id: 'ana.martinez',
        name: 'Ana Martínez',
        roleName: 'Partner',
        department: 'Auditoría Externa'
      }
    ];
    
    // Usuario por defecto
    this.defaultUser = this.mockUsers[1]; // María García
  }

  async getCurrentUser() {
    try {
      // Si hay un usuario seleccionado manualmente, devolverlo
      if (this.isUserOverridden && this.currentUserState) {
        return {
          success: true,
          user: this.currentUserState
        };
      }

      // Devolver usuario por defecto
      this.currentUserState = this.defaultUser;
      
      return {
        success: true,
        user: this.currentUserState
      };
    } catch (error) {
      console.error('Error getting current user:', error);
      throw error;
    }
  }

  // Establecer el usuario actual (cuando se cambia desde el Header)
  setCurrentUser(user) {
    this.currentUserState = user;
    this.isUserOverridden = true;
    console.log('User state updated in service:', user);
  }

  // Resetear al usuario por defecto
  resetToOriginalUser() {
    this.isUserOverridden = false;
    this.currentUserState = this.defaultUser;
  }

  // Obtener usuarios disponibles para el selector
  async getAvailableUsers() {
    try {
      // Devolver usuarios simulados
      return {
        success: true,
        users: this.mockUsers
      };
    } catch (error) {
      console.error('Error getting available users:', error);
      throw error;
    }
  }

  getUserById(userId) {
    try {
      const user = this.mockUsers.find(u => u.id === userId);
      if (!user) {
        throw new Error('User not found');
      }
      
      return {
        success: true,
        user: user
      };
    } catch (error) {
      console.error('Error fetching user by ID:', error);
      throw error;
    }
  }
}

// Exportar una única instancia para mantener el estado
const userServiceInstance = new UserService();
export default userServiceInstance;