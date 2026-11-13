import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { ThemeToggle } from "@/components/ThemeToggle";
import { getLogoPath } from "@/lib/getReferenceImage";

const Home = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 relative overflow-hidden">
      <ThemeToggle />

      <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-secondary/20 -z-10" />

      <div className="text-center space-y-8 max-w-2xl animate-fade-in">
        <div className="flex justify-center">
          <div className="w-40 h-40 sm:w-48 sm:h-48 rounded-full bg-primary/10 neon-glow flex items-center justify-center p-6 shadow-2xl animate-pulse-glow">
            <img
              src={getLogoPath()}
              alt="SignSpeak"
              className="w-32 h-32 sm:w-40 sm:h-40 object-contain drop-shadow-lg"
            />
          </div>
        </div>

        <div className="space-y-3">
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold text-primary neon-text tracking-tight">
            SignSpeak
          </h1>
          <p className="text-lg sm:text-xl text-muted-foreground font-light">
            AI-Powered Sign Language Interpreter
          </p>
        </div>

        <div className="flex flex-col sm:flex-row flex-wrap gap-3 sm:gap-4 justify-center pt-2 sm:pt-4">
          <Button
            onClick={() => navigate("/interpreter")}
            size="lg"
            className="w-full sm:w-auto px-8 py-6 text-lg rounded-xl neon-glow hover:scale-[1.02] focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-300"
          >
            Start Interpreter
          </Button>

          <Button
            onClick={() => navigate("/practice-game")}
            variant="outline"
            size="lg"
            className="w-full sm:w-auto px-8 py-6 text-lg rounded-xl border-2 border-primary/30 hover:border-primary hover:neon-glow hover:scale-[1.02] focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-300"
          >
            Practice Game
          </Button>

          <Button
            onClick={() => navigate("/guide")}
            variant="outline"
            size="lg"
            className="w-full sm:w-auto px-8 py-6 text-lg rounded-xl border-2 border-primary/30 hover:border-primary hover:neon-glow hover:scale-[1.02] focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-300"
          >
            Sign Language Guide
          </Button>
        </div>

        <div className="mt-12 pt-8 border-t border-border/50 space-y-2">
          <p className="text-sm text-muted-foreground">
            Real-time gesture detection • Works 100% offline
          </p>
          <p className="text-sm text-muted-foreground">
            Made by{" "}
            <a
              href="https://www.linkedin.com/in/medhanshsharma05/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded transition-colors"
            >
              Medhansh Sharma
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Home;
