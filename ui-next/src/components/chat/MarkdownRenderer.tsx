'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from 'next-themes';
import { Check, Copy } from 'lucide-react';
import { TIMING } from '@/lib/config';
import { copyToClipboard } from '@/lib/utils';

export function MarkdownRenderer({ children }: { children: string }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1({ children }) {
            return <Heading level={1} children={children} />;
          },
          h2({ children }) {
            return <Heading level={2} children={children} />;
          },
          h3({ children }) {
            return <Heading level={3} children={children} />;
          },
          h4({ children }) {
            return <Heading level={4} children={children} />;
          },
          a({ href, children, ...rest }) {
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" {...rest}>
                {children}
              </a>
            );
          },
          code(props) {
            const { inline, className, children, ...rest } = props as {
              inline?: boolean;
              className?: string;
              children?: React.ReactNode;
            };
            const match = /language-(\w+)/.exec(className || '');
            const lang = match ? match[1] : '';
            const codeString = String(children).replace(/\n$/, '');

            if (!inline && lang) {
              return <CodeBlock code={codeString} language={lang} isDark={isDark} />;
            }

            return (
              <code className={className} {...rest}>
                {children}
              </code>
            );
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}

function Heading({ level, children }: { level: 1 | 2 | 3 | 4; children: React.ReactNode }) {
  const text = extractText(children);
  const id = text ? slugify(text) : undefined;
  const Tag = `h${level}` as const;
  return (
    <Tag id={id} className="scroll-mt-24">
      {children}
    </Tag>
  );
}

function extractText(node: React.ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(extractText).join('');
  if (node && typeof node === 'object' && 'props' in node) {
    const props = (node as { props?: { children?: React.ReactNode } }).props;
    return extractText(props?.children);
  }
  return '';
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
}

function CodeBlock({ code, language, isDark }: { code: string; language: string; isDark?: boolean }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const ok = await copyToClipboard(code);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), TIMING.copiedFeedbackMs);
    }
  }

  return (
    <div className="code-block">
      <div className="code-block-header">
        <span className="uppercase tracking-wide">{language}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs transition-colors hover:bg-[var(--surface-3)]"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5" /> Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" /> Copy
            </>
          )}
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={isDark ? vscDarkPlus : vs}
        customStyle={{
          margin: 0,
          padding: '1em',
          background: 'transparent',
          fontSize: '0.85em',
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
