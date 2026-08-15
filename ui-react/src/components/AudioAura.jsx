import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Sparkles } from '@react-three/drei';
import * as THREE from 'three';

export default function AudioAura({ amplitude, emotion }) {
  const sparklesRef = useRef();

  // Determine base color of particles based on emotion
  const getEmotionColor = () => {
    switch(emotion) {
        case 'happy': return '#00ffcc'; 
        case 'angry': return '#ff003c'; 
        case 'sad': return '#0066ff'; 
        case 'surprised': return '#ffcc00'; 
        default: return '#bb86fc'; 
    }
  };

  const targetColor = new THREE.Color(getEmotionColor());

  useFrame((state) => {
    if (sparklesRef.current) {
        // Pulse particles outward when amplitude is high
        const baseScale = 3;
        const targetScale = baseScale + (amplitude * 5.0);
        sparklesRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
        
        // Rotate particles slightly faster when speaking
        sparklesRef.current.rotation.y += (0.002 + (amplitude * 0.02));
        
        // Optional: you could manually update colors in the points geometry here 
        // if you want each particle to shift smoothly, but for performance, 
        // passing it to the <Sparkles> prop color works well enough for re-renders.
    }
  });

  return (
    <Sparkles 
      ref={sparklesRef}
      count={400} 
      scale={3} 
      size={20 + (amplitude * 100)} // Particles get huge when loud
      speed={0.4 + (amplitude * 2)} // Particles swirl faster when loud
      opacity={0.8}
      color={targetColor}
      noise={1.5}
    />
  );
}
