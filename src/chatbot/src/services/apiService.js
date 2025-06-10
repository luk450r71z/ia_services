import axios from 'axios';

const API_BASE_URL = process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000';

const apiService = {
  /**
   * Create a new session by authenticating the user
   * @param {Object} credentials - User credentials
   * @param {string} credentials.username - Username
   * @param {string} credentials.password - Password
   * @returns {Promise<Object>} - Session data
   */
  async createSession(credentials) {
    try {
      const response = await axios.post('/api/chat/session/auth', credentials);
      return response.data;
    } catch (error) {
      console.error('Error creating session:', error);
      throw error;
    }
  },

  /**
   * Initiate a questionnaire
   * @param {Object} payload - Questionnaire data
   * @param {string} payload.session_id - Session ID
   * @param {Object} payload.user_data - User data
   * @returns {Promise<Object>} - Questionnaire data
   */
  async initiateQuestionnaire(payload) {
    try {
      const response = await axios.post('/api/chat/questionnarie/initiate', payload);
      return response.data;
    } catch (error) {
      console.error('Error initiating questionnaire:', error);
      throw error;
    }
  },

  /**
   * Start a questionnaire
   * @param {Object} payload - Questionnaire data
   * @param {string} payload.session_id - Session ID
   * @param {string} payload.questionnaire_id - Questionnaire ID
   * @returns {Promise<Object>} - Questionnaire status
   */
  async startQuestionnaire(payload) {
    try {
      const response = await axios.post('/api/chat/questionnarie/start', payload);
      return response.data;
    } catch (error) {
      console.error('Error starting questionnaire:', error);
      throw error;
    }
  }
};

export default apiService; 