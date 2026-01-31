/**
 * Groq AI Provider
 *
 * Implements the AIProvider interface for Groq cloud inference.
 * Uses OpenAI-compatible API at api.groq.com.
 * Supports chat, function calling, and streaming.
 */

const axios = require('axios');
const { AIProvider, DEFAULT_STREAM_TIMEOUT, CHUNK_TIMEOUT } = require('./base');
const { onlineConfig } = require('../config');
const { retryWithBackoff, ValidationError } = require('../../../utils/errorHandler');

/**
 * Groq API endpoints (OpenAI-compatible)
 */
const ENDPOINTS = {
  CHAT: '/chat/completions',
  MODELS: '/models',
  AUDIO_TRANSCRIPTIONS: '/audio/transcriptions',
  AUDIO_SPEECH: '/audio/speech'
};

class GroqProvider extends AIProvider {
  /**
   * @param {Object} options - Provider options
   * @param {string} options.apiKey - Groq API key (required for API calls)
   * @param {number} options.timeout - Request timeout
   */
  constructor(options = {}) {
    // Use config timeouts as defaults
    super('groq', {
      timeout: options.timeout || onlineConfig.defaults.timeout,
      streamTimeout: options.streamTimeout || onlineConfig.defaults.streamTimeout,
      chunkTimeout: options.chunkTimeout || 60000,
      ...options
    });

    this.baseUrl = onlineConfig.baseUrl;
    this.apiKey = options.apiKey || null;
    this.defaultModel = options.defaultModel || onlineConfig.models.response.name;
  }

  /**
   * Set the API key (can be set after construction)
   * @param {string} apiKey - Groq API key
   */
  setApiKey(apiKey) {
    this.apiKey = apiKey;
  }

  /**
   * Get authorization headers
   * @returns {Object} Headers object
   * @throws {ValidationError} If API key is not set
   */
  getHeaders() {
    if (!this.apiKey) {
      throw new ValidationError('Groq API key is required. Add your key in Settings.');
    }

    return {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json'
    };
  }

  /**
   * Send a chat message and get a response
   * @param {Object} params - Chat parameters
   * @returns {Promise<string>} AI response text
   */
  async chat(params) {
    const { message, messages: history, model, systemPrompt, options = {} } = params;

    this.validateParams(params, ['message']);

    const modelName = model || this.defaultModel;
    const messagesArray = this.buildMessages(systemPrompt, history, message);

    this.log(`Chat request to model: ${modelName}`, {
      messageCount: messagesArray.length,
      lastMessageLength: message.length
    });

    try {
      const response = await retryWithBackoff(
        () => this.withTimeout(
          axios.post(
            `${this.baseUrl}${ENDPOINTS.CHAT}`,
            {
              model: modelName,
              messages: messagesArray,
              temperature: options.temperature ?? onlineConfig.defaults.temperature,
              top_p: options.topP ?? onlineConfig.defaults.topP,
              max_tokens: options.maxTokens ?? onlineConfig.defaults.maxTokens,
              stream: false
            },
            { headers: this.getHeaders() }
          ),
          this.timeout,
          'Chat request timed out'
        ),
        {
          maxRetries: 2,
          initialDelay: 1000,
          onRetry: (attempt, max, delay) => {
            this.log(`Request failed, retrying (${attempt}/${max}) after ${delay}ms`);
          }
        }
      );

      if (!response.data?.choices?.[0]?.message?.content) {
        throw this.createError('Invalid response format from Groq');
      }

      const content = response.data.choices[0].message.content;

      this.logDebug('Chat response received', {
        length: content.length,
        usage: response.data.usage
      });

      return content;

    } catch (error) {
      if (error.isOperational) throw error;
      throw this.handleHttpError(error, 'chat');
    }
  }

