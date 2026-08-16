import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { Sphere, Cylinder, RoundedBox } from '@react-three/drei';
import * as THREE from 'three';
import AudioAura from './AudioAura';

function safeLerp(current, target, alpha, fallback = 1.0) {
  const c = Number.isFinite(current) ? current : fallback;
  const t = Number.isFinite(target) ? target : fallback;
  return THREE.MathUtils.lerp(c, t, alpha);
}

function ResponsiveRobotHead({ emotion = 'neutral', amplitude = 0 }) {
  const headGroupRef = useRef();
  const leftEyeRef = useRef();
  const rightEyeRef = useRef();
  const leftBrowRef = useRef();
  const rightBrowRef = useRef();
  const mouthRef = useRef();
  
  const targetMouse = useRef(new THREE.Vector2());

  // Complete emotion configuration dictionary
  const getEmotionConfig = (emo) => {
    switch (emo) {
      case 'happy':
        return {
          color: '#00ffcc',
          eyeScaleX: 1.25,
          eyeScaleY: 0.3,
          eyeRotZ: 0.0,
          browY: 1.1,
          browRotZ: 0.1,
          mouthWidth: 1.8,
          mouthBaseY: 0.25,
        };
      case 'excited':
        return {
          color: '#00f3ff',
          eyeScaleX: 1.3,
          eyeScaleY: 1.3,
          eyeRotZ: 0.05,
          browY: 1.25,
          browRotZ: 0.15,
          mouthWidth: 1.9,
          mouthBaseY: 0.35,
        };
      case 'angry':
        return {
          color: '#ff0055',
          eyeScaleX: 0.85,
          eyeScaleY: 0.55,
          eyeRotZ: 0.35,
          browY: 0.95,
          browRotZ: -0.4,
          mouthWidth: 1.3,
          mouthBaseY: 0.2,
        };
      case 'sad':
        return {
          color: '#3a86ff',
          eyeScaleX: 0.85,
          eyeScaleY: 0.95,
          eyeRotZ: -0.25,
          browY: 1.15,
          browRotZ: 0.3,
          mouthWidth: 1.2,
          mouthBaseY: 0.2,
        };
      case 'surprised':
        return {
          color: '#ffbe0b',
          eyeScaleX: 1.4,
          eyeScaleY: 1.5,
          eyeRotZ: 0.0,
          browY: 1.35,
          browRotZ: 0.0,
          mouthWidth: 1.0,
          mouthBaseY: 0.6,
        };
      case 'hesitant':
        return {
          color: '#00b4d8',
          eyeScaleX: 0.9,
          eyeScaleY: 0.7,
          eyeRotZ: -0.15,
          browY: 1.05,
          browRotZ: 0.2,
          mouthWidth: 1.1,
          mouthBaseY: 0.2,
        };
      case 'refusing':
        return {
          color: '#e63946',
          eyeScaleX: 1.3,
          eyeScaleY: 0.2,
          eyeRotZ: 0.2,
          browY: 0.9,
          browRotZ: -0.3,
          mouthWidth: 1.4,
          mouthBaseY: 0.15,
        };
      case 'neutral':
      default:
        return {
          color: '#00f3ff',
          eyeScaleX: 1.0,
          eyeScaleY: 1.0,
          eyeRotZ: 0.0,
          browY: 1.1,
          browRotZ: 0.0,
          mouthWidth: 1.6,
          mouthBaseY: 0.2,
        };
    }
  };

  const config = getEmotionConfig(emotion);
  const targetColor = new THREE.Color(config.color);

  useFrame((state) => {
    // 1. Interactive Cursor / Gyro Parallax Tracking
    targetMouse.current.set(
      (state.pointer.x * Math.PI) / 6,
      (state.pointer.y * Math.PI) / 6
    );

    if (headGroupRef.current) {
      headGroupRef.current.rotation.y = safeLerp(headGroupRef.current.rotation.y, targetMouse.current.x, 0.08, 0);
      headGroupRef.current.rotation.x = safeLerp(headGroupRef.current.rotation.x, -targetMouse.current.y, 0.08, 0);
      // Breathing floating offset
      headGroupRef.current.position.y = Math.sin(state.clock.elapsedTime * 2) * 0.08;
    }

    // 2. Left & Right Eyes Scaling & Rotation
    if (leftEyeRef.current && rightEyeRef.current) {
      leftEyeRef.current.scale.x = safeLerp(leftEyeRef.current.scale.x, config.eyeScaleX, 0.12, 1.0);
      leftEyeRef.current.scale.y = safeLerp(leftEyeRef.current.scale.y, config.eyeScaleY, 0.12, 1.0);
      leftEyeRef.current.rotation.z = safeLerp(leftEyeRef.current.rotation.z, config.eyeRotZ, 0.12, 0.0);

      rightEyeRef.current.scale.x = safeLerp(rightEyeRef.current.scale.x, config.eyeScaleX, 0.12, 1.0);
      rightEyeRef.current.scale.y = safeLerp(rightEyeRef.current.scale.y, config.eyeScaleY, 0.12, 1.0);
      rightEyeRef.current.rotation.z = safeLerp(rightEyeRef.current.rotation.z, -config.eyeRotZ, 0.12, 0.0);

      if (leftEyeRef.current.material) leftEyeRef.current.material.color.lerp(targetColor, 0.1);
      if (rightEyeRef.current.material) rightEyeRef.current.material.color.lerp(targetColor, 0.1);
    }

    // 3. Floating Stylized Holographic Eyebrows
    if (leftBrowRef.current && rightBrowRef.current) {
      leftBrowRef.current.position.y = safeLerp(leftBrowRef.current.position.y, config.browY, 0.1, 1.1);
      leftBrowRef.current.rotation.z = safeLerp(leftBrowRef.current.rotation.z, config.browRotZ, 0.1, 0.0);

      rightBrowRef.current.position.y = safeLerp(rightBrowRef.current.position.y, config.browY, 0.1, 1.1);
      rightBrowRef.current.rotation.z = safeLerp(rightBrowRef.current.rotation.z, -config.browRotZ, 0.1, 0.0);

      if (leftBrowRef.current.material) leftBrowRef.current.material.color.lerp(targetColor, 0.1);
      if (rightBrowRef.current.material) rightBrowRef.current.material.color.lerp(targetColor, 0.1);
    }

    // 4. Reactive Lip Sync
    if (mouthRef.current) {
      const targetMouthY = Math.max(config.mouthBaseY, amplitude * 4.5);
      const targetMouthX = config.mouthWidth * (1.0 + (amplitude * 0.3));

      mouthRef.current.scale.y = safeLerp(mouthRef.current.scale.y, targetMouthY, 0.35, 0.2);
      mouthRef.current.scale.x = safeLerp(mouthRef.current.scale.x, targetMouthX, 0.15, 1.6);

      if (mouthRef.current.material) mouthRef.current.material.color.lerp(targetColor, 0.1);
    }
  });

  return (
    <group ref={headGroupRef} position={[0, 0, 0]}>
      {/* Left Eyebrow */}
      <RoundedBox ref={leftBrowRef} args={[0.9, 0.12, 0.1]} position={[-1.1, 1.1, 0]} radius={0.05} smoothness={2}>
        <meshBasicMaterial color={config.color} toneMapped={false} />
      </RoundedBox>

      {/* Right Eyebrow */}
      <RoundedBox ref={rightBrowRef} args={[0.9, 0.12, 0.1]} position={[1.1, 1.1, 0]} radius={0.05} smoothness={2}>
        <meshBasicMaterial color={config.color} toneMapped={false} />
      </RoundedBox>

      {/* Left Eye */}
      <RoundedBox ref={leftEyeRef} args={[0.9, 0.9, 0.2]} position={[-1.1, 0.45, 0]} radius={0.25} smoothness={4}>
        <meshBasicMaterial color={config.color} toneMapped={false} />
      </RoundedBox>

      {/* Right Eye */}
      <RoundedBox ref={rightEyeRef} args={[0.9, 0.9, 0.2]} position={[1.1, 0.45, 0]} radius={0.25} smoothness={4}>
        <meshBasicMaterial color={config.color} toneMapped={false} />
      </RoundedBox>

      {/* Mouth */}
      <RoundedBox ref={mouthRef} args={[1.0, 1.0, 0.2]} position={[0, -0.6, 0]} radius={0.12} smoothness={3}>
        <meshBasicMaterial color={config.color} toneMapped={false} />
      </RoundedBox>

      {/* Dynamic Emotion Accents */}
      {(emotion === 'sad' || emotion === 'hesitant') && (
        <Sphere args={[0.18, 16, 16]} position={[1.9, 0.8, 0.2]} scale={[1, 1.6, 1]}>
          <meshBasicMaterial color="#00e5ff" toneMapped={false} />
        </Sphere>
      )}

      {emotion === 'angry' && (
        <group position={[1.8, 1.2, 0]} rotation={[0, 0, -0.4]}>
          <Cylinder args={[0.0, 0.35, 0.8, 3]}>
            <meshBasicMaterial color="#ff0055" toneMapped={false} />
          </Cylinder>
        </group>
      )}

      {emotion === 'excited' && (
        <Sphere args={[0.12, 16, 16]} position={[-1.8, 1.0, 0.2]} scale={[1.2, 1.2, 1.2]}>
          <meshBasicMaterial color="#ff00ea" toneMapped={false} />
        </Sphere>
      )}
    </group>
  );
}

export default function HologramFace({ emotion = 'neutral', amplitude = 0 }) {
  return (
    <div className="hologram-container" style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}>
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
        {/* Lights */}
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 10, 7]} intensity={1.8} />
        <pointLight position={[-10, -10, -10]} intensity={0.6} color="#00f3ff" />

        {/* 3D Robot Face */}
        <ResponsiveRobotHead emotion={emotion} amplitude={amplitude} />
        
        {/* Audio Reactive Particle Aura */}
        <AudioAura emotion={emotion} amplitude={amplitude} />

        {/* Cinematic Glow */}
        <EffectComposer disableNormalPass>
          <Bloom
            luminanceThreshold={0.15}
            luminanceSmoothing={0.9}
            intensity={2.2}
            radius={0.85}
            mipmapBlur
          />
        </EffectComposer>
      </Canvas>
    </div>
  );
}

