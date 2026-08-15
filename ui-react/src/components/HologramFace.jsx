import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { Sphere, Box, Cylinder, MeshDistortMaterial, RoundedBox } from '@react-three/drei';
import * as THREE from 'three';
import AudioAura from './AudioAura';

function ResponsiveRobotHead({ emotion, amplitude }) {
  const headGroupRef = useRef();
  const leftEyeRef = useRef();
  const rightEyeRef = useRef();
  const mouthRef = useRef();
  
  // Smooth target variables
  const targetMouse = useRef(new THREE.Vector2());

  // Determine colors and shapes based on emotion
  const getEmotionConfig = () => {
      switch(emotion) {
          case 'happy': return { color: '#00ffcc', eyeScaleY: 0.2, eyeScaleX: 1.2 }; 
          case 'angry': return { color: '#ff003c', eyeScaleY: 0.5, eyeScaleX: 0.8, eyeRotZ: 0.3 }; 
          case 'sad': return { color: '#0066ff', eyeScaleY: 1.2, eyeScaleX: 0.8, eyeRotZ: -0.3 }; 
          case 'surprised': return { color: '#ffcc00', eyeScaleY: 1.5, eyeScaleX: 1.0, eyeRotZ: 0 }; 
          case 'hesitant': return { color: '#0066ff', eyeScaleY: 0.8, eyeScaleX: 0.9, eyeRotZ: -0.1 }; 
          default: return { color: '#bb86fc', eyeScaleY: 1.0, eyeScaleX: 1.0, eyeRotZ: 0 }; 
      }
  };

  const config = getEmotionConfig();
  const materialColor = new THREE.Color(config.color);

  useFrame((state, delta) => {
    // 1. Cursor Tracking
    targetMouse.current.set(
      (state.pointer.x * Math.PI) / 4, 
      (state.pointer.y * Math.PI) / 4
    );
    
    if (headGroupRef.current) {
        // Smoothly rotate the head group towards the mouse
        headGroupRef.current.rotation.y = THREE.MathUtils.lerp(headGroupRef.current.rotation.y, targetMouse.current.x, 0.1);
        headGroupRef.current.rotation.x = THREE.MathUtils.lerp(headGroupRef.current.rotation.x, -targetMouse.current.y, 0.1);
        
        // Add a slight natural breathing hover
        headGroupRef.current.position.y = Math.sin(state.clock.elapsedTime * 2) * 0.1;
    }

    // 2. Emotion Morph Targets (Simulated by scaling and rotating primitive eyes)
    if (leftEyeRef.current && rightEyeRef.current) {
        leftEyeRef.current.scale.y = THREE.MathUtils.lerp(leftEyeRef.current.scale.y, config.eyeScaleY, 0.1);
        leftEyeRef.current.scale.x = THREE.MathUtils.lerp(leftEyeRef.current.scale.x, config.eyeScaleX, 0.1);
        leftEyeRef.current.rotation.z = THREE.MathUtils.lerp(leftEyeRef.current.rotation.z, config.eyeRotZ, 0.1);
        
        rightEyeRef.current.scale.y = THREE.MathUtils.lerp(rightEyeRef.current.scale.y, config.eyeScaleY, 0.1);
        rightEyeRef.current.scale.x = THREE.MathUtils.lerp(rightEyeRef.current.scale.x, config.eyeScaleX, 0.1);
        rightEyeRef.current.rotation.z = THREE.MathUtils.lerp(rightEyeRef.current.rotation.z, -config.eyeRotZ, 0.1);

        // Transition color smoothly
        leftEyeRef.current.material.color.lerp(materialColor, 0.1);
        rightEyeRef.current.material.color.lerp(materialColor, 0.1);
    }

    // 3. Real-Time Lip Sync
    if (mouthRef.current) {
        // Fix disappearing mouth: Minimum scale 0.15, max scales with amplitude
        const targetMouthScale = Math.max(0.15, amplitude * 5.0);
        mouthRef.current.scale.y = THREE.MathUtils.lerp(mouthRef.current.scale.y, targetMouthScale, 0.3);
        mouthRef.current.material.color.lerp(materialColor, 0.1);
    }
  });

  return (
    <group ref={headGroupRef}>
      {/* Left Eye */}
      <RoundedBox ref={leftEyeRef} args={[0.8, 0.8, 0.2]} position={[-1.2, 0.5, 0]} radius={0.2} smoothness={2}>
        <meshBasicMaterial color={config.color} toneMapped={false} />
      </RoundedBox>

      {/* Right Eye */}
      <RoundedBox ref={rightEyeRef} args={[0.8, 0.8, 0.2]} position={[1.2, 0.5, 0]} radius={0.2} smoothness={2}>
        <meshBasicMaterial color={config.color} toneMapped={false} />
      </RoundedBox>

      {/* Mouth */}
      <RoundedBox ref={mouthRef} args={[1.6, 0.3, 0.2]} position={[0, -1.2, 0]} radius={0.1} smoothness={2}>
        <meshBasicMaterial color={config.color} toneMapped={false} />
      </RoundedBox>

      {/* Geometric Expression Particles */}
      {(emotion === 'sad' || emotion === 'hesitant') && (
        <Sphere args={[0.15, 16, 16]} position={[1.8, 0.8, 0.2]} scale={[1, 1.5, 1]}>
          <meshBasicMaterial color="#00ffff" toneMapped={false} />
        </Sphere>
      )}
      {emotion === 'angry' && (
        <Cylinder args={[0.0, 0.3, 0.8, 3]} position={[1.5, 1.2, 0]} rotation={[0, 0, -0.5]}>
           <meshBasicMaterial color="#ff003c" toneMapped={false} />
        </Cylinder>
      )}
    </group>
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

        {/* The 3D Interactive Object */}
        <ResponsiveRobotHead emotion={emotion} amplitude={amplitude} />
        
        {/* Audio Reactive Particle Aura */}
        <AudioAura emotion={emotion} amplitude={amplitude} />

        {/* Post-Processing Glow */}
        <EffectComposer disableNormalPass>
          <Bloom
            luminanceThreshold={0.2}
            luminanceSmoothing={0.9}
            intensity={2.0}
            radius={0.8}
            mipmapBlur
          />
        </EffectComposer>
      </Canvas>
    </div>
  );
}