  /**
   * Send a chat message with function calling support
   * @param {Object} params - Chat parameters
   * @returns {Promise<Object>} Response with potential function calls
   */
  async chatWithTools(params) {
    const { message, messages: history, model, systemPrompt, tools, options = {} } = params;

    this.validateParams(params, ['message', 'tools']);

    if (!Array.isArray(tools) || tools.length === 0) {
      throw this.createError('Tools array is required and must not be empty');
    }

    const modelName = model || this.defaultModel;
    const messagesArray = this.buildMessages(systemPrompt, history, message);

    // Convert tools to OpenAI function format
    const openaiTools = tools.map(tool => ({
      type: 'function',
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.parameters || { type: 'object', properties: {} }
      }
    }));

    this.log(`Tool chat request to model: ${modelName}`, {
      messageCount: messagesArray.length,
      toolCount: openaiTools.length
    });

    try {
      const response = await retryWithBackoff(
        () => this.withTimeout(
          axios.post(
            `${this.baseUrl}${ENDPOINTS.CHAT}`,
            {
              model: modelName,
              messages: messagesArray,
              tools: openaiTools,
              tool_choice: options.toolChoice || 'auto',
              temperature: options.temperature ?? onlineConfig.defaults.temperature,
              top_p: options.topP ?? onlineConfig.defaults.topP,
              max_tokens: options.maxTokens ?? onlineConfig.defaults.maxTokens,
              stream: false
            },
            { headers: this.getHeaders() }
          ),
          this.timeout,
          'Tool chat request timed out'
        ),
        {
          maxRetries: 2,
          initialDelay: 1000
        }
      );

      if (!response.data?.choices?.[0]?.message) {
        throw this.createError('Invalid response format from Groq');
      }

      const responseMessage = response.data.choices[0].message;
      const finishReason = response.data.choices[0].finish_reason;

      const result = {
        content: responseMessage.content || null,
        toolCalls: null,
        finishReason: finishReason
      };

      // Check for tool calls in response
      if (responseMessage.tool_calls && responseMessage.tool_calls.length > 0) {
        result.toolCalls = responseMessage.tool_calls.map(tc => ({
          id: tc.id,
          name: tc.function?.name,
          arguments: tc.function?.arguments
        }));
      }

      this.logDebug('Tool chat response received', {
        hasContent: !!result.content,
        toolCallCount: result.toolCalls?.length || 0,
        finishReason
      });

      return result;

    } catch (error) {
      if (error.isOperational) throw error;
      throw this.handleHttpError(error, 'tool chat');
    }
  }

  /**
   * Send a chat message and stream the response
   * @param {Object} params - Chat parameters
   * @yields {string} Response chunks
   */
  async *stream(params) {
    const { message, messages: history, model, systemPrompt, options = {} } = params;

    this.validateParams(params, ['message']);

    const modelName = model || this.defaultModel;
    const messagesArray = this.buildMessages(systemPrompt, history, message);

    this.log(`Stream request to model: ${modelName}`, {
      messageCount: messagesArray.length
    });

    let response;
    try {
      response = await axios.post(
        `${this.baseUrl}${ENDPOINTS.CHAT}`,
        {
          model: modelName,
          messages: messagesArray,
          temperature: options.temperature ?? onlineConfig.defaults.temperature,
          top_p: options.topP ?? onlineConfig.defaults.topP,
          max_tokens: options.maxTokens ?? onlineConfig.defaults.maxTokens,
          stream: true
        },
        {
          headers: this.getHeaders(),
          responseType: 'stream',
          timeout: this.streamTimeout
        }
      );
    } catch (error) {
      throw this.handleHttpError(error, 'stream initiation');
    }

    let fullResponse = '';
    let lastChunkTime = Date.now();

    try {
      for await (const chunk of response.data) {
        // Check for chunk timeout
        const now = Date.now();
        if (now - lastChunkTime > this.chunkTimeout) {
          throw this.createError(`Stream timed out - no data received for ${this.chunkTimeout / 1000} seconds`);
        }
        lastChunkTime = now;

        const lines = chunk.toString().split('\n').filter(line => line.trim());

        for (const line of lines) {
          // Skip [DONE] marker
          if (line.trim() === 'data: [DONE]') {
            this.logDebug('Stream completed', { totalLength: fullResponse.length });
            return;
          }

          // Parse SSE data
          const dataMatch = line.match(/^data: (.+)$/);
          if (!dataMatch) continue;

          const data = dataMatch[1];
          if (!data || data === '[DONE]') continue;

          try {
            const json = JSON.parse(data);
            const content = json.choices?.[0]?.delta?.content;

            if (content) {
              fullResponse += content;
              yield content;
            }

            // Check for stream completion
            if (json.choices?.[0]?.finish_reason) {
              this.logDebug('Stream finished', {
                reason: json.choices[0].finish_reason,
                totalLength: fullResponse.length
              });
            }
          } catch (parseError) {
            // Skip malformed JSON lines
            this.logDebug('Skipping malformed SSE data', { data: data.substring(0, 100) });
          }
        }
      }
    } catch (error) {
      if (error.isOperational) throw error;
      throw this.handleHttpError(error, 'streaming');
    }
  }

  /**
   * Check if Groq is available (requires API key)
   * @returns {Promise<boolean>}
   */
  async isAvailable() {
    if (!this.apiKey) {
      return false;
    }

    try {
      const response = await axios.get(
        `${this.baseUrl}${ENDPOINTS.MODELS}`,
        {
          headers: this.getHeaders(),
          timeout: 5000
        }
      );
      return response.status === 200;
    } catch (error) {
      this.logDebug('Availability check failed', { error: error.message });
      return false;
    }
  }

  /**
   * Get available models from Groq
   * @returns {Promise<Array>} List of available models
   */
  async getModels() {
    try {
      const response = await axios.get(
        `${this.baseUrl}${ENDPOINTS.MODELS}`,
        {
          headers: this.getHeaders(),
          timeout: 10000
        }
      );

      if (!response.data?.data) {
        return [];
      }

      return response.data.data
        .filter(model => model.active !== false)
        .map(model => ({
          id: model.id,
          name: model.id,
          ownedBy: model.owned_by,
          contextWindow: model.context_window,
          created: model.created
        }))
        .sort((a, b) => a.id.localeCompare(b.id));

    } catch (error) {
      this.logError('Failed to fetch models', { error: error.message });
      throw this.handleHttpError(error, 'fetching models');
    }
  }

  /**
   * Transcribe audio using Whisper via Groq
   * @param {Buffer|ReadStream} audio - Audio data
   * @param {Object} options - Transcription options
   * @returns {Promise<Object>} Transcription result
   */
  async transcribe(audio, options = {}) {
    const FormData = require('form-data');
    const form = new FormData();

    form.append('file', audio, {
      filename: options.filename || 'audio.wav',
      contentType: options.contentType || 'audio/wav'
    });
    form.append('model', options.model || onlineConfig.models.stt.name);

    if (options.language) {
      form.append('language', options.language);
    }
    if (options.prompt) {
      form.append('prompt', options.prompt);
    }

    try {
      const response = await axios.post(
        `${this.baseUrl}${ENDPOINTS.AUDIO_TRANSCRIPTIONS}`,
        form,
        {
          headers: {
            ...this.getHeaders(),
            ...form.getHeaders()
          },
          timeout: 60000
        }
      );

      return {
        text: response.data.text,
        language: response.data.language,
        duration: response.data.duration
      };

    } catch (error) {
      throw this.handleHttpError(error, 'audio transcription');
    }
  }

  /**
   * Generate speech from text using PlayAI TTS via Groq
   * @param {string} text - Text to synthesize
   * @param {Object} options - TTS options
   * @returns {Promise<Buffer>} Audio data
   */
  async textToSpeech(text, options = {}) {
    try {
      const response = await axios.post(
        `${this.baseUrl}${ENDPOINTS.AUDIO_SPEECH}`,
        {
          model: options.model || onlineConfig.models.tts.name,
          input: text,
          voice: options.voice || 'alloy',
          response_format: options.format || 'mp3',
          speed: options.speed || 1.0
        },
        {
          headers: this.getHeaders(),
          responseType: 'arraybuffer',
          timeout: 60000
        }
      );

      return Buffer.from(response.data);

    } catch (error) {
      throw this.handleHttpError(error, 'text-to-speech');
    }
  }
}

module.exports = GroqProvider;
