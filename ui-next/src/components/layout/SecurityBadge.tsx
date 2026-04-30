'use client';

import { useState } from 'react';
import { Lock } from 'lucide-react';
import { SecurityModal } from './SecurityModal';
import { Button } from '@/components/ui/Button';

export function SecurityBadge({ className }: { className?: string }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        leftIcon={<Lock className="h-3.5 w-3.5" />}
        onClick={() => setIsOpen(true)}
        className={className}
      >
        Secure
      </Button>

      <SecurityModal isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  );
}
