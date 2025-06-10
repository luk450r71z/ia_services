import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';

// Mock axios
vi.mock('axios');

// Import the API service - update path as needed
// This is a placeholder - you'll need to create this service
import apiService from '../src/services/apiService';

describe('API Service', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('should create a session', async () => {
    const mockResponse = { data: { session_id: 'test_session_id' } };
    axios.post.mockResolvedValue(mockResponse);

    const credentials = { username: 'user', password: 'pass' };
    const result = await apiService.createSession(credentials);

    expect(axios.post).toHaveBeenCalledWith('/api/chat/session/auth', credentials);
    expect(result).toEqual(mockResponse.data);
  });

  it('should initiate a questionnaire', async () => {
    const mockResponse = { data: { questionnaire_id: 'test_questionnaire_id' } };
    axios.post.mockResolvedValue(mockResponse);

    const payload = { 
      session_id: 'test_session_id',
      user_data: { name: 'Test User' }
    };
    const result = await apiService.initiateQuestionnaire(payload);

    expect(axios.post).toHaveBeenCalledWith('/api/chat/questionnarie/initiate', payload);
    expect(result).toEqual(mockResponse.data);
  });

  it('should start a questionnaire', async () => {
    const mockResponse = { data: { status: 'started' } };
    axios.post.mockResolvedValue(mockResponse);

    const payload = { 
      session_id: 'test_session_id',
      questionnaire_id: 'test_questionnaire_id'
    };
    const result = await apiService.startQuestionnaire(payload);

    expect(axios.post).toHaveBeenCalledWith('/api/chat/questionnarie/start', payload);
    expect(result).toEqual(mockResponse.data);
  });

  it('should handle API errors', async () => {
    const errorMessage = 'Network Error';
    axios.post.mockRejectedValue(new Error(errorMessage));

    try {
      await apiService.createSession({ username: 'user', password: 'pass' });
      // Should not reach here
      expect(true).toBe(false);
    } catch (error) {
      expect(error.message).toBe(errorMessage);
    }
  });
}); 