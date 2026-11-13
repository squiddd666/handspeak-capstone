import { ReactNode } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { BackButton } from "@/components/BackButton";
import { cn } from "@/lib/utils";

interface PageLayoutProps {
  children: ReactNode;
  onBack?: () => void;
  backAriaLabel?: string;
  className?: string;
}

export function PageLayout({
  children,
  onBack,
  backAriaLabel = "Go back",
  className,
}: PageLayoutProps) {
  return (
    <div
      className={cn(
        "min-h-screen px-4 py-8 pt-16 sm:pt-8 relative overflow-x-hidden",
        className,
      )}
    >
      <ThemeToggle />
      {onBack && <BackButton onClick={onBack} ariaLabel={backAriaLabel} />}
      <div className="max-w-7xl mx-auto space-y-8">{children}</div>
    </div>
  );
}
