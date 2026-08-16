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
        case 'excited': return '#00f3ff';
        case 'angry': return '#ff0055'; 
        case 'sad': return '#3a86ff'; 
        case 'surprised': return '#ffbe0b'; 
        case 'hesitant': return '#00b4d8';
        case 'refusing': return '#e63946';
        default: return '#00f3ff'; 
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
      scale={10} 
      size={2 + (amplitude * 8)} // Particles pulse reasonably when loud
      speed={0.2 + (amplitude * 1.5)} // Particles swirl faster when loud
      opacity={0.8}
      color={targetColor}
      noise={1.5}
    />
  );
}
