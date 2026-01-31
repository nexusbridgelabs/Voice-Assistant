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
    meshRef.current.rotation.x = time * 0.2;
    meshRef.current.rotation.y = time * 0.3;

    // Dynamic scaling based on audio level
    const targetScale = 1 + audioLevel * 2; // Amplify small audio changes
    meshRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
  });

  // Determine color and distortion based on state
  let color = "#00f0ff"; // Default Blue
  let distort = 0.4;
  let speed = 2;

  switch (state) {
    case 'listening':
      color = "#00ff88"; // Green
      distort = 0.6;
      speed = 4;
      break;
    case 'processing':
      color = "#aa00ff"; // Purple
      distort = 0.8;
      speed = 8;
      break;
    case 'speaking':
      color = "#00f0ff"; // Blue
      distort = 0.5 + audioLevel; // Distort more when speaking loud
      speed = 3;
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
