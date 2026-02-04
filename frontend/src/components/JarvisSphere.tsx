import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';

interface JarvisSphereProps {
  state: 'idle' | 'listening' | 'processing' | 'speaking';
  audioLevel: number;
}

export const JarvisSphere = ({ state, audioLevel }: JarvisSphereProps) => {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((stateContext) => {
    if (!meshRef.current) return;

    const time = stateContext.clock.getElapsedTime();

    // Base rotation
    meshRef.current.rotation.x = time * 0.1; // Slower rotation
    meshRef.current.rotation.y = time * 0.15;

    // Dynamic scaling based on audio level or state - Increased by ~30%
    let targetScale = 1 + audioLevel * 0.8; // Max scale ~1.8
    if (state === 'processing') {
      targetScale = 1.05 + Math.sin(time * 3) * 0.05; // Even slower, deeper pulse
    }
    meshRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
  });

  // Determine color and distortion based on state
  let color = "#00f0ff"; // Default Blue
  let distort = 0.4;
  let speed = 0.3; // Very slow base speed for eye comfort

  switch (state) {
    case 'listening':
      color = "#00ff88"; // Green
      distort = 0.3 + audioLevel * 0.7; 
      speed = 0.2 + audioLevel * 0.5; 
      break;
    case 'processing':
      color = "#aa00ff"; // Purple
      distort = 0.4;
      speed = 0.5; 
      break;
    case 'speaking':
      color = "#00f0ff"; // Blue
      distort = 0.3 + audioLevel * 0.8; 
      speed = 0.2 + audioLevel * 0.6;
      break;
    case 'idle':
    default:
      color = "#444444"; // Dim/Gray
      distort = 0.3;
      speed = 1.5;
      break;
  }

  return (
    <Sphere args={[1, 64, 64]} ref={meshRef}>
      <MeshDistortMaterial
        color={color}
        attach="material"
        distort={distort}
        speed={speed}
        roughness={0.2}
        metalness={0.8}
        emissive={color}
        emissiveIntensity={0.5}
      />
    </Sphere>
  );
};
