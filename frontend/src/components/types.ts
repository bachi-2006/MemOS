export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export interface UserProfileData {
  preferred_languages: string[];
  preferred_frameworks: string[];
  current_projects: string[];
  interests: string[];
  skills: string[];
  technologies: string[];
  writing_style: string;
  learning_goals: string[];
  preferred_model: string;
  recent_focus: string[];
}

export interface AnalysisResult {
  summary: string;
  facts: string[];
  entities: { name: string; type: string; related_to?: string; relationship?: string }[];
  projects: string[];
  technologies: string[];
  user_preferences: string[];
  goals: string[];
  skills: string[];
  recurring_topics: string[];
  important_decisions: string[];
  memories_created: any[];
  duplicates_removed: number;
  graph_nodes_created: number;
}
