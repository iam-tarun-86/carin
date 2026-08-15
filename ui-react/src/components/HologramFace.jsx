import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { Sphere, MeshDistortMaterial } from '@react-three/drei';

function ResponsiveRobotHead({ emotion, amplitude }) {
  const headRef = useRef();

  useFrame((state, delta) => {
    // Basic reactive animation based on amplitude
    // Make the head pulse slightly based on the audio
    if (headRef.current) {
        const targetScale = 1 + (amplitude * 0.5);
        // Interpolate for smooth scaling
        headRef.current.scale.lerp({ x: targetScale, y: targetScale, z: targetScale }, 0.1);
        
        // Slow rotation over time
        headRef.current.rotation.y += delta * 0.5;
        headRef.current.rotation.x = Math.sin(state.clock.elapsedTime) * 0.1;
    }
  });

  // Change color based on emotion
  const getColor = () => {
      switch(emotion) {
          case 'happy': return '#00ffcc'; // neon cyan
          case 'angry': return '#ff003c'; // neon red
          case 'sad': return '#0066ff'; // deep blue
          case 'surprised': return '#ffcc00'; // neon yellow
          default: return '#bb86fc'; // neutral purple
      }
  };

  return (
    <Sphere ref={headRef} args={[1.5, 64, 64]} position={[0, 0, 0]}>
      {/* MeshDistortMaterial gives it a liquid/blobby futuristic look, acting as a placeholder */}
      <MeshDistortMaterial
        color={getColor()}
        envMapIntensity={1}
        clearcoat={1}
        clearcoatRoughness={0.1}
        metalness={0.8}
        roughness={0.2}
        distort={0.4 + (amplitude * 2)} // More audio amplitude = more distortion
        speed={2 + (amplitude * 5)}    // More audio amplitude = faster distortion
      />
    </Sphere>
  );
}

export default function HologramFace({ emotion = 'neutral', amplitude = 0 }) {
  return (
    <div className="hologram-container" style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}>
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
        {/* Basic Lighting */}
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1.5} />
        <pointLight position={[-10, -10, -10]} intensity={0.5} color="#00ffcc" />

        {/* The 3D Object */}
        <ResponsiveRobotHead emotion={emotion} amplitude={amplitude} />

        {/* Post-Processing Glow */}
        <EffectComposer>
          <Bloom
            luminanceThreshold={0.2}
            luminanceSmoothing={0.9}
            intensity={2.5}
            radius={0.8}
          />
        </EffectComposer>
      </Canvas>
    </div>
  );
}
