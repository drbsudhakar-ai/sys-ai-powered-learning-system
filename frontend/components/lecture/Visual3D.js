/** Isolated 3D teaching visuals (react-three-fiber). Lazy-loaded by parent. */
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import { useMemo, useRef } from "react";

function AxisArrow({ dir = [1, 0, 0], color = "#1e88e5", length = 1.4 }) {
  const [x, y, z] = dir;
  const len = Math.sqrt(x * x + y * y + z * z) || 1;
  const nx = x / len;
  const ny = y / len;
  const nz = z / len;
  // Orient +Y cylinder toward direction via simple euler for common teaching axes
  const rot =
    Math.abs(nx) > 0.7
      ? [0, 0, -Math.PI / 2]
      : Math.abs(ny) > 0.7
        ? [0, 0, 0]
        : [Math.PI / 2, 0, 0];
  return (
    <group>
      <mesh position={[nx * length * 0.4, ny * length * 0.4, nz * length * 0.4]} rotation={rot}>
        <cylinderGeometry args={[0.035, 0.035, length * 0.8, 12]} />
        <meshStandardMaterial color={color} />
      </mesh>
      <mesh position={[nx * length * 0.85, ny * length * 0.85, nz * length * 0.85]} rotation={rot}>
        <coneGeometry args={[0.09, 0.22, 12]} />
        <meshStandardMaterial color={color} />
      </mesh>
    </group>
  );
}

function ForceVectors({ playing }) {
  const ref = useRef();
  useFrame((_, dt) => {
    if (playing && ref.current) ref.current.rotation.y += dt * 0.35;
  });
  return (
    <group ref={ref}>
      <mesh position={[0, 0, 0]}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshStandardMaterial color="#fb8c00" />
      </mesh>
      <AxisArrow dir={[1, 0.15, 0]} color="#1e88e5" />
      <AxisArrow dir={[0.2, 1, 0]} color="#43a047" length={1.1} />
      <Html position={[1.35, 0.25, 0]} center>
        <span className="r3f-label">F</span>
      </Html>
      <Html position={[0.25, 1.15, 0]} center>
        <span className="r3f-label">a</span>
      </Html>
    </group>
  );
}

function HeartModel({ playing, highlight }) {
  const ref = useRef();
  useFrame((_, dt) => {
    if (playing && ref.current) ref.current.rotation.y += dt * 0.4;
  });
  const color = highlight ? "#e53935" : "#c62828";
  return (
    <group ref={ref}>
      <mesh position={[-0.25, 0.15, 0]} scale={[0.9, 1, 0.85]}>
        <sphereGeometry args={[0.55, 24, 24]} />
        <meshStandardMaterial color={color} roughness={0.45} />
      </mesh>
      <mesh position={[0.25, 0.15, 0]} scale={[0.9, 1, 0.85]}>
        <sphereGeometry args={[0.55, 24, 24]} />
        <meshStandardMaterial color="#b71c1c" roughness={0.45} />
      </mesh>
      <mesh position={[0, -0.45, 0]} rotation={[0, 0, Math.PI / 4]}>
        <coneGeometry args={[0.75, 1.1, 4]} />
        <meshStandardMaterial color="#8e0000" />
      </mesh>
      <Html position={[0, 1.1, 0]} center>
        <span className="r3f-label">{highlight || "Heart"}</span>
      </Html>
    </group>
  );
}

function ConceptSpace({ playing }) {
  const ref = useRef();
  useFrame((_, dt) => {
    if (playing && ref.current) {
      ref.current.rotation.y += dt * 0.3;
      ref.current.rotation.x = Math.sin(Date.now() / 900) * 0.15;
    }
  });
  return (
    <group ref={ref}>
      <mesh>
        <icosahedronGeometry args={[0.9, 0]} />
        <meshStandardMaterial color="#1e88e5" wireframe />
      </mesh>
      <mesh position={[1.2, 0.4, 0]}>
        <boxGeometry args={[0.35, 0.35, 0.35]} />
        <meshStandardMaterial color="#fb8c00" />
      </mesh>
    </group>
  );
}

export default function Visual3D({ step, playing }) {
  const model = step?.visual?.model_type || "concept_space";
  const objects = step?.visual?.objects || [];
  const highlight = objects.find((o) => String(o).includes("atrium") || String(o).includes("ventricle"));

  const scene = useMemo(() => {
    if (model === "force_vectors" || model === "block_force") return <ForceVectors playing={playing} />;
    if (model === "heart") return <HeartModel playing={playing} highlight={highlight} />;
    return <ConceptSpace playing={playing} />;
  }, [model, playing, highlight]);

  return (
    <div className="visual3d-wrap" role="img" aria-label={`3D model ${model}`}>
      <Canvas camera={{ position: [0, 0.4, 3.2], fov: 45 }} dpr={[1, 1.75]}>
        <ambientLight intensity={0.7} />
        <directionalLight position={[3, 4, 2]} intensity={1.1} />
        {scene}
        <OrbitControls enablePan={false} enableZoom maxDistance={6} minDistance={2} />
      </Canvas>
    </div>
  );
}
