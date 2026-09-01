import Navbar from "./components/Navbar";
import Hero3D from "./components/Hero3D";
import ProjectStory from "./components/ProjectStory";
import HowItWorks from "./components/HowItWorks";
import OnionExplorer from "./components/OnionExplorer";
import VisionLab from "./components/VisionLab";
import ProjectDashboard from "./components/ProjectDashboard";
import Footer from "./components/Footer";

export default function App() {
  return (
    <div className="min-h-screen bg-bg text-fg">
      <Navbar />
      <main>
        <Hero3D />
        <ProjectStory />
        <HowItWorks />
        <OnionExplorer />
        <VisionLab />
        <ProjectDashboard />
      </main>
      <Footer />
    </div>
  );
}
