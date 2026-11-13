import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

interface BackButtonProps {
  onClick: () => void;
  ariaLabel?: string;
}

export function BackButton({ onClick, ariaLabel = "Go back" }: BackButtonProps) {
  return (
    <Button
      onClick={onClick}
      variant="ghost"
      size="icon"
      aria-label={ariaLabel}
      className="fixed top-4 left-4 z-50 rounded-full hover:bg-secondary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      <ArrowLeft className="h-5 w-5" />
    </Button>
  );
}
