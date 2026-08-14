import './globals.css';

export const metadata = {
  title: 'MemOS - Adaptive Memory Lifecycle Framework',
  description: 'Persistent Long-Term Memory System for Local LLM Agents',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#090d16] text-gray-100 min-h-screen">
        {children}
      </body>
    </html>
  );
}
