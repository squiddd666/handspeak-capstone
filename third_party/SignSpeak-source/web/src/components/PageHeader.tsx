import { getLogoPath } from "@/lib/getReferenceImage";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  showLogo?: boolean;
  centered?: boolean;
  className?: string;
}

export function PageHeader({
  title,
  subtitle,
  showLogo = true,
  centered = true,
  className,
}: PageHeaderProps) {
  return (
    <header className={cn("space-y-3", centered && "text-center", className)}>
      {showLogo && (
        <div className="flex justify-center">
          <img
            src={getLogoPath()}
            alt="SignSpeak"
            className="w-16 h-16 sm:w-20 sm:h-20 object-contain drop-shadow-md"
          />
        </div>
      )}
      <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-primary neon-text tracking-tight">
        {title}
      </h1>
      {subtitle && (
        <p className="text-sm sm:text-base text-muted-foreground max-w-2xl mx-auto">{subtitle}</p>
      )}
    </header>
  );
}
