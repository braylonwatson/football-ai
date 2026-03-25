import Particles from "react-tsparticles";
import { loadSlim } from "tsparticles-slim";

export default function BackgroundParticles() {
  const particlesInit = async (engine) => {
    await loadSlim(engine);
  };

  return (
    <Particles
      id="tsparticles"
      init={particlesInit}
      options={{
        fullScreen: {
          enable: true,
          zIndex: 0,
        },
        background: {
          color: "#000000",
        },
        fpsLimit: 60,
        particles: {
          number: {
            value: 90,
          },
          color: {
            value: "#39ff14",
          },
          links: {
            enable: true,
            color: "#39ff14",
            distance: 150,
            opacity: 0.45,
            width: 1,
          },
          move: {
            enable: true,
            speed: 1,
          },
          size: {
            value: { min: 1, max: 3 },
          },
          opacity: {
            value: 0.8,
          },
        },
        interactivity: {
          events: {
            onHover: {
              enable: true,
              mode: "repulse",
            },
          },
          modes: {
            repulse: {
              distance: 100,
            },
          },
        },
      }}
    />
  );
}