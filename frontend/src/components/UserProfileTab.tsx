import React from 'react';
import { UserCheck, Loader2, Save, Code, Layers, Target, Cpu, Sparkles, Tag, Brain } from 'lucide-react';
import { UserProfileData } from './types';

interface UserProfileTabProps {
  userProfile: UserProfileData;
  setUserProfile: React.Dispatch<React.SetStateAction<UserProfileData>>;
  isSavingProfile: boolean;
  profileSaveSuccess: boolean;
  handleSaveProfile: () => void;
}

export const UserProfileTab: React.FC<UserProfileTabProps> = ({
  userProfile,
  setUserProfile,
  isSavingProfile,
  profileSaveSuccess,
  handleSaveProfile,
}) => {
  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-100 flex items-center gap-3">
            <UserCheck className="w-8 h-8 text-indigo-400" />
            User Profile & Preferences
          </h2>
          <p className="text-gray-400 mt-1">
            Automatically learned by MemOS chat analysis engine. You can manually edit any field below.
          </p>
        </div>

        <button
          onClick={handleSaveProfile}
          disabled={isSavingProfile}
          className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-5 py-2.5 rounded-xl shadow-lg shadow-indigo-950/40 transition duration-200 disabled:opacity-50"
        >
          {isSavingProfile ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          <span>{profileSaveSuccess ? 'Saved Successfully!' : 'Save Changes'}</span>
        </button>
      </div>

      {/* Profile Grid Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Preferred Languages */}
        <div className="bg-[#111827]/80 p-6 rounded-2xl border border-gray-800 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-semibold text-indigo-300 flex items-center gap-2">
              <Code className="w-4 h-4 text-indigo-400" /> Preferred Programming Languages
            </label>
            <span className="text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded-full font-medium">
              Auto-Learned
            </span>
          </div>
          <input
            type="text"
            value={userProfile.preferred_languages.join(', ')}
            onChange={(e) =>
              setUserProfile({ ...userProfile, preferred_languages: e.target.value.split(',').map((s) => s.trim()) })
            }
            className="w-full bg-gray-900 border border-gray-700/80 rounded-xl px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
            placeholder="Python, TypeScript, Rust..."
          />
        </div>

        {/* Preferred Frameworks */}
        <div className="bg-[#111827]/80 p-6 rounded-2xl border border-gray-800 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-semibold text-purple-300 flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-400" /> Preferred Frameworks
            </label>
            <span className="text-[10px] bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded-full font-medium">
              Auto-Learned
            </span>
          </div>
          <input
            type="text"
            value={userProfile.preferred_frameworks.join(', ')}
            onChange={(e) =>
              setUserProfile({ ...userProfile, preferred_frameworks: e.target.value.split(',').map((s) => s.trim()) })
            }
            className="w-full bg-gray-900 border border-gray-700/80 rounded-xl px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
            placeholder="FastAPI, Next.js, PyTorch..."
          />
        </div>

        {/* Current Projects */}
        <div className="bg-[#111827]/80 p-6 rounded-2xl border border-gray-800 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-semibold text-emerald-300 flex items-center gap-2">
              <Target className="w-4 h-4 text-emerald-400" /> Current Projects
            </label>
            <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-medium">
              Auto-Learned
            </span>
          </div>
          <input
            type="text"
            value={userProfile.current_projects.join(', ')}
            onChange={(e) =>
              setUserProfile({ ...userProfile, current_projects: e.target.value.split(',').map((s) => s.trim()) })
            }
            className="w-full bg-gray-900 border border-gray-700/80 rounded-xl px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
            placeholder="MemOS, Ollama Desktop Companion..."
          />
        </div>

        {/* Skills & Technologies */}
        <div className="bg-[#111827]/80 p-6 rounded-2xl border border-gray-800 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-semibold text-blue-300 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-400" /> Skills & Technologies
            </label>
            <span className="text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded-full font-medium">
              Auto-Learned
            </span>
          </div>
          <input
            type="text"
            value={userProfile.technologies.join(', ')}
            onChange={(e) =>
              setUserProfile({ ...userProfile, technologies: e.target.value.split(',').map((s) => s.trim()) })
            }
            className="w-full bg-gray-900 border border-gray-700/80 rounded-xl px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
            placeholder="Qdrant, Neo4j, Redis, PostgreSQL..."
          />
        </div>

        {/* Writing Style */}
        <div className="bg-[#111827]/80 p-6 rounded-2xl border border-gray-800 shadow-xl space-y-3 md:col-span-2">
          <label className="text-sm font-semibold text-amber-300 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-400" /> Writing Style & Response Formatting
          </label>
          <input
            type="text"
            value={userProfile.writing_style}
            onChange={(e) => setUserProfile({ ...userProfile, writing_style: e.target.value })}
            className="w-full bg-gray-900 border border-gray-700/80 rounded-xl px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
            placeholder="Concise, technical, direct with production code examples..."
          />
        </div>

        {/* Learning Goals */}
        <div className="bg-[#111827]/80 p-6 rounded-2xl border border-gray-800 shadow-xl space-y-3">
          <label className="text-sm font-semibold text-rose-300 flex items-center gap-2">
            <Tag className="w-4 h-4 text-rose-400" /> Learning Goals
          </label>
          <input
            type="text"
            value={userProfile.learning_goals.join(', ')}
            onChange={(e) =>
              setUserProfile({ ...userProfile, learning_goals: e.target.value.split(',').map((s) => s.trim()) })
            }
            className="w-full bg-gray-900 border border-gray-700/80 rounded-xl px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
            placeholder="Build local agent memory system..."
          />
        </div>

        {/* Preferred Model */}
        <div className="bg-[#111827]/80 p-6 rounded-2xl border border-gray-800 shadow-xl space-y-3">
          <label className="text-sm font-semibold text-cyan-300 flex items-center gap-2">
            <Brain className="w-4 h-4 text-cyan-400" /> Preferred AI Model
          </label>
          <select
            value={userProfile.preferred_model}
            onChange={(e) => setUserProfile({ ...userProfile, preferred_model: e.target.value })}
            className="w-full bg-gray-900 border border-gray-700/80 rounded-xl px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
          >
            <option value="qwen3.5:9b">qwen3.5:9b (Recommended)</option>
            <option value="llama3:latest">llama3:latest</option>
            <option value="mistral:latest">mistral:latest</option>
            <option value="codellama:latest">codellama:latest</option>
          </select>
        </div>
      </div>
    </div>
  );
};
