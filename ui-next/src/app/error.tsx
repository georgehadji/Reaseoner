'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[100vh] flex-col items-center justify-center p-4">
      <h2 className="mb-4 text-xl font-semibold text-red-500">Something went wrong!</h2>
      <p className="mb-6 text-lg text-gray-700 dark:text-gray-300">{error.message}</p>
      <button
        onClick={
          // Attempt to recover by trying to re-render the segments prior to the error
          () => reset()
        }
        className="rounded-lg bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:bg-blue-700 dark:hover:bg-blue-800"
      >
        Try again
      </button>
    </div>
  );
}
