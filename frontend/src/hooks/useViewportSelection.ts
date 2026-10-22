import { useState, useCallback, useRef, useEffect } from 'react'
import * as THREE from 'three'

export interface SelectionBox {
  min: THREE.Vector3
  max: THREE.Vector3
}

export interface SelectedGeometry {
  faces: number[]
  edges: number[]
  boundingBox: SelectionBox
}

export function useViewportSelection() {
  const [isSelecting, setIsSelecting] = useState(false)
  const [selectionBox, setSelectionBox] = useState<SelectionBox | null>(null)
  const [selectedGeometry, setSelectedGeometry] = useState<SelectedGeometry | null>(null)
  const startPoint = useRef<THREE.Vector2 | null>(null)
  const endPoint = useRef<THREE.Vector2 | null>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.Camera | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)

  const setScene = useCallback((scene: THREE.Scene) => {
    sceneRef.current = scene
  }, [])

  const setCamera = useCallback((camera: THREE.Camera) => {
    cameraRef.current = camera
  }, [])

  const setRenderer = useCallback((renderer: THREE.WebGLRenderer) => {
    rendererRef.current = renderer
  }, [])

  const startSelection = useCallback((event: React.MouseEvent) => {
    if (!rendererRef.current || !cameraRef.current) return
    setIsSelecting(true)
    const rect = rendererRef.current.domElement.getBoundingClientRect()
    startPoint.current = new THREE.Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1
    )
    endPoint.current = startPoint.current.clone()
  }, [])

  const updateSelection = useCallback((event: React.MouseEvent) => {
    if (!isSelecting || !rendererRef.current || !endPoint.current) return
    const rect = rendererRef.current.domElement.getBoundingClientRect()
    endPoint.current.set(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1
    )
  }, [isSelecting])

  const endSelection = useCallback(() => {
    if (!isSelecting || !startPoint.current || !endPoint.current || !sceneRef.current || !cameraRef.current) {
      setIsSelecting(false)
      return
    }

    // Compute selection box in world space
    const frustum = new THREE.Frustum()
    const projScreenMatrix = new THREE.Matrix4()
    projScreenMatrix.multiplyMatrices(cameraRef.current.projectionMatrix, cameraRef.current.matrixWorldInverse)
    frustum.setFromProjectionMatrix(projScreenMatrix)

    const min = new THREE.Vector3(
      Math.min(startPoint.current.x, endPoint.current.x),
      Math.min(startPoint.current.y, endPoint.current.y),
      -1
    )
    const max = new THREE.Vector3(
      Math.max(startPoint.current.x, endPoint.current.x),
      Math.max(startPoint.current.y, endPoint.current.y),
      1
    )

    // Raycast to find intersected objects
    const selectedFaces: number[] = []
    const selectedEdges: number[] = []

    sceneRef.current.traverse((object) => {
      if (object.isMesh && object.geometry) {
        // Simplified: check if object bounds intersect selection frustum
        const box = new THREE.Box3().setFromObject(object)
        if (frustum.intersectsBox(box)) {
          // In real implementation, would do per-face/edge raycasting
          selectedFaces.push(object.id)
        }
      }
    })

    const box: SelectionBox = { min, max }
    setSelectionBox(box)
    setSelectedGeometry({ faces: selectedFaces, edges: selectedEdges, boundingBox: box })
    setIsSelecting(false)
    startPoint.current = null
    endPoint.current = null
  }, [isSelecting])

  const clearSelection = useCallback(() => {
    setSelectionBox(null)
    setSelectedGeometry(null)
  }, [])

  const getSelectionForAgent = useCallback(() => {
    if (!selectedGeometry) return null
    return {
      type: 'viewport_selection',
      face_count: selectedGeometry.faces.length,
      edge_count: selectedGeometry.edges.length,
      bounding_box: {
        min: [selectedGeometry.boundingBox.min.x, selectedGeometry.boundingBox.min.y, selectedGeometry.boundingBox.min.z],
        max: [selectedGeometry.boundingBox.max.x, selectedGeometry.boundingBox.max.y, selectedGeometry.boundingBox.max.z]
      }
    }
  }, [selectedGeometry])

  return {
    isSelecting,
    selectionBox,
    selectedGeometry,
    setScene,
    setCamera,
    setRenderer,
    startSelection,
    updateSelection,
    endSelection,
    clearSelection,
    getSelectionForAgent
  }
}