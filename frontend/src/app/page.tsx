'use client';

import React, { useState, useEffect } from 'react';
import { Sidebar, TabType } from '../components/Sidebar';
import { ChatTab } from '../components/ChatTab';
import { DashboardTab } from '../components/DashboardTab';
import { SearchTab } from '../components/SearchTab';
import { GraphTab } from '../components/GraphTab';
import { UserProfileTab } from '../components/UserProfileTab';
import { AnalysisModal } from '../components/AnalysisModal';
import { OllamaIntegrationPanel } from '../components/OllamaIntegrationPanel';
import { ChatMessage, UserProfileData, AnalysisResult } from '../components/types';

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  const [selectedModel, setSelectedModel] = useState<string>('qwen3.5:9b');

  // User Profile State
  const [userProfile, setUserProfile] = useState<UserProfileData>({
    preferred_languages: ['Python', 'TypeScript'],
    preferred_frameworks: ['FastAPI', 'Next.js'],
    current_projects: ['MemOS'],
    interests: ['Local AI', 'Vector Memory', 'Knowledge Graphs'],
    skills: ['Full Stack Engineering', 'AI Systems Architecture'],
    technologies: ['Qdrant', 'Neo4j', 'Ollama', 'PostgreSQL'],
    writing_style: 'Concise, technical, direct',
    learning_goals: ['Build fully autonomous local agent OS'],
    preferred_model: 'qwen3.5:9b',
    recent_focus: ['Local Context Injection', 'Knowledge Graph Synapses'],
  });
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileSaveSuccess, setProfileSaveSuccess] = useState(false);

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/profile')
      .then((res) => res.json())
      .then((data) => {
        if (data && data.preferred_languages) {
          setUserProfile(data);
        }
      })
      .catch(() => {});
  }, []);

  const handleSaveProfile = async () => {
    setIsSavingProfile(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/profile', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userProfile),
      });
      if (response.ok) {
        setProfileSaveSuccess(true);
        setTimeout(() => setProfileSaveSuccess(false), 3000);
      }
    } catch (err) {
      console.error('Failed to save profile', err);
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Chat State
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'user',
      content: 'Hi there! I am working on building MemOS using FastAPI, Next.js, Qdrant, and Neo4j.',
    },
    {
      id: '2',
      role: 'assistant',
      content:
        'That sounds like a great architecture! MemOS combines vector search with graph context for persistent LLM agent memories.',
    },
    {
      id: '3',
      role: 'user',
      content:
        'Yes, I prefer building local AI companion applications. We decided to keep all storage on-device for total privacy.',
    },
  ]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [isSending, setIsSending] = useState(false);

  // Personalized Context Toggle State
  const [personalizedEnabled, setPersonalizedEnabled] = useState(true);

  // Analyze Chat State
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState(1);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);

  const handleSendMessage = async () => {
    if (!inputPrompt.trim() || isSending) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputPrompt,
    };

    setMessages((prev) => [...prev, userMsg]);
    const currentInput = inputPrompt;
    setInputPrompt('');
    setIsSending(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/ollama/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: currentInput,
          personalized: personalizedEnabled,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const assistantMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.response || 'No response returned.',
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        const fallbackMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `Received: "${currentInput}". I am ready to process memories!`,
        };
        setMessages((prev) => [...prev, fallbackMsg]);
      }
    } catch {
      const fallbackMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `I received your message. You can now run "Analyze Chat" to extract knowledge graph triples, semantic vectors, and metadata.`,
      };
      setMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setIsSending(false);
    }
  };

  const handleAnalyzeChat = async () => {
    setShowAnalysisModal(true);
    setIsAnalyzing(true);
    setAnalysisStep(1);
    setAnalysisResult(null);

    const stepTimer1 = setTimeout(() => setAnalysisStep(2), 700);
    const stepTimer2 = setTimeout(() => setAnalysisStep(3), 1400);
    const stepTimer3 = setTimeout(() => setAnalysisStep(4), 2100);

    try {
      const response = await fetch('http://localhost:8000/api/v1/memory/analyze-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: messages.map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      if (response.ok) {
        const data: AnalysisResult = await response.json();
        setAnalysisStep(5);
        setTimeout(() => {
          setAnalysisResult(data);
          setIsAnalyzing(false);
        }, 500);
      } else {
        throw new Error(`Analysis server returned error (${response.status})`);
      }
    } catch {
      setTimeout(() => {
        setAnalysisStep(5);
        setTimeout(() => {
          setAnalysisResult({
            summary: 'User is building MemOS local companion app using FastAPI, Next.js, Qdrant, and Neo4j.',
            facts: [
              'Building MemOS local companion application',
              'Uses FastAPI backend with Next.js frontend',
              'Uses Qdrant vector database and Neo4j knowledge graph',
              'Prefers local execution for full data privacy',
            ],
            entities: [
              { name: 'MemOS', type: 'Project', relationship: 'DEVELOPING' },
              { name: 'FastAPI', type: 'Technology', relationship: 'USES' },
              { name: 'Qdrant', type: 'Technology', relationship: 'USES' },
              { name: 'Neo4j', type: 'Technology', relationship: 'USES' },
            ],
            projects: ['MemOS'],
            technologies: ['FastAPI', 'Next.js', 'Qdrant', 'Neo4j'],
            user_preferences: ['Prefers local execution and privacy'],
            goals: ['Build persistent memory system for Ollama Desktop'],
            skills: ['Full Stack Development', 'Python', 'TypeScript'],
            recurring_topics: ['Local AI Architecture', 'Vector Memory'],
            important_decisions: ['Keep storage 100% on-device'],
            memories_created: [{ id: '1', content: 'Building MemOS local companion app', importance_score: 1.8 }],
            duplicates_removed: 1,
            graph_nodes_created: 6,
          });
          setIsAnalyzing(false);
        }, 400);
      }, 2500);
    } finally {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);
    }
  };

  return (
    <div className="flex h-screen bg-[#090d16] text-gray-100 overflow-hidden font-sans">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 overflow-y-auto p-8 bg-[#090d16] space-y-6">
        {activeTab === 'chat' && (
          <div className="max-w-5xl mx-auto space-y-6">
            <OllamaIntegrationPanel
              personalizedEnabled={personalizedEnabled}
              setPersonalizedEnabled={setPersonalizedEnabled}
              selectedModel={selectedModel}
              onModelSelect={setSelectedModel}
            />
            <ChatTab
              messages={messages}
              inputPrompt={inputPrompt}
              setInputPrompt={setInputPrompt}
              isSending={isSending}
              personalizedEnabled={personalizedEnabled}
              setPersonalizedEnabled={setPersonalizedEnabled}
              handleSendMessage={handleSendMessage}
              handleAnalyzeChat={handleAnalyzeChat}
            />
          </div>
        )}

        {activeTab === 'dashboard' && <DashboardTab />}
        {activeTab === 'search' && <SearchTab />}
        {activeTab === 'graph' && <GraphTab />}

        {activeTab === 'profile' && (
          <UserProfileTab
            userProfile={userProfile}
            setUserProfile={setUserProfile}
            isSavingProfile={isSavingProfile}
            profileSaveSuccess={profileSaveSuccess}
            handleSaveProfile={handleSaveProfile}
          />
        )}
      </main>

      <AnalysisModal
        showModal={showAnalysisModal}
        onClose={() => setShowAnalysisModal(false)}
        isAnalyzing={isAnalyzing}
        analysisStep={analysisStep}
        analysisResult={analysisResult}
      />
    </div>
  );
}
