import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

interface Message {
  user_message: string;
  assistant_message: string;
  tools_used: string[];
  created_at: string;
}

export default function ChatBot() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get('/api/chatbot/history?limit=50', {
          headers: { Authorization: `Bearer ${token}` },
        });
        setMessages(response.data);
        setError(null);
      } catch (err) {
        console.error('Failed to load chat history:', err);
        setError('Failed to load chat history');
      }
    };

    loadHistory();
  }, []);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = input;
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        '/api/chatbot/chat',
        { message: userMessage },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const data = response.data;
      setMessages((prev) => [
        ...prev,
        {
          user_message: userMessage,
          assistant_message: data.assistant_message,
          tools_used: data.tools_used || [],
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err: any) {
      console.error('Chat error:', err);
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          'Failed to send message'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-96 bg-brand-surface border border-brand-border rounded-xl">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !error && (
          <div className="text-center text-gray-500 py-8">
            <p>No messages yet. Start by asking about your database.</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className="space-y-2">
            {/* User message */}
            <div className="flex justify-end">
              <div className="bg-cyan-900/40 text-cyan-100 px-4 py-2 rounded-lg max-w-xs break-words">
                {msg.user_message}
              </div>
            </div>

            {/* Assistant message */}
            <div className="flex justify-start">
              <div className="bg-gray-800/50 text-gray-100 px-4 py-2 rounded-lg max-w-xs break-words">
                <p className="text-sm whitespace-pre-wrap">
                  {msg.assistant_message}
                </p>
                {msg.tools_used.length > 0 && (
                  <div className="text-xs text-gray-400 mt-2 pt-2 border-t border-gray-700">
                    🔧 Tools: {msg.tools_used.join(', ')}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {error && (
          <div className="bg-red-900/20 border border-red-500/30 text-red-400 px-4 py-2 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-700 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
            placeholder="Ask about your database..."
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || !input.trim()}
            className="bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition-colors"
          >
            {loading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
