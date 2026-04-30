import { Conversation } from './types';

export interface LoadedConversationMessage {
  id: string;
  role: 'user' | 'assistant' | 'error' | 'info';
  content: string;
  phases?: Array<{ index: number; phase: number; name: string; data: unknown }>;
  tokens?: Conversation['total_tokens'] | undefined;
  duration?: number;
  animated?: boolean;
  images?: Array<{ data: string; model?: string }>;
  meta?: { original?: string; enhanced?: string };
}

export function conversationToMessages(
  conversation: Conversation,
  buildMarkdownFromPhases: (phases: Conversation['phases']) => string,
): LoadedConversationMessage[] {
  const renderedPhases = conversation.phases.map((phase, index) => ({
    index,
    phase: phase.phase,
    name: phase.name,
    data: phase.data,
  }));
  const messages: LoadedConversationMessage[] = [
    { id: `u-${conversation.id}`, role: 'user', content: conversation.problem },
  ];

  if (conversation.kind === 'image' && conversation.prompt_meta?.enhanced) {
    messages.push({
      id: `info-${conversation.id}`,
      role: 'info',
      content:
        conversation.prompt_meta.original &&
        conversation.prompt_meta.original !== conversation.prompt_meta.enhanced
          ? `Enhanced prompt: "${conversation.prompt_meta.enhanced}"`
          : `Prompt used for generation: "${conversation.prompt_meta.enhanced}"`,
      meta:
        conversation.prompt_meta.original &&
        conversation.prompt_meta.original !== conversation.prompt_meta.enhanced
          ? conversation.prompt_meta
          : undefined,
    });
  }

  messages.push({
    id: `a-${conversation.id}`,
    role: 'assistant',
    content: conversation.response_content || buildMarkdownFromPhases(conversation.phases),
    phases: renderedPhases.length > 0 ? renderedPhases : undefined,
    tokens: conversation.total_tokens ?? undefined,
    duration: conversation.duration,
    animated: false,
    images: conversation.images,
  });

  if (conversation.errors.length > 0) {
    messages.push({ id: `err-${conversation.id}`, role: 'error', content: conversation.errors.join('\n') });
  }

  return messages;
}
