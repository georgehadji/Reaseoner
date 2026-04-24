'use client';

import { memo, Suspense } from 'react';
import dynamic from 'next/dynamic';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// CodeBlock is in its own JS chunk (~400KB with Prism), loaded on demand
const CodeBlock = dynamic(
  () => import('./CodeBlock').then((mod) => mod.CodeBlock),
  { ssr: false },
);

const MarkdownRendererComponent = ({ children }: { children: string }) => {
  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1({ children }) {
            return <Heading level={1}>{children}</Heading>;
          },
          h2({ children }) {
            return <Heading level={2}>{children}</Heading>;
          },
          h3({ children }) {
            return <Heading level={3}>{children}</Heading>;
          },
          h4({ children }) {
            return <Heading level={4}>{children}</Heading>;
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
              return (
                <Suspense fallback={<pre className="code-block"><code>{codeString}</code></pre>}>
                  <CodeBlock code={codeString} language={lang} />
                </Suspense>
              );
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
};

export const MarkdownRenderer = memo(MarkdownRendererComponent);

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
