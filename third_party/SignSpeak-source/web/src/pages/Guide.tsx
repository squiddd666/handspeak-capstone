import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { PageLayout } from "@/components/PageLayout";
import { PageHeader } from "@/components/PageHeader";

const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
const signDescriptions: Record<string, string> = {
  A: "Make a fist with thumb alongside",
  B: "Fingers together pointing up, thumb across palm",
  C: "Curved hand forming C shape",
  D: "Index finger up, other fingers touch thumb",
  E: "All fingertips touching thumb",
  F: "Index and thumb touching in circle, other fingers up",
  G: "Index finger and thumb pointing forward",
  H: "Index and middle finger extended sideways",
  I: "Pinky finger extended up",
  J: "Draw a J with pinky finger",
  K: "Index and middle finger up, thumb between them",
  L: "Thumb and index forming L shape",
  M: "Thumb under three fingers",
  N: "Thumb under two fingers",
  O: "All fingertips touching in circle",
  P: "Like K but pointing down",
  Q: "Index finger and thumb pointing down",
  R: "Index and middle fingers crossed",
  S: "Fist with thumb across fingers",
  T: "Thumb between index and middle",
  U: "Index and middle fingers together, pointing up",
  V: "Index and middle fingers apart, pointing up",
  W: "Three fingers up and apart",
  X: "Index finger curved like a hook",
  Y: "Thumb and pinky extended",
  Z: "Draw a Z with index finger",
};

const Guide = () => {
  const navigate = useNavigate();

  return (
    <PageLayout onBack={() => navigate("/")} backAriaLabel="Back to home">
      <PageHeader
        title="Sign Language Guide"
        subtitle="Browse the ASL alphabet and jump into letter practice"
      />

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 sm:gap-5">
        {alphabet.map((letter) => (
          <article
            key={letter}
            role="button"
            tabIndex={0}
            onClick={() => navigate(`/practice/${letter}`)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                navigate(`/practice/${letter}`);
              }
            }}
            className="panel-card p-5 sm:p-6 hover:border-primary hover:neon-glow transition-all duration-300 cursor-pointer group flex flex-col items-center text-center gap-4 min-h-[9.5rem]"
          >
            <span className="text-5xl sm:text-6xl font-bold text-primary group-hover:scale-105 transition-transform duration-300 leading-none">
              {letter}
            </span>

            <p className="text-sm text-muted-foreground leading-relaxed flex-1">
              {signDescriptions[letter]}
            </p>

            <Button
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/practice/${letter}`);
              }}
              size="sm"
              className="w-full rounded-xl mt-auto focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              variant="outline"
            >
              Practice
            </Button>
          </article>
        ))}
      </div>
    </PageLayout>
  );
};

export default Guide;
