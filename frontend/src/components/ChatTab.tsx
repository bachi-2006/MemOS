import React from 'react';
import { MessageSquare, Sparkles, Cpu, Brain, Loader2 } from 'lucide-react';
import { ChatMessage } from './types';

interface ChatTabProps {
  messages: ChatMessage[];
  inputPrompt: string;
  setInputPrompt: (val: string) => void;
  isSending: boolean;
  personalizedEnabled: boolean;
  setPersonalizedEnabled: (val: boolean) => void;
  handleSendMessage: () => void;
  handleAnalyzeChat: () => void;
}

export const ChatTab: React.FC<ChatTabProps> = ({
  messages,
  inputPrompt,
  setInputPrompt,
  isSending,
  personalizedEnabled,
  setPersonalizedEnabled,
  handleSendMessage,
  handleAnalyzeChat,
}) => {
  return (
    <div className="h-full flex flex-col max-w-5xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between bg-[#111827]/80 backdrop-blur-md p-4 rounded-2xl border border-gray-800/80 shadow-lg">
        <div>
          <h2 className="text-xl font-bold text-gray-100 flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-indigo-400" />
            Ollama Conversation Mode
          </h2>
          <div className="flex items-center gap-2 mt-1">
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-medium border flex items-center gap-1.5 ${
                personalizedEnabled
                  ? 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30'
                  : 'bg-gray-800 text-gray-400 border-gray-700'
              }`}
            >
              {personalizedEnabled ? (
                <>
                  <Sparkles className="w-3 h-3 text-indigo-400" />
                  ✨ Personalized Context Active (Memories + Graph + Profile + Projects + Pinned)
                </>
              ) : (
                <>
                  <Cpu className="w-3 h-3 text-gray-400" />
                  ⚡ Standard Ollama Mode (Raw Prompt)
                </>
              )}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Toggle Switch */}
          <button
            onClick={() => setPersonalizedEnabled(!personalizedEnabled)}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl border text-xs font-semibold transition-all duration-200 ${
              personalizedEnabled
                ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/40 shadow-inner'
                : 'bg-gray-800/80 text-gray-400 border-gray-700 hover:bg-gray-800'
            }`}
          >
            <Sparkles className={`w-3.5 h-3.5 ${personalizedEnabled ? 'text-indigo-400' : 'text-gray-500'}`} />
            <span>✨ Personalized Responses</span>
            <div
              className={`w-8 h-4 rounded-full p-0.5 transition-colors duration-200 flex items-center ${
                personalizedEnabled ? 'bg-indigo-600 justify-end' : 'bg-gray-700 justify-start'
              }`}
            >
              <div className="w-3 h-3 rounded-full bg-white shadow-sm"></div>
            </div>
          </button>

          {/* Action Buttons */}
          <button
            onClick={handleAnalyzeChat}
            className="flex items-center gap-1.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium px-3.5 py-2 rounded-xl shadow-lg shadow-indigo-900/30 border border-indigo-400/30 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
          >
            <Brain className="w-4 h-4 text-indigo-200" />
            <span className="text-xs font-semibold">🧠 Analyze Chat</span>
          </button>

          <button
            onClick={async () => {
              try {
                const res = await fetch('http://localhost:8000/api/v1/memory/optimize', { method: 'POST' });
                if (res.ok) {
                  const data = await res.json();
                  alert(`🧹 Memory Optimization Complete!\nScanned: ${data.memories_scanned}\nCompressed: ${data.memories_compressed}\nForgotten: ${data.memories_forgotten}`);
                } else {
                  alert('Memory optimization returned error.');
                }
              } catch (e: any) {
                alert(`Optimization notice: ${e.message}`);
              }
            }}
            className="flex items-center gap-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 font-medium px-3.5 py-2 rounded-xl border border-gray-700 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
            title="Sweep, recalculate importance, compress older memories, and prune graph"
          >
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-xs font-semibold">🧹 Optimize Memory</span>
          </button>
        </div>
      </div>

      {/* Chat Transcript Area */}
      <div className="flex-1 bg-[#111827]/60 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6 flex flex-col justify-between overflow-hidden shadow-2xl">
        <div className="flex-1 overflow-y-auto space-y-4 pr-2">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-2xl px-5 py-3.5 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-br-none shadow-md shadow-indigo-950/40'
                    : 'bg-gray-800/80 text-gray-200 border border-gray-700/60 rounded-bl-none shadow-md'
                }`}
              >
                <div className="text-[10px] uppercase font-bold tracking-wider mb-1 opacity-60">
                  {msg.role === 'user' ? 'You' : 'Ollama LLM'}
                </div>
                {msg.content}
              </div>
            </div>
          ))}
        </div>

        {/* Chat Input Bar */}
        <div className="mt-4 flex space-x-3 pt-4 border-t border-gray-800/80">
          <input
            type="text"
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type a message or discuss your project..."
            className="flex-1 bg-gray-900/90 border border-gray-700/80 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 text-gray-100 placeholder-gray-500 transition-colors"
          />
          <button
            onClick={handleSendMessage}
            disabled={isSending}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl font-medium text-sm transition-all duration-200 shadow-md disabled:opacity-50"
          >
            {isSending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
};
