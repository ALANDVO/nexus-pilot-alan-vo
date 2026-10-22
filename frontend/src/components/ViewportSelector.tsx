import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Box, Edges } from '@react-three/drei'
import * as THREE from 'three'
import { useRef, useEffect, useState } from 'react'
import { useViewportSelection, SelectionBox } from '@/hooks/useViewportSelection'

interface ViewportSelectorProps {
  modelUrl?: string
  onSelectionChange?: (selection: ReturnType<typeof useViewportSelection>['getSelectionForAgent']) => void
}

export function ViewportSelector({ modelUrl, onSelectionChange }: ViewportSelectorProps) {
  const { scene, camera, gl } = useThree()
  const selection = useViewportSelection()
  const [modelLoaded, setModelLoaded] = useState(false)

  // Connect refs to selection hook
  useEffect(() => {
    selection.setScene(scene)
    selection.setCamera(camera)
    selection.setRenderer(gl)
  }, [scene, camera, gl, selection])

  // Handle mouse events for selection
  const handleMouseDown = (event: React.MouseEvent) => {
    if (event.button === 0 && !event.shiftKey) { // Left click, no shift
      selection.startSelection(event)
    }
  }

  const handleMouseMove = (event: React.MouseEvent) => {
    selection.updateSelection(event)
  }

  const handleMouseUp = () => {
    selection.endSelection()
    if (selection.selectedGeometry && onSelectionChange) {
      onSelectionChange(selection.getSelectionForAgent())
    }
  }

  useFrame(() => {
    // Could add selection box visualization here
  })

  return (
    <div className="relative w-full h-full" onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
      <Canvas
        camera={{ position: [0, 0, 5], fov: 50 }}
        gl={{ preserveDrawingBuffer: true }}
        onCreated={({ gl }) => { gl.setClearColor(0xf8fafc, 1) }}
      >
        <color attach="background" args={['#f8fafc']} />
        <ambientLight intensity={0.8} />
        <directionalLight position={[5, 10, 7]} intensity={1} />
        <OrbitControls enablePan={true} enableZoom={true} enableRotate={true} />
        {modelUrl && (
          <ModelLoader url={modelUrl} onLoad={setModelLoaded} />
        )}
        {!modelLoaded && !modelUrl && (
          <group>
            <Box args={[1, 1, 1]}>
              <meshStandardMaterial color="#2563eb" opacity={0.3} transparent />
            </Box>
            <Edges color="#1e40af" />
          </group>
        )}
        <gridHelper args={[10, 10, '#e2e8f0', '#e2e8f0']} />
      </Canvas>

      {selection.isSelecting && selection.selectionBox && (
        <SelectionOverlay box={selection.selectionBox} camera={camera} size={gl.getSize(new THREE.Vector2())} />
      )}

      {selection.selectedGeometry && (
        <div className="absolute bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-64">
          <div className="card p-3 text-sm">
            <p className="font-medium mb-1">Selection Active</p>
            <p>Faces: {selection.selectedGeometry.faces.length}</p>
            <p>Edges: {selection.selectedGeometry.edges.length}</p>
            <button
              onClick={() => { selection.clearSelection(); onSelectionChange?.(null) }}
              className="btn btn-secondary text-xs mt-2 w-full"
            >
              Clear Selection
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function ModelLoader({ url, onLoad }: { url: string; onLoad: (loaded: boolean) => void }) {
  const loaderRef = useRef<THREE.STLLoader | null>(null)
  const groupRef = useRef<THREE.Group>(new THREE.Group())

  useEffect(() => {
    // In real implementation, use STEP loader (e.g., three-step-loader)
    // For now, show placeholder
    onLoad(true)
    return () => {
      groupRef.current.clear()
    }
  }, [url, onLoad])

  return <primitive object={groupRef.current} dispose={null} />
}

function SelectionOverlay({ box, camera, size }: { box: SelectionBox; camera: THREE.Camera; size: THREE.Vector2 }) {
  // Render selection box overlay
  return null
}

function gridHelper(args: [number, number, string, string]) {
  const [size, divisions, color1, color2] = args
  const grid = new THREE.GridHelper(size, divisions, color1, color2)
  return <primitive object={grid} />
}