import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { getReferenceImage } from "@/lib/getReferenceImage";
import { Skeleton } from "@/components/ui/skeleton";

interface ReferenceImageProps {
  letter: string;
  alt?: string;
  className?: string;
  frameClassName?: string;
  compact?: boolean;
}

export function ReferenceImage({
  letter,
  alt,
  className,
  frameClassName,
  compact = false,
}: ReferenceImageProps) {
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const src = getReferenceImage(letter);

  useEffect(() => {
    setLoading(true);
    setFailed(false);
  }, [src]);

  const handleError = () => {
    setFailed(true);
    setLoading(false);
  };

  return (
    <div
      className={cn(
        "reference-frame relative flex items-center justify-center bg-secondary/10",
        compact ? "aspect-square p-2 min-h-[120px]" : "aspect-[4/3] p-4 min-h-[200px] sm:min-h-[260px]",
        frameClassName,
      )}
    >
      {loading && !failed && (
        <Skeleton
          className={cn("absolute rounded-xl", compact ? "inset-2" : "inset-4")}
          aria-hidden="true"
        />
      )}
      {!failed ? (
        <img
          src={src}
          alt={alt ?? `ASL reference sign for letter ${letter}`}
          className={cn(
            "max-w-full max-h-full w-auto h-auto object-contain transition-opacity duration-300",
            loading ? "opacity-0" : "opacity-100",
            className,
          )}
          onLoad={() => {
            setLoading(false);
          }}
          onError={handleError}
        />
      ) : (
        <p className="text-sm text-muted-foreground text-center px-4">
          Reference image unavailable for letter {letter}
        </p>
      )}
    </div>
  );
}
