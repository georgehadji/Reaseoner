import { describe, expect, it } from 'vitest';

import { conversationToMessages } from './conversation-history';
import { Conversation } from './types';

describe('conversationToMessages', () => {
  it('restores image conversations with prompt metadata and images', () => {
    const conversation: Conversation = {
      id: 'conv-1',
      conversation_id: 'thread-1',
      turn_number: 1,
      timestamp: '2026-04-22T12:00:00.000Z',
      problem: 'Draw a fox astronaut',
      phases: [],
      errors: [],
      preset: 'balanced',
      method: 'image',
      total_tokens: null,
      duration: 3.2,
      kind: 'image',
      response_content: 'Generated 2 images',
      images: [
        { data: 'data:image/png;base64,one', model: 'gpt-5-image' },
        { data: 'data:image/png;base64,two', model: 'gemini-pro-image' },
      ],
      prompt_meta: {
        original: 'Draw a fox astronaut',
        enhanced: 'Cinematic fox astronaut portrait with rim lighting',
      },
    };

    const messages = conversationToMessages(conversation, () => '');

    expect(messages).toHaveLength(3);
    expect(messages[1]).toMatchObject({
      role: 'info',
      meta: conversation.prompt_meta,
    });
    expect(messages[2]).toMatchObject({
      role: 'assistant',
      content: 'Generated 2 images',
      images: conversation.images,
    });
  });

  it('falls back to markdown content for phase-based conversations', () => {
    const conversation: Conversation = {
      id: 'conv-2',
      conversation_id: 'thread-2',
      turn_number: 1,
      timestamp: '2026-04-22T12:00:00.000Z',
      problem: 'Explain the issue',
      phases: [{ phase: 1, name: 'Synthesis', data: { solution: 'Answer' } }],
      errors: [],
      preset: 'balanced',
      method: 'multi_perspective',
      total_tokens: { input: 1, output: 2, total: 3 },
      kind: 'pipeline',
    };

    const messages = conversationToMessages(conversation, () => 'Rendered markdown');

    expect(messages[1]).toMatchObject({
      role: 'assistant',
      content: 'Rendered markdown',
    });
    expect(messages[1].phases).toHaveLength(1);
  });
});
