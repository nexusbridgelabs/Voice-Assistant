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
      targetScale = 1.2 + Math.sin(time * 2) * 0.25; // Slower frequency (3 -> 2) for deep breathing
    }
    // Faster lerp (0.15) for the scale ensures the "Spikes" are seen, 
    // while the slow audioLevel calculation in useAudio handles the smoothness.
    meshRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.15);
  });

  // Determine color and distortion based on state
  let color = "#00f0ff"; // Default Blue
  let distort = 0.4;
  let speed = 0.2; // Even slower base speed for ultra-smooth liquid feel

  switch (state) {
    case 'listening':
      color = "#00ff88"; // Green
      distort = 0.3 + audioLevel * 0.7; 
      speed = 0.1 + audioLevel * 0.4; // Very low speed multipliers
      break;
    case 'processing':
      color = "#aa00ff"; // Purple
      distort = 0.4;
      speed = 0.3; 
      break;
    case 'speaking':
      color = "#00f0ff"; // Blue
      distort = 0.3 + audioLevel * 0.8; 
      speed = 0.1 + audioLevel * 0.5;
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
