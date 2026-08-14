import React from 'react';
import { Brain, X, CheckCircle2, Loader2, Code, Target, Check } from 'lucide-react';
import { AnalysisResult } from './types';

interface AnalysisModalProps {
  showModal: boolean;
  onClose: () => void;
  isAnalyzing: boolean;
  analysisStep: number;
  analysisResult: AnalysisResult | null;
}

export const AnalysisModal: React.FC<AnalysisModalProps> = ({
  showModal,
  onClose,
  isAnalyzing,
  analysisStep,
  analysisResult,
}) => {
  if (!showModal) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md transition-all duration-300">
      <div className="bg-[#111827] border border-indigo-500/30 rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-6 border-b border-gray-800 flex items-center justify-between bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-900">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-indigo-600/20 border border-indigo-500/30 rounded-2xl text-indigo-400">
              <Brain className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-100 flex items-center gap-2">
                🧠 MemOS Chat Analysis Engine
              </h3>
              <p className="text-xs text-gray-400">Extracting entities, facts, projects & updating graph memory</p>
            </div>
          </div>

          {!isAnalyzing && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-200 p-2 rounded-xl hover:bg-gray-800/60 transition"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Progress Bar & Animated Steps when Analyzing */}
          {isAnalyzing && (
            <div className="space-y-6 py-4">
              <div className="flex justify-between items-center text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                <span>Running Multi-Step Analysis</span>
                <span>Step {analysisStep} of 4</span>
              </div>

              <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-indigo-500 to-purple-500 h-full transition-all duration-500"
                  style={{ width: `${(analysisStep / 4) * 100}%` }}
                ></div>
              </div>

              <div className="space-y-3.5">
                <div
                  className={`flex items-center space-x-3 text-sm transition-all duration-300 ${
                    analysisStep >= 1 ? 'text-indigo-300 font-medium' : 'text-gray-600'
                  }`}
                >
                  {analysisStep > 1 ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                  )}
                  <span>Reading conversation transcript & ignoring greetings / small talk</span>
                </div>

                <div
                  className={`flex items-center space-x-3 text-sm transition-all duration-300 ${
                    analysisStep >= 2 ? 'text-indigo-300 font-medium' : 'text-gray-600'
                  }`}
                >
                  {analysisStep > 2 ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : analysisStep === 2 ? (
                    <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border border-gray-700" />
                  )}
                  <span>Extracting important facts, entities, projects, technologies & user preferences</span>
                </div>

                <div
                  className={`flex items-center space-x-3 text-sm transition-all duration-300 ${
                    analysisStep >= 3 ? 'text-indigo-300 font-medium' : 'text-gray-600'
                  }`}
                >
                  {analysisStep > 3 ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : analysisStep === 3 ? (
                    <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border border-gray-700" />
                  )}
                  <span>Removing duplicate memories & calculating importance & confidence scores</span>
                </div>

                <div
                  className={`flex items-center space-x-3 text-sm transition-all duration-300 ${
                    analysisStep >= 4 ? 'text-indigo-300 font-medium' : 'text-gray-600'
                  }`}
                >
                  {analysisStep >= 4 ? (
                    <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border border-gray-700" />
                  )}
                  <span>Syncing Neo4j Knowledge Graph triples & Qdrant vector embeddings</span>
                </div>
              </div>
            </div>
          )}

          {/* Analysis Result Card Output */}
          {!isAnalyzing && analysisResult && (
            <div className="space-y-6">
              {/* Summary Box */}
              <div className="p-4 bg-indigo-950/40 border border-indigo-500/30 rounded-2xl">
                <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1">
                  Memory Summary
                </div>
                <p className="text-sm text-gray-200 leading-relaxed font-medium">{analysisResult.summary}</p>
              </div>

              {/* Quick Metric Pills */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-gray-900/80 p-3 rounded-xl border border-gray-800 text-center">
                  <div className="text-xs text-gray-400">Facts Extracted</div>
                  <div className="text-lg font-bold text-emerald-400">{analysisResult.facts.length}</div>
                </div>
                <div className="bg-gray-900/80 p-3 rounded-xl border border-gray-800 text-center">
                  <div className="text-xs text-gray-400">Graph Triples</div>
                  <div className="text-lg font-bold text-purple-400">{analysisResult.graph_nodes_created}</div>
                </div>
                <div className="bg-gray-900/80 p-3 rounded-xl border border-gray-800 text-center">
                  <div className="text-xs text-gray-400">Duplicates Filtered</div>
                  <div className="text-lg font-bold text-indigo-400">{analysisResult.duplicates_removed}</div>
                </div>
              </div>

              {/* Extracted Technologies & Frameworks */}
              {analysisResult.technologies.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Code className="w-3.5 h-3.5 text-indigo-400" /> Technologies & Frameworks
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {analysisResult.technologies.map((t, idx) => (
                      <span
                        key={idx}
                        className="bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs px-3 py-1 rounded-full font-medium"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Extracted Projects */}
              {analysisResult.projects.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Target className="w-3.5 h-3.5 text-purple-400" /> Detected Projects
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {analysisResult.projects.map((p, idx) => (
                      <span
                        key={idx}
                        className="bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs px-3 py-1 rounded-full font-medium"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Extracted Facts List */}
              {analysisResult.facts.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                    Important Facts
                  </div>
                  <ul className="space-y-2">
                    {analysisResult.facts.map((fact, idx) => (
                      <li
                        key={idx}
                        className="text-xs bg-gray-900/60 border border-gray-800 p-2.5 rounded-xl text-gray-300 flex items-start gap-2"
                      >
                        <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{fact}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-gray-800 bg-gray-900/50 flex justify-end">
          <button
            onClick={onClose}
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-5 py-2 rounded-xl text-sm transition"
          >
            Close Summary
          </button>
        </div>
      </div>
    </div>
  );
};
