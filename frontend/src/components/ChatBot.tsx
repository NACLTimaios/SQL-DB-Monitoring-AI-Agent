import { useState, useEffect, useRef } from 'react';
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
        const token = localStorage.getItem('access_token');
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
      const token = localStorage.getItem('access_token');
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
    <div className="flex flex-col h-full w-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl overflow-hidden">
      <div className="bg-gradient-to-r from-cyan-900/30 to-blue-900/30 border-b border-slate-700 px-4 py-3 flex-shrink-0">
        <h3 className="text-lg font-semibold text-white">Database Assistant</h3>
        <p className="text-xs text-slate-400 mt-1">Ask questions about your database • Powered by AI</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
        {messages.length === 0 && !error && (
          <div className="text-center text-gray-500 py-8">
            <p className="text-2xl">No messages yet. Start by asking about your database.</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className="space-y-2 w-full">
            {/* User message */}
            <div className="flex justify-end w-full">
              <div className="bg-cyan-900/40 text-cyan-100 px-4 py-2 rounded-lg max-w-2xl md:max-w-3xl lg:max-w-4xl break-words text-2xl">
                {msg.user_message}
              </div>
            </div>

            {/* Assistant message */}
            <div className="flex justify-start w-full">
              <div className="bg-slate-700/50 text-slate-100 px-4 py-2 rounded-lg max-w-2xl md:max-w-3xl lg:max-w-4xl break-words">
                <p className="text-2xl whitespace-pre-wrap">
                  {msg.assistant_message}
                </p>
                {msg.tools_used.length > 0 && (
                  <div className="text-lg text-slate-400 mt-2 pt-2 border-t border-slate-600">
                    Tools: {msg.tools_used.join(', ')}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {error && (
          <div className="bg-red-900/20 border border-red-500/30 text-red-400 px-4 py-2 rounded-lg text-lg">
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-slate-700 p-4 bg-slate-900/50">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
            placeholder="Ask about your database..."
            className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 disabled:opacity-50 text-lg"
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || !input.trim()}
            className="bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition-colors text-lg"
          >
            {loading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
